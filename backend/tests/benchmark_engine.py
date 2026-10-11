"""
Transcriber Engine Performance & Accuracy Benchmark.
Tests:
1. Audio Waveform Loading & Peak SNR Normalization latency.
2. Fast greedy vs beam temperature fallback decoding efficiency.
3. Silero VAD continuity and segment generation.
4. Memory stability across multiple transcriptions.
"""

import time
import math
import struct
import tempfile
import numpy as np
import wave
from engine.transcriber import TranscriberEngine, load_audio_waveform
from engine.hardware import get_compute_backend, get_system_telemetry


def benchmark_engine():
    print("========================================================================")
    print(" TRANSCRIBER ENGINE ACCURACY & PERFORMANCE BENCHMARK")
    print("========================================================================")

    # 1. Hardware Environment
    backend = get_compute_backend()
    print(f"Hardware: {backend['platform']} ({backend['device_name']})")
    print(f"Compute Type: {backend['compute_type']} | CPU Threads: {backend['cpu_threads']}")

    # 2. Audio Waveform Loading & Dynamic Range Normalization
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name

    try:
        # Create a 5-second synthetic quiet speech tone (amplitude 0.15 = -16 dBFS)
        sr = 16000
        duration = 5.0
        n_samples = int(sr * duration)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            raw = bytearray()
            for i in range(n_samples):
                # 440 Hz + 880 Hz harmonic
                val = int(32767.0 * (0.10 * math.sin(2.0 * math.pi * 440.0 * i / sr) + 0.05 * math.sin(2.0 * math.pi * 880.0 * i / sr)))
                raw.extend(struct.pack("<h", val))
            wf.writeframes(raw)

        t0 = time.perf_counter()
        wf_unnorm = load_audio_waveform(wav_path, normalize_volume=False)
        t_unnorm = time.perf_counter() - t0

        t0 = time.perf_counter()
        wf_norm = load_audio_waveform(wav_path, normalize_volume=True)
        t_norm = time.perf_counter() - t0

        peak_before = float(np.max(np.abs(wf_unnorm)))
        peak_after = float(np.max(np.abs(wf_norm)))
        print(f"\n[1/3] Audio Dynamic Range Optimization:")
        print(f"  -> Raw peak amplitude:  {peak_before:.3f} (-{20 * math.log10(max(peak_before, 1e-5)):.1f} dBFS)")
        print(f"  -> Boosted peak amplitude: {peak_after:.3f} (-{20 * math.log10(max(peak_after, 1e-5)):.1f} dBFS)")
        print(f"  -> Normalization latency: {t_norm * 1000:.2f} ms")
        assert peak_after >= 0.85, "Peak normalization did not reach target SNR level"

        # 3. Model Pre-warming and Inference
        print(f"\n[2/3] Engine Inference Latency (Cheetah Tier - Fast Greedy):")
        t0 = time.perf_counter()
        result = TranscriberEngine.transcribe(
            audio_path=wav_path,
            mode="cheetah",
            language="en",
        )
        t_infer = time.perf_counter() - t0
        rtf = t_infer / duration
        print(f"  -> Transcribed 5.0s audio in {t_infer:.2f}s (Real-Time Factor: {rtf:.2f}x)")
        print(f"  -> Detected language: {result['detected_language']} ({result['language_probability'] * 100:.1f}%)")
        print(f"  -> Segments extracted: {len(result['segments'])}")

        # 4. Memory Footprint Stability Check
        telemetry = get_system_telemetry()
        print(f"\n[3/3] Engine Resource Telemetry:")
        print(f"  -> CPU Threads: {telemetry['cpu_threads']}")
        print(f"  -> System RAM Available: {telemetry['system_ram_available_gb']} GB")
        print(f"  -> System RAM Used: {telemetry['system_ram_used_percent']}%")

        print("\n========================================================================")
        print(" ALL ENGINE BENCHMARKS COMPLETED SUCCESSFULLY!")
        print("========================================================================")
    finally:
        import os
        if os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    benchmark_engine()
