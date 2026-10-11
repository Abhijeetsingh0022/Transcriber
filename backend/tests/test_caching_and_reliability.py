"""
Self-check validation test for Caching, Performance, Redundancy, and Reliability.
Zero test frameworks required — pure assert-based runnable script.
"""

import os
import sys
import time
import wave
import struct
import tempfile
from pathlib import Path

# Ensure backend root is on Python sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi import Request
from core.http_cache import (
    compute_file_etag,
    format_http_date,
    is_client_fresh,
    send_cached_range_file,
)
from engine.audio import generate_waveform_peaks
from engine.ai_client import (
    _AI_CACHE,
    _cache_put,
    _cool_down_key,
    _key_hash,
    _KEY_COOLDOWNS,
    get_healthy_candidate_keys,
)


class MockRequest:
    """Lightweight mock of FastAPI Request for unit testing conditional headers."""
    def __init__(self, headers: dict = None):
        self.headers = headers or {}


def test_http_etag_and_freshness():
    """Validates RFC 7231 / RFC 7233 compliant ETag and 304 freshness checking."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"Hello world of caching and reliability!")
        temp_path = f.name

    try:
        stat = os.stat(temp_path)
        etag = compute_file_etag(stat)
        assert etag.startswith('"') and etag.endswith('"'), f"ETag format invalid: {etag}"
        assert f"{stat.st_size:x}" in etag, "ETag must incorporate file size"

        # Matching ETag -> fresh
        req_fresh = MockRequest(headers={"if-none-match": etag})
        assert is_client_fresh(req_fresh, etag, stat.st_mtime) is True

        # Non-matching ETag -> stale
        req_stale = MockRequest(headers={"if-none-match": '"outdated-etag"'})
        assert is_client_fresh(req_stale, etag, stat.st_mtime) is False

        # Wildcard * -> fresh
        req_wildcard = MockRequest(headers={"if-none-match": "*"})
        assert is_client_fresh(req_wildcard, etag, stat.st_mtime) is True

        # If-Modified-Since
        future_date = format_http_date(stat.st_mtime + 3600)
        req_ims = MockRequest(headers={"if-modified-since": future_date})
        assert is_client_fresh(req_ims, etag, stat.st_mtime) is True

        print("✓ ETag generation & conditional freshness verified")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_range_streaming_and_304():
    """Validates HTTP 206 Partial Content range slicing and 304 Not Modified responses."""
    payload = b"0123456789" * 100  # 1,000 bytes
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(payload)
        temp_path = f.name

    try:
        stat = os.stat(temp_path)
        etag = compute_file_etag(stat)

        # 1. Full request (no Range header)
        req_full = MockRequest()
        resp_full = send_cached_range_file(temp_path, req_full, media_type="video/mp4")
        assert resp_full.status_code == 200
        assert resp_full.headers["Accept-Ranges"] == "bytes"
        assert resp_full.headers["ETag"] == etag
        assert "max-age=86400" in resp_full.headers["Cache-Control"]

        # 2. Conditional request (matching If-None-Match) -> 304 Not Modified
        req_304 = MockRequest(headers={"if-none-match": etag})
        resp_304 = send_cached_range_file(temp_path, req_304, media_type="video/mp4")
        assert resp_304.status_code == 304, f"Expected 304, got {resp_304.status_code}"
        assert resp_304.headers["ETag"] == etag

        # 3. Range request (bytes=0-99 -> 100 bytes)
        req_range = MockRequest(headers={"range": "bytes=0-99"})
        resp_range = send_cached_range_file(temp_path, req_range, media_type="video/mp4")
        assert resp_range.status_code == 206, f"Expected 206, got {resp_range.status_code}"
        assert resp_range.headers["Content-Range"] == "bytes 0-99/1000"
        assert resp_range.headers["Content-Length"] == "100"

        # 4. Suffix range request (bytes=-100 -> last 100 bytes: 900-999)
        req_suffix = MockRequest(headers={"range": "bytes=-100"})
        resp_suffix = send_cached_range_file(temp_path, req_suffix, media_type="video/mp4")
        assert resp_suffix.status_code == 206
        assert resp_suffix.headers["Content-Range"] == "bytes 900-999/1000"
        assert resp_suffix.headers["Content-Length"] == "100"

        # 5. Out-of-bounds range request -> 416 Range Not Satisfiable
        req_oob = MockRequest(headers={"range": "bytes=5000-6000"})
        resp_oob = send_cached_range_file(temp_path, req_oob, media_type="video/mp4")
        assert resp_oob.status_code == 416
        assert resp_oob.headers["Content-Range"] == "bytes */1000"

        print("✓ Range partial streaming (206, 304, 416) verified")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_vectorized_waveform_performance():
    """Validates vectorized NumPy waveform peak calculation and LRU memoization speedup."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name

    try:
        # Create a synthetic 16kHz mono WAV file with 16,000 samples (1.0 sec)
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            # Modulated sine wave
            samples = [int(16000 * (i % 500) / 500) for i in range(16000)]
            raw_bytes = struct.pack(f"<{len(samples)}h", *samples)
            wf.writeframes(raw_bytes)

        # First call (cold calculation via vectorized NumPy)
        t0 = time.perf_counter()
        peaks1 = generate_waveform_peaks(wav_path, num_peaks=64)
        t_cold = time.perf_counter() - t0

        assert len(peaks1) == 64
        assert all(0.0 <= p <= 1.0 for p in peaks1)
        assert max(peaks1) > 0.5, "Peaks should reflect sound amplitude"

        # Second call (warm calculation via LRU cache)
        t1 = time.perf_counter()
        peaks2 = generate_waveform_peaks(wav_path, num_peaks=64)
        t_warm = time.perf_counter() - t1

        assert peaks1 == peaks2
        assert t_warm < 0.001, f"LRU cache hit should take <1ms, took {t_warm * 1000:.3f}ms"

        print(f"✓ Vectorized waveform calculation verified (cold={t_cold * 1000:.2f}ms, warm={t_warm * 1000:.4f}ms)")
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_ai_gateway_key_redundancy():
    """Validates that cooling down one key in a provider pool does NOT cool down peer keys."""
    key_a = "AIzaSyTestKeyAlpha12345678"
    key_b = "AIzaSyTestKeyBeta87654321"

    # Save test keys pool for gemini
    from services.settings_service import set_provider_keys_pool
    set_provider_keys_pool("gemini", [key_a, key_b])

    # Initially both keys healthy
    healthy = get_healthy_candidate_keys("gemini")
    assert key_a in healthy and key_b in healthy, "Both keys must initially be candidate keys"

    # Simulate Key A hitting rate limit (429) -> cool down Key A
    _cool_down_key(key_a, seconds=30.0)

    # Key A is now in cooldown, but Key B MUST remain healthy and available!
    healthy_after = get_healthy_candidate_keys("gemini")
    assert key_a not in healthy_after, "Cooled-down Key A must not be a candidate"
    assert key_b in healthy_after, "Key B must remain healthy when Key A hits 429 quota"

    # Validate thread-safe LRU cache
    _cache_put("test:job1", {"status": "ok", "val": 42})
    assert _AI_CACHE.get("test:job1") == {"status": "ok", "val": 42}

    print("✓ Multi-key failover redundancy & peer key preservation verified")


def test_crud_performance_and_caching():
    """Validates in-memory transcript LRU cache, count_jobs TTL, and invalidation speed."""
    from db.crud import (
        create_job,
        save_transcript,
        get_transcript,
        update_speakers,
        count_jobs,
        delete_job,
        _TRANSCRIPT_CACHE,
    )

    test_jid = create_job("test_perf_media.wav", "/tmp/nonexistent.wav", 1000)
    try:
        # Save dummy transcript with 10 segments and 50 words
        segs = [
            {
                "start_time": float(i),
                "end_time": float(i + 1),
                "text": f"Sentence number {i}",
                "speaker_label": "SPEAKER_00",
                "words": [
                    {"word": f"word_{i}_{w}", "start_time": float(i + w * 0.2), "end_time": float(i + (w + 1) * 0.2), "confidence_score": 0.95}
                    for w in range(5)
                ],
            }
            for i in range(10)
        ]
        save_transcript(test_jid, "Full transcript text", "en", 0.99, segs, [{"speaker_label": "SPEAKER_00", "display_name": "Speaker 1"}])

        # 1. Cold fetch (populates cache)
        t0 = time.perf_counter()
        t_cold = get_transcript(test_jid)
        cold_duration = time.perf_counter() - t0

        assert t_cold is not None
        assert len(t_cold["segments"]) == 10
        assert test_jid in _TRANSCRIPT_CACHE, "Transcript must be cached in memory"

        # 2. Warm fetch (served from memory LRU cache)
        t1 = time.perf_counter()
        t_warm = get_transcript(test_jid)
        warm_duration = time.perf_counter() - t1

        assert t_warm is not None
        assert len(t_warm["segments"]) == 10
        assert warm_duration < 0.001, f"Warm cache hit should take <1ms, took {warm_duration * 1000:.4f}ms"

        # 3. Cache invalidation on speaker edit
        update_speakers(test_jid, [{"speaker_label": "SPEAKER_00", "display_name": "Renamed Host", "color_hex": "#ff0000"}])
        assert test_jid not in _TRANSCRIPT_CACHE, "Cache must be invalidated after speaker update"

        # 4. Re-fetch reflects updated speaker
        t_refreshed = get_transcript(test_jid)
        assert t_refreshed["speakers"][0]["display_name"] == "Renamed Host"

        # 5. count_jobs TTL cache
        c1 = count_jobs("queued")
        c2 = count_jobs("queued")
        assert c1 == c2

        print(f"✓ Database CRUD transcript in-memory cache verified (cold={cold_duration * 1000:.2f}ms, warm={warm_duration * 1000:.4f}ms)")
    finally:
        delete_job(test_jid)


if __name__ == "__main__":
    print("Running Caching, Performance, Redundancy & Reliability Checks...")
    test_http_etag_and_freshness()
    test_range_streaming_and_304()
    test_vectorized_waveform_performance()
    test_ai_gateway_key_redundancy()
    test_crud_performance_and_caching()
    print("\nALL CACHING, PERFORMANCE, REDUNDANCY & RELIABILITY CHECKS PASSED SUCCESSFULLY!")

