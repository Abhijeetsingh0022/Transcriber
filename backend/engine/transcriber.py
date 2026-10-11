"""
Core Speech-to-Text & Acoustic Translation Engine.
Wraps faster-whisper (CTranslate2) with dynamic model switching, hardware routing,
built-in Silero VAD hallucination filtering, and word-level timestamps.
"""

import wave
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from faster_whisper import WhisperModel
from engine.hardware import get_compute_backend

# Model mappings corresponding to Transcriber tiers
MODEL_TIER_MAP = {
    "whale": "Systran/faster-whisper-large-v3",
    "whale_turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "dolphin": "Systran/faster-whisper-small",
    "cheetah": "Systran/faster-whisper-base",
}

DEFAULT_BEAM_SIZES = {
    "whale": 5,        # Gold standard: Whisper Large-v3 with 5-beam search
    "whale_turbo": 5,  # Large-v3 Turbo (4 decoder layers) with 5-beam search is ultra-fast & maximum accuracy
    "dolphin": 5,      # Small model needs 5-beam search to resolve phonetic ambiguities
    "cheetah": 3,      # Base model upgraded from greedy to 3-beam search
}


def load_audio_waveform(audio_path: str, normalize_volume: bool = True) -> np.ndarray:
    """
    Reads audio into normalized float32 numpy array at 16 kHz mono.
    Supports standard 16-bit PCM WAV via wave, with automatic PyAV fallback
    for non-standard bit depths, float WAV, or container audio.
    Applies percentile-calibrated loudness leveling to ensure optimal SNR for Whisper log-mel filterbanks.
    """
    arr: Optional[np.ndarray] = None
    try:
        with wave.open(audio_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if n_frames > 0 and n_channels == 1 and sampwidth == 2 and framerate == 16000:
                frames = wf.readframes(n_frames)
                raw = np.frombuffer(frames, dtype=np.int16)
                arr = raw.astype(np.float32) * np.float32(1.0 / 32768.0)
    except Exception:
        arr = None

    # Fallback to PyAV if wave.open failed or audio is not standard 16kHz mono 16-bit
    if arr is None or arr.size == 0:
        try:
            import av
            container = av.open(audio_path)
            try:
                audio_stream = next((s for s in container.streams if s.type == "audio"), None)
                if audio_stream:
                    resampler = av.audio.resampler.AudioResampler(format="flt", layout="mono", rate=16000)
                    chunks = []
                    for frame in container.decode(audio_stream):
                        for resampled in resampler.resample(frame):
                            chunks.append(resampled.to_ndarray().flatten())
                    if chunks:
                        arr = np.concatenate(chunks).astype(np.float32)
            finally:
                container.close()
        except Exception:
            pass

    if arr is None or arr.size == 0:
        return np.empty(0, dtype=np.float32)

    # High-accuracy dynamic range optimization:
    # Uses 99th percentile peak energy so an isolated click or mic pop does not keep quiet speech quiet.
    if normalize_volume and arr.size > 0:
        p99 = float(np.percentile(np.abs(arr), 99.0))
        if 0.003 < p99 < 0.65:
            # Target speech level around 0.85 peak without clipping
            gain = min(0.85 / p99, 5.0)
            arr = np.clip(arr * np.float32(gain), -0.99, 0.99)

    return arr


import threading
import gc


class TranscriberEngine:
    """
    Manages Whisper model instances, lifecycle, caching, and inference.
    """
    _loaded_model: Optional[WhisperModel] = None
    _loaded_tier: Optional[str] = None
    _model_lock = threading.Lock()

    @classmethod
    def get_model(cls, tier: str = "whale") -> WhisperModel:
        """
        Loads or returns cached model instance for the requested tier with thread safety.
        """
        tier_key = tier.lower()
        model_name = MODEL_TIER_MAP.get(tier_key, tier)

        with cls._model_lock:
            if cls._loaded_model is not None and cls._loaded_tier == tier_key:
                return cls._loaded_model

            # Clean up prior loaded model to free VRAM/system RAM before switching tiers
            if cls._loaded_model is not None:
                del cls._loaded_model
                cls._loaded_model = None
                cls._loaded_tier = None
                gc.collect()

            backend = get_compute_backend()
            cpu_threads = backend.get("cpu_threads", 4)

            # Resolve persistent OS model directory
            try:
                from services.model_service import get_default_models_dir
                models_dir = str(get_default_models_dir())
            except Exception:
                models_dir = str(Path.home() / ".cache" / "transcriber" / "models")

            # Initialize Faster-Whisper with detected hardware backend
            model = WhisperModel(
                model_size_or_path=model_name,
                device=backend["whisper_device"],
                compute_type=backend["compute_type"],
                cpu_threads=cpu_threads,
                download_root=models_dir,
            )

            cls._loaded_model = model
            cls._loaded_tier = tier_key
            return model

    @classmethod
    def release_model(cls) -> bool:
        """
        Unloads any cached Whisper model from RAM/VRAM and forces garbage collection.
        Returns True if a model was unloaded.
        """
        with cls._model_lock:
            if cls._loaded_model is not None:
                del cls._loaded_model
                cls._loaded_model = None
                cls._loaded_tier = None
                gc.collect()
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
                return True
            return False

    @classmethod
    def transcribe(
        cls,
        audio_path: str,
        mode: str = "whale",
        language: str = "auto",
        task: str = "transcribe",
        initial_prompt: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Transcribes or translates 16 kHz mono WAV file to text with word-level timestamps.
        Optimized for high throughput, low latency, and maximum word accuracy.
        """
        model = cls.get_model(mode)
        beam_size = DEFAULT_BEAM_SIZES.get(mode, 5)
        best_of = 5
        patience = 1.0 if beam_size > 1 else None
        lang_arg = None if (not language or language == "auto") else language

        # Multi-candidate temperature fallback schedule:
        # Temperature 0.0 executes first for fast, deterministic, greedy/beam decoding.
        # If and only if compression ratio or log-probability thresholds fail, higher temperatures
        # are tested sequentially to unstick the decoder without dropping words or getting trapped in loops.
        temperature = [0.0, 0.2, 0.4, 0.6, 0.8]

        # Sensitive, non-clipping VAD parameters:
        # Preserves short responses ("yes", "no", "hi", "OK") and low-energy speech
        vad_params = dict(
            threshold=0.38,               # Captures soft speech and quiet consonant onsets
            min_speech_duration_ms=100,   # Preserves single-syllable and short answers (was 250ms)
            max_speech_duration_s=30.0,   # Matches Whisper 30s context window
            min_silence_duration_ms=500,  # Natural clause and sentence boundary detection
            speech_pad_ms=400,            # 400ms padding on both sides to preserve initial plosives and ending fricatives
        )

        if progress_callback:
            progress_callback(10.0, f"Loaded {mode.upper()} model. Running transcription...")

        # Load normalized waveform into memory, with automatic audio_path fallback
        waveform = load_audio_waveform(audio_path)
        audio_target = waveform if len(waveform) > 0 else audio_path

        # Transcribe with faster-whisper with full acoustic precision
        segments_gen, info = model.transcribe(
            audio=audio_target,
            language=lang_arg,
            task=task,
            beam_size=beam_size,
            best_of=best_of,
            patience=patience,
            initial_prompt=initial_prompt,
            condition_on_previous_text=True,  # preserves context, capitalization, and naming
            prompt_reset_on_temperature=0.5,  # resets prompt context if temperature fallback triggers
            vad_filter=True,  # Built-in Silero VAD suppression
            vad_parameters=vad_params,
            word_timestamps=True,
            prepend_punctuations="\"'“¿([{-",
            append_punctuations="\"'.。,，!！?？:：”)]}、",
            hallucination_silence_threshold=2.0,  # suppresses hallucinated tokens during long silence
            temperature=temperature,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
            language_detection_segments=3 if lang_arg is None else 1,
        )

        detected_language = info.language
        language_probability = info.language_probability
        duration = info.duration or 1.0

        segments_data = []
        full_text_parts = []

        # Consume generator and track progress
        for seg in segments_gen:
            text = seg.text.strip()
            if not text:
                continue

            words = []
            seg_start = round(seg.start, 3) if seg.start is not None else 0.0
            seg_end = round(seg.end, 3) if seg.end is not None else (seg_start + 0.1)

            if seg.words:
                for w in seg.words:
                    w_start = round(w.start, 3) if w.start is not None else seg_start
                    w_end = round(w.end, 3) if w.end is not None else seg_end
                    w_prob = round(w.probability, 3) if (hasattr(w, "probability") and w.probability is not None) else 1.0
                    words.append({
                        "word": w.word,
                        "start_time": w_start,
                        "end_time": max(w_end, w_start),
                        "confidence_score": w_prob,
                    })

            # Calculate segment-level confidence from average token log-probability
            seg_confidence = round(float(np.exp(seg.avg_logprob)), 3) if (hasattr(seg, "avg_logprob") and seg.avg_logprob is not None) else 1.0

            # Fallback word generator: ensure word synchronization even if alignment skipped tokens
            if not words and text:
                tokens = text.split()
                if tokens:
                    tok_dur = max(0.04, (seg_end - seg_start) / len(tokens))
                    for i, tok in enumerate(tokens):
                        t_s = round(seg_start + i * tok_dur, 3)
                        t_e = round(min(seg_end, t_s + tok_dur), 3)
                        words.append({
                            "word": tok,
                            "start_time": t_s,
                            "end_time": max(t_e, t_s + 0.02),
                            "confidence_score": seg_confidence,
                        })

            segment_dict = {
                "start_time": seg_start,
                "end_time": max(seg_end, seg_start + 0.05),
                "text": text,
                "confidence_score": seg_confidence,
                "words": words,
            }
            segments_data.append(segment_dict)
            full_text_parts.append(text)

            if progress_callback and duration > 0:
                # Progress from 10% to 90%
                pct = 10.0 + (min(seg_end / duration, 1.0) * 80.0)
                progress_callback(round(pct, 1), f"Transcribing ({round(seg_end)}s / {round(duration)}s)")

        full_text = " ".join(full_text_parts)

        if progress_callback:
            progress_callback(90.0, "Transcription inference complete.")

        total_words = len(full_text.split()) if full_text else 0

        return {
            "full_text": full_text,
            "detected_language": detected_language,
            "language_probability": round(language_probability, 3),
            "duration_seconds": round(duration, 2),
            "word_count": total_words,
            "segments": segments_data,
        }
