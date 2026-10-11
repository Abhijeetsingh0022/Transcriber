"""
End-to-End Frontend & Backend Integration Test Suite.
Validates 100% seamless connectivity, API contracts, CORS headers, HTTP 304 caching,
and feature interactions between the Next.js frontend and FastAPI backend.
"""

import json
import uuid
from typing import Dict, Any
from starlette.testclient import TestClient

from main import app
from db.database import init_db, get_db
from db.crud import (
    create_job,
    update_job_status,
    save_transcript,
    save_intelligence,
    delete_job,
    create_marker,
    insert_mux_track,
)


def setup_module():
    init_db()


def test_cors_preflight_and_exposed_headers():
    """Validates CORS preflight headers and exposed headers for frontend client."""
    client = TestClient(app)
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,If-None-Match",
    }
    resp = client.options("/api/jobs", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Actual request must expose ETag and Server-Timing to the browser
    resp_get = client.get("/api/jobs", headers={"Origin": "http://localhost:3000"})
    assert resp_get.status_code == 200
    exposed = resp_get.headers.get("access-control-expose-headers", "").lower()
    assert "etag" in exposed
    assert "server-timing" in exposed


def test_system_status_and_settings_endpoints():
    """Validates all frontend settings, model manager, and system telemetry endpoints."""
    client = TestClient(app)

    # 1. System telemetry used by useTelemetry hook
    resp = client.get("/api/system/status")
    assert resp.status_code == 200
    telemetry = resp.json()
    assert "platform" in telemetry
    assert "cpu_threads" in telemetry
    assert "worker_status" in telemetry
    assert "queued_jobs_count" in telemetry

    # 2. Settings keys used by Settings modal
    resp_keys = client.get("/api/settings/keys")
    assert resp_keys.status_code == 200
    keys_data = resp_keys.json()
    assert "gemini_configured" in keys_data
    assert "openrouter_configured" in keys_data
    assert "tokenharbor_configured" in keys_data

    # 3. Model status used by Model Manager
    resp_models = client.get("/api/settings/models")
    assert resp_models.status_code == 200
    models_list = resp_models.json()
    assert isinstance(models_list, list)
    assert len(models_list) >= 4  # cheetah, dolphin, whale, whale_turbo

    # 4. Storage info
    resp_storage = client.get("/api/settings/storage")
    assert resp_storage.status_code == 200
    storage = resp_storage.json()
    assert "total_disk_gb" in storage
    assert "free_disk_gb" in storage


def test_complete_studio_job_lifecycle():
    """
    Validates complete studio workflow end-to-end:
    - Job listing & retrieval
    - Transcript retrieval & conditional HTTP 304 caching
    - Segment text updates (PUT and PATCH)
    - Speaker tag updates and segment reassignment
    - Topic extraction and dialogue turn clustering
    - Audio markers (pins) CRUD
    - Executive intelligence briefing
    - FTS5 full-text search
    - Mux track list and reorder
    """
    client = TestClient(app)

    # Seed job
    job_id = create_job(
        filename="Integration_Demo.mp4",
        filepath="/tmp/fake_demo.mp4",
        file_size_bytes=1024,
        mode="whale",
        language="en",
    )
    update_job_status(job_id, status="completed", duration_seconds=120.0)

    full_text = "Hello students. Today we will build a resonant LC circuit. Amit, please hand me the oscilloscope."
    segments_data = [
        {
            "segment_index": 0,
            "start_time": 0.0,
            "end_time": 4.5,
            "text": "Hello students. Today we will build a resonant LC circuit.",
            "speaker_label": "SPEAKER_00",
            "addressed_to": "Audience",
            "confidence_score": 0.98,
            "words": [
                {"word": "Hello", "start_time": 0.0, "end_time": 0.5, "confidence_score": 0.99},
                {"word": "students", "start_time": 0.6, "end_time": 1.2, "confidence_score": 0.98},
            ],
        },
        {
            "segment_index": 1,
            "start_time": 4.8,
            "end_time": 9.2,
            "text": "Amit, please hand me the oscilloscope.",
            "speaker_label": "SPEAKER_01",
            "addressed_to": "Amit",
            "confidence_score": 0.95,
            "words": [
                {"word": "Amit", "start_time": 4.8, "end_time": 5.4, "confidence_score": 0.96},
                {"word": "oscilloscope", "start_time": 7.5, "end_time": 9.0, "confidence_score": 0.94},
            ],
        },
    ]
    speakers_data = [
        {"speaker_label": "SPEAKER_00", "display_name": "Instructor", "color_hex": "#3B82F6"},
        {"speaker_label": "SPEAKER_01", "display_name": "Student", "color_hex": "#10B981"},
    ]
    save_transcript(
        job_id=job_id,
        full_text=full_text,
        detected_language="en",
        language_probability=0.99,
        segments_data=segments_data,
        speakers_data=speakers_data,
    )

    try:
        # 1. Job details
        res_job = client.get(f"/api/jobs/{job_id}")
        assert res_job.status_code == 200
        assert res_job.json()["filename"] == "Integration_Demo.mp4"

        # 2. Transcript & ETag caching
        res_tx = client.get(f"/api/jobs/{job_id}/transcript")
        assert res_tx.status_code == 200
        etag = res_tx.headers.get("etag")
        assert etag is not None
        tx_data = res_tx.json()
        assert len(tx_data["segments"]) == 2

        # Conditional 304 request
        res_304 = client.get(f"/api/jobs/{job_id}/transcript", headers={"If-None-Match": etag})
        assert res_304.status_code == 304

        # 3. Segment text edits via PUT and PATCH using actual ID returned to frontend
        seg0_id = tx_data["segments"][0]["id"]
        put_res = client.put(
            f"/api/jobs/{job_id}/segments/{seg0_id}",
            json={"text": "Hello engineering students. Today we will design a resonant LC circuit."},
        )
        assert put_res.status_code == 200

        patch_res = client.patch(
            f"/api/jobs/{job_id}/segments/{seg0_id}",
            json={"text": "Hello engineering students. Welcome to circuit design."},
        )
        assert patch_res.status_code == 200

        # Verify update in transcript
        res_updated_tx = client.get(f"/api/jobs/{job_id}/transcript")
        assert "Welcome to circuit design" in res_updated_tx.json()["segments"][0]["text"]

        # 4. Speaker label & Addressee reassignments
        res_spk = client.patch(
            f"/api/jobs/{job_id}/segments/speaker",
            json={"segment_ids": [seg0_id], "speaker_label": "SPEAKER_01"},
        )
        assert res_spk.status_code == 200
        assert res_spk.json()["speaker_label"] == "SPEAKER_01"

        res_addr = client.patch(
            f"/api/jobs/{job_id}/segments/addressee",
            json={"segment_ids": [seg0_id], "addressed_to": "Class"},
        )
        assert res_addr.status_code == 200
        assert res_addr.json()["addressed_to"] == "Class"

        # Update speaker display names
        res_spk_meta = client.patch(
            f"/api/jobs/{job_id}/speakers",
            json=[{"speaker_label": "SPEAKER_01", "display_name": "Dr. Sarah", "color_hex": "#0284C7"}],
        )
        assert res_spk_meta.status_code == 200

        # 5. Topics and Dialogue Turns
        res_topics = client.get(f"/api/jobs/{job_id}/topics")
        assert res_topics.status_code == 200
        assert "topics" in res_topics.json()

        res_dialogues = client.get(f"/api/jobs/{job_id}/dialogues")
        assert res_dialogues.status_code == 200
        assert "dialogues" in res_dialogues.json()
        assert res_dialogues.json()["turn_count"] >= 1

        # 6. Audio Markers (Pins & Bookmarks)
        marker_res = client.post(
            f"/api/jobs/{job_id}/markers",
            json={"time": 4.8, "label": "Oscilloscope Demonstration", "tag": "important"},
        )
        assert marker_res.status_code == 200
        marker_obj = marker_res.json()
        assert marker_obj["label"] == "Oscilloscope Demonstration"
        marker_id = marker_obj["id"]

        fetch_markers = client.get(f"/api/jobs/{job_id}/markers")
        assert fetch_markers.status_code == 200
        assert len(fetch_markers.json()) >= 1

        del_marker = client.delete(f"/api/jobs/{job_id}/markers/{marker_id}")
        assert del_marker.status_code == 200

        # 7. Executive Intelligence Briefing
        save_intelligence(job_id, {
            "tldr": "Dialogue session on circuit design.",
            "executive_summary": "In this session, students assembled and tested a resonant LC circuit using an oscilloscope.",
            "key_takeaways": ["LC resonance verified"],
            "action_items": [],
            "chapters": [],
            "generated_by": "Test Intelligence",
        })
        res_intel = client.get(f"/api/jobs/{job_id}/intelligence")
        assert res_intel.status_code == 200
        intel_data = res_intel.json()
        assert "tldr" in intel_data
        assert "executive_summary" in intel_data

        res_intel_export = client.get(f"/api/jobs/{job_id}/intelligence/export?format=markdown")
        assert res_intel_export.status_code == 200
        assert "content" in res_intel_export.json()

        # 8. FTS5 Full-Text Search
        res_search = client.get(f"/api/search?q=oscilloscope&job_id={job_id}")
        assert res_search.status_code == 200
        search_json = res_search.json()
        assert search_json["count"] >= 1
        assert "oscilloscope" in search_json["results"][0]["snippet"].lower()

        # 9. Mux Track List and Reordering
        t1 = insert_mux_track(job_id=job_id, label="Stem 1", filepath="/tmp/s1.wav")
        t2 = insert_mux_track(job_id=job_id, label="Stem 2", filepath="/tmp/s2.wav")

        res_tracks = client.get(f"/api/jobs/{job_id}/mux/tracks")
        assert res_tracks.status_code == 200
        assert len(res_tracks.json()) == 2

        # Test reorder endpoint
        res_reorder = client.post(
            f"/api/jobs/{job_id}/mux/tracks/reorder",
            json={"track_ids": [t2["id"], t1["id"]]},
        )
        assert res_reorder.status_code == 200
        reordered = res_reorder.json()
        assert reordered[0]["id"] == t2["id"]
        assert reordered[1]["id"] == t1["id"]

        # 10. Video info & mux status
        res_vinfo = client.get(f"/api/jobs/{job_id}/mux/video/info")
        assert res_vinfo.status_code == 200
        res_mstatus = client.get(f"/api/jobs/{job_id}/mux/status")
        assert res_mstatus.status_code == 200

    finally:
        delete_job(job_id)


def test_bulk_delete_and_clean_exit():
    """Validates bulk delete API used by dashboard job list."""
    client = TestClient(app)
    j1 = create_job(filename="j1.wav", filepath="/tmp/j1.wav", file_size_bytes=1024)
    j2 = create_job(filename="j2.wav", filepath="/tmp/j2.wav", file_size_bytes=1024)

    res = client.post("/api/jobs/delete/bulk", json={"job_ids": [j1, j2]})
    assert res.status_code == 200
    assert res.json()["deleted_count"] == 2


if __name__ == "__main__":
    test_cors_preflight_and_exposed_headers()
    test_system_status_and_settings_endpoints()
    test_complete_studio_job_lifecycle()
    test_bulk_delete_and_clean_exit()
    print("✅ All Frontend & Backend Integration Tests Passed Successfully!")
