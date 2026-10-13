"""
Sequential Queue Worker for Transcriber.
Pulls jobs from SQLite, coordinates audio extraction, transcription, and diarization,
and updates database state and SSE telemetry without memory exhaustion.
"""

import threading
import time
import os
import traceback
from pathlib import Path
from typing import Optional, Dict, Any

from db.database import get_db, DATA_DIR
from db.crud import (
    get_job,
    update_job_progress,
    update_job_status,
    save_transcript,
)
from engine.audio import extract_audio_stream
from engine.transcriber import TranscriberEngine
from api.events import (
    broadcast_job_progress,
    broadcast_job_completed,
    broadcast_job_failed,
)


from core.constants import SPEAKER_PALETTE  # noqa: F401 — re-exported for worker internals


class QueueWorker(threading.Thread):
    """
    Background worker thread running sequential jobs one-by-one.
    """
    _instance: Optional["QueueWorker"] = None
    _lock = threading.Lock()
    _cancelled_jobs = set()
    _cancelled_lock = threading.Lock()

    def __init__(self):
        super().__init__(name="TranscriberQueueWorker", daemon=True)
        self.stop_event = threading.Event()
        self.active_job_id: Optional[str] = None
        self.is_busy = False

    @classmethod
    def cancel_job_id(cls, job_id: str):
        """Signals active or queued job cancellation immediately in memory."""
        with cls._cancelled_lock:
            cls._cancelled_jobs.add(job_id)

    @classmethod
    def is_job_cancelled(cls, job_id: str) -> bool:
        with cls._cancelled_lock:
            return job_id in cls._cancelled_jobs

    @classmethod
    def get_instance(cls) -> "QueueWorker":
        with cls._lock:
            if cls._instance is None:
                cls._instance = QueueWorker()
                cls._instance.start()
            return cls._instance

    def run(self):
        """Worker loop polling SQLite for queued jobs."""
        # On Windows, set worker process priority to BELOW_NORMAL to ensure buttery UI & no audio drops
        import sys
        if sys.platform == "win32":
            try:
                import psutil
                psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            except Exception:
                pass

        while not self.stop_event.is_set():
            job = self._fetch_next_job()
            if job:
                self.is_busy = True
                self.active_job_id = job["id"]
                try:
                    self._process_job(job)
                except InterruptedError:
                    print(f"Job {job['id']} cancelled by user.")
                    update_job_status(job["id"], "cancelled")
                    update_job_progress(job["id"], 0.0, "Cancelled by user")
                    broadcast_job_progress(job["id"], 0.0, "Cancelled by user", status="cancelled")
                except Exception as e:
                    err_msg = f"{str(e)}\n{traceback.format_exc()}"
                    print(f"Job {job['id']} failed: {err_msg}")
                    update_job_status(job["id"], "failed", error_message=str(e))
                    broadcast_job_failed(job["id"], str(e))
                finally:
                    with self._cancelled_lock:
                        self._cancelled_jobs.discard(job["id"])
                    self.active_job_id = None
                    self.is_busy = False
            else:
                # Sleep briefly before polling again
                time.sleep(1.0)

    def _fetch_next_job(self) -> Optional[Dict[str, Any]]:
        """Pulls the oldest queued job from SQLite."""
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1"
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def _process_job(self, job: Dict[str, Any]):
        """Executes full ingestion and transcription pipeline for a single job."""
        job_id = job["id"]
        last_db_cancel_check = 0.0

        def check_cancelled():
            nonlocal last_db_cancel_check
            # Fast in-memory check first (sub-microsecond)
            if self.is_job_cancelled(job_id):
                raise InterruptedError("Job cancelled by user")
            # Throttle database polling to at most once every 2 seconds
            now = time.time()
            if now - last_db_cancel_check >= 2.0:
                last_db_cancel_check = now
                current = get_job(job_id)
                if not current or current.get("status") == "cancelled":
                    raise InterruptedError("Job cancelled by user")

        check_cancelled()
        input_filepath = job["filepath"]
        if not input_filepath or not os.path.exists(input_filepath):
            err = f"Media file not found on disk: {input_filepath}"
            print(f"Job {job_id} aborted: {err}")
            update_job_status(job_id, "failed", error_message=err)
            broadcast_job_failed(job_id, err)
            return

        cache_dir = DATA_DIR / "media" / job_id
        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_wav_path = str(cache_dir / "audio_16k.wav")

        start_time = time.time()

        # Step 1: Preprocessing & Audio Extraction
        update_job_status(job_id, "preprocessing")
        update_job_progress(job_id, 2.0, "Extracting 16kHz audio stream...")
        broadcast_job_progress(job_id, 2.0, "Extracting audio stream...", status="preprocessing")

        restore = bool(job.get("restore_audio", False))
        duration = extract_audio_stream(input_filepath, temp_wav_path, restore_audio=restore)
        check_cancelled()

        # Precompute acoustic waveform peaks for instantaneous UI rendering
        try:
            from engine.audio import generate_waveform_peaks
            peaks = generate_waveform_peaks(temp_wav_path, num_peaks=128)
            waveform_file = cache_dir / "waveform.json"
            with open(waveform_file, "w") as wf:
                json.dump({"job_id": job_id, "peaks": peaks}, wf)
        except Exception:
            pass

        update_job_progress(job_id, 10.0, f"Audio extracted ({round(duration, 1)}s). Initializing ASR...")
        broadcast_job_progress(job_id, 10.0, "Audio extracted. Initializing ASR...", status="transcribing")

        # Step 2: Transcription
        update_job_status(job_id, "transcribing")

        last_progress_time = 0.0
        last_progress_pct = -1.0

        def progress_cb(pct: float, msg: str):
            nonlocal last_progress_time, last_progress_pct
            check_cancelled()
            now = time.time()
            if (now - last_progress_time >= 0.4) or abs(pct - last_progress_pct) >= 2.0 or pct >= 90.0:
                last_progress_time = now
                last_progress_pct = pct
                update_job_progress(job_id, pct, msg)
                broadcast_job_progress(job_id, pct, msg, status="transcribing")

        prompt = job.get("initial_prompt")
        if not prompt and job.get("language") == "hi":
            from engine.hindi_processor import HINDI_LEXICAL_PROMPT
            prompt = HINDI_LEXICAL_PROMPT

        asr_result = TranscriberEngine.transcribe(
            audio_path=temp_wav_path,
            mode=job.get("mode", "whale"),
            language=job.get("language", "auto"),
            task=job.get("task", "transcribe"),
            initial_prompt=prompt,
            progress_callback=progress_cb,
        )

        check_cancelled()

        segments = asr_result["segments"]
        full_text = asr_result["full_text"]
        detected_lang = asr_result["detected_language"]
        lang_prob = asr_result["language_probability"]

        # Automatic post-processing for Hindi (suppresses Perso-Arabic bleed and cleans phonetic terms)
        if detected_lang == "hi" or job.get("language") == "hi":
            try:
                from engine.hindi_processor import polish_segments_with_ai, clean_perso_arabic_bleed
                update_job_progress(job_id, 88.0, "Polishing Hindi transcript & normalizing Devanagari...")
                broadcast_job_progress(job_id, 88.0, "Polishing Hindi transcript...", status="transcribing")
                corrections = polish_segments_with_ai(segments)
                for idx, seg in enumerate(segments):
                    if idx in corrections:
                        seg["text"] = corrections[idx]
                    else:
                        seg["text"] = clean_perso_arabic_bleed(seg.get("text", ""))

                    # Synchronize word objects with polished vocabulary
                    new_w_list = seg["text"].split()
                    seg_words = seg.get("words", [])
                    if len(new_w_list) == len(seg_words):
                        for w_obj, new_w in zip(seg_words, new_w_list):
                            w_obj["word"] = clean_perso_arabic_bleed(new_w)
                    elif new_w_list:
                        s_start = seg.get("start_time", 0.0)
                        s_end = seg.get("end_time", s_start + 1.0)
                        s_dur = max(0.05, s_end - s_start)
                        step = s_dur / len(new_w_list)
                        seg["words"] = [
                            {
                                "word": clean_perso_arabic_bleed(w),
                                "start_time": round(s_start + (w_idx * step), 3),
                                "end_time": round(s_start + ((w_idx + 1) * step), 3),
                                "confidence_score": 1.0,
                            }
                            for w_idx, w in enumerate(new_w_list)
                        ]
                full_text = " ".join(seg["text"] for seg in segments)
            except Exception as e:
                print(f"Warning: Hindi post-processing failed ({e}), continuing with raw transcript.")

        # Step 3: Diarization / Intelligent Speaker & Character Identification
        update_job_status(job_id, "diarizing")
        update_job_progress(job_id, 92.0, "Identifying speakers & roles...")
        broadcast_job_progress(job_id, 92.0, "Identifying speakers & roles...", status="diarizing")

        from engine.speaker_id import identify_speakers_for_segments
        from services.settings_service import get_raw_gemini_key, get_raw_openrouter_key

        num_spk = job.get("num_speakers") or 3
        g_key = get_raw_gemini_key()
        o_key = get_raw_openrouter_key()
        try:
            smart_id_res = identify_speakers_for_segments(
                segments,
                num_speakers=num_spk,
                tier="auto",
                gemini_api_key=g_key,
                openrouter_api_key=o_key,
            )
        except Exception as e:
            print(f"Warning: Speaker ID failed ({e}), falling back to default attribution.")
            smart_id_res = {
                "speakers": [{"speaker_label": "SPEAKER_00", "display_name": "Speaker 1", "color_hex": "#2563eb"}],
                "segment_assignments": {i: "SPEAKER_00" for i in range(len(segments))},
                "addressee_assignments": {},
                "intent_assignments": {},
            }
        speakers_list = smart_id_res["speakers"]
        assignments = smart_id_res.get("segment_assignments", {})
        addressees = smart_id_res.get("addressee_assignments", {})
        intents = smart_id_res.get("intent_assignments", {})

        for idx, seg in enumerate(segments):
            assigned_label = assignments.get(idx, "SPEAKER_00")
            seg["speaker_label"] = assigned_label
            seg["addressed_to"] = addressees.get(idx)
            seg["turn_intent"] = intents.get(idx)
            for w in seg.get("words", []):
                w["speaker_label"] = assigned_label

        # Step 4: Persist Results
        update_job_progress(job_id, 98.0, "Saving transcript records to database...")
        broadcast_job_progress(job_id, 98.0, "Saving transcript records...", status="saving")

        save_transcript(
            job_id=job_id,
            full_text=full_text,
            detected_language=detected_lang,
            language_probability=lang_prob,
            segments_data=segments,
            speakers_data=speakers_list,
        )

        total_duration = time.time() - start_time
        update_job_status(job_id, "completed", duration_seconds=round(duration, 2))
        update_job_progress(job_id, 100.0, "Transcription completed successfully.")
        broadcast_job_completed(job_id, round(duration, 2))

        # Reclaim VRAM after job completion
        try:
            import torch
            if torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def stop(self):
        """Stops the worker loop cleanly."""
        self.stop_event.set()


def start_worker():
    """Initializes and starts the queue worker singleton."""
    return QueueWorker.get_instance()
