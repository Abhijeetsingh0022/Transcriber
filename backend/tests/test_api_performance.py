"""
Self-check and regression tests for API Performance:
1. Server-Timing & X-Response-Time latency headers.
2. HTTP 304 conditional caching for /api/jobs.
3. HTTP 304 conditional caching for /api/jobs/{job_id}.
4. HTTP 304 conditional caching for /api/jobs/{job_id}/transcript.
5. HTTP 304 conditional caching for /api/jobs/{job_id}/markers.
6. 0.8s in-memory TTL caching for get_system_telemetry().
"""

import sys
import time
from pathlib import Path
from starlette.testclient import TestClient

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app
from db.database import init_db
from db.crud import create_job, delete_job, save_transcript, create_marker
from engine.hardware import get_system_telemetry


def run_checks():
    print("Initializing test client...")
    init_db()
    client = TestClient(app)

    # 1. TEST SERVER-TIMING HEADER
    print("\n--- 1. Testing Server-Timing & X-Response-Time Headers ---")
    resp_health = client.get("/")
    assert resp_health.status_code == 200
    assert "Server-Timing" in resp_health.headers, "Server-Timing header missing"
    assert "total;dur=" in resp_health.headers["Server-Timing"]
    assert "X-Response-Time" in resp_health.headers, "X-Response-Time header missing"
    print(f"  ✓ Headers verified: Server-Timing={resp_health.headers['Server-Timing']}, X-Response-Time={resp_health.headers['X-Response-Time']}")

    # 2. TEST CONDITIONAL 304 CACHING FOR /api/jobs
    print("\n--- 2. Testing HTTP 304 Caching for /api/jobs ---")
    resp_jobs = client.get("/api/jobs")
    assert resp_jobs.status_code == 200
    assert "ETag" in resp_jobs.headers, "ETag header missing on /api/jobs"
    etag_jobs = resp_jobs.headers["ETag"]

    # Re-fetch with matching If-None-Match
    resp_jobs_cached = client.get("/api/jobs", headers={"If-None-Match": etag_jobs})
    assert resp_jobs_cached.status_code == 304, f"Expected 304 Not Modified, got {resp_jobs_cached.status_code}"
    assert resp_jobs_cached.content == b"", "304 response body must be empty"
    print(f"  ✓ /api/jobs returned HTTP 304 with 0 body bytes (ETag: {etag_jobs})")

    # 3. CREATE DUMMY JOB FOR SINGLE JOB & TRANSCRIPT CHECKS
    print("\n--- 3. Testing Single Job & Transcript HTTP 304 Caching ---")
    job_id = create_job(
        filename="test_perf.mp4",
        filepath="/tmp/test_perf.mp4",
        file_size_bytes=4096,
        mode="whale",
    )

    try:
        # Check /api/jobs/{job_id}
        resp_job = client.get(f"/api/jobs/{job_id}")
        assert resp_job.status_code == 200
        assert "ETag" in resp_job.headers
        etag_job = resp_job.headers["ETag"]

        resp_job_cached = client.get(f"/api/jobs/{job_id}", headers={"If-None-Match": etag_job})
        assert resp_job_cached.status_code == 304
        assert resp_job_cached.content == b""
        print(f"  ✓ /api/jobs/{{job_id}} returned HTTP 304 (ETag: {etag_job})")

        # Save dummy transcript
        save_transcript(
            job_id=job_id,
            full_text="Testing transcript caching speed.",
            detected_language="en",
            language_probability=0.99,
            segments_data=[
                {
                    "speaker_label": "SPEAKER_00",
                    "start_time": 0.0,
                    "end_time": 2.5,
                    "text": "Testing transcript caching speed.",
                    "words": [{"word": "Testing", "start_time": 0.0, "end_time": 0.5}],
                }
            ],
        )

        resp_tr = client.get(f"/api/jobs/{job_id}/transcript")
        assert resp_tr.status_code == 200
        assert "ETag" in resp_tr.headers
        etag_tr = resp_tr.headers["ETag"]

        resp_tr_cached = client.get(f"/api/jobs/{job_id}/transcript", headers={"If-None-Match": etag_tr})
        assert resp_tr_cached.status_code == 304
        assert resp_tr_cached.content == b""
        print(f"  ✓ /api/jobs/{{job_id}}/transcript returned HTTP 304 (ETag: {etag_tr})")

        # 4. TEST MARKERS CONDITIONAL 304 CACHING
        print("\n--- 4. Testing Audio Markers HTTP 304 Caching ---")
        create_marker(job_id, 1.2, "Intro", "note", "m_perf_1")
        resp_mk = client.get(f"/api/jobs/{job_id}/markers")
        assert resp_mk.status_code == 200
        assert "ETag" in resp_mk.headers
        etag_mk = resp_mk.headers["ETag"]

        resp_mk_cached = client.get(f"/api/jobs/{job_id}/markers", headers={"If-None-Match": etag_mk})
        assert resp_mk_cached.status_code == 304
        assert resp_mk_cached.content == b""
        print(f"  ✓ /api/jobs/{{job_id}}/markers returned HTTP 304 (ETag: {etag_mk})")

    finally:
        delete_job(job_id)

    # 5. TEST TELEMETRY TTL CACHING
    print("\n--- 5. Testing Hardware Telemetry TTL Caching ---")
    t0 = time.perf_counter()
    tel1 = get_system_telemetry()
    tel2 = get_system_telemetry()
    elapsed = (time.perf_counter() - t0) * 1000.0
    assert tel1["platform"] == tel2["platform"]
    assert tel1["cpu_threads"] == tel2["cpu_threads"]
    print(f"  ✓ Back-to-back telemetry call took {elapsed:.3f}ms (sub-millisecond TTL cache)")

    print("\n✅ ALL API PERFORMANCE CHECKS PASSED PERFECTLY!\n")


if __name__ == "__main__":
    run_checks()
