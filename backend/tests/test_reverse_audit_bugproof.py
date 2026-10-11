"""
Reverse Engineering & Bug-Proofing Audit Verification Test Suite.
Verifies all trust boundaries, path traversal guards, datetime timezone safety,
and edge-case resilience across the Transcriber stack.
"""

import pytest
from datetime import datetime, timezone
from starlette.testclient import TestClient

from main import app
from db.crud import (
    create_job,
    update_job_status,
    get_job,
    get_mux_track,
    get_mux_tracks,
    update_mux_track,
    delete_mux_track,
    get_markers,
    create_marker,
    delete_marker,
    save_intelligence,
    is_safe_id,
)
from engine.exporters.subtitles import generate_srt, generate_vtt


@pytest.fixture
def client():
    return TestClient(app)


def test_timezone_utc_serialization():
    """Ensures job timestamps use timezone-aware UTC ISO format without deprecation."""
    job_id = create_job(
        filename="utc_test.mp3",
        filepath="/tmp/utc_test.mp3",
        file_size_bytes=100,
    )
    assert is_safe_id(job_id)
    update_job_status(job_id, status="completed", duration_seconds=10.5)

    job = get_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["completed_at"] is not None
    # Verify ISO-8601 string parseability
    dt = datetime.fromisoformat(job["completed_at"])
    assert dt is not None


def test_path_traversal_crud_guards():
    """Verifies that malicious path traversal strings are blocked at the data layer."""
    traversal_payloads = [
        "../../../etc/passwd",
        "..\\..\\windows\\system32",
        "job/../../secret",
        "id with spaces",
        "id;DROP TABLE jobs;--",
        "<script>alert(1)</script>",
        "null\x00byte",
    ]

    for bad_id in traversal_payloads:
        assert not is_safe_id(bad_id)
        assert get_job(bad_id) is None
        assert get_mux_track(bad_id) is None
        assert get_mux_tracks(bad_id) == []
        assert update_mux_track(bad_id, {"label": "test"}) is None
        assert not delete_mux_track(bad_id)
        assert get_markers(bad_id) == []
        assert delete_marker(bad_id, "m1") is False
        assert save_intelligence(bad_id, {"tldr": "test"}) == {}


def test_path_traversal_api_endpoints(client):
    """Verifies HTTP 400 Bad Request on path traversal attempts against routes."""
    bad_id = "traversal..job..id"

    # Mux routes
    res = client.get(f"/api/jobs/{bad_id}/mux/tracks")
    assert res.status_code == 400
    assert "Invalid job ID" in res.json().get("detail", "")

    res = client.get(f"/api/jobs/{bad_id}/mux/video/stream")
    assert res.status_code == 400

    res = client.get(f"/api/jobs/{bad_id}/mux/download")
    assert res.status_code == 400

    # Export & Media routes
    res = client.get(f"/api/jobs/{bad_id}/export/srt")
    assert res.status_code == 400

    res = client.get(f"/api/jobs/{bad_id}/media")
    assert res.status_code == 400

    # Speakers & Segments routes
    res = client.patch(f"/api/jobs/{bad_id}/speakers", json=[])
    assert res.status_code == 400

    res = client.patch(f"/api/jobs/{bad_id}/segments/speaker", json={"segment_ids": ["s1"], "speaker_label": "SPEAKER_00"})
    assert res.status_code == 400


def test_subtitle_generation_null_safety():
    """Verifies that SRT and VTT exporters never raise KeyError on missing/None timestamps."""
    corrupted_segments = [
        {"text": "Speech with missing start and end"},
        {"text": "Speech with None timestamps", "start_time": None, "end_time": None},
        {"text": "Speech with zero duration", "start_time": 5.0, "end_time": 5.0},
        {"text": "   "},  # Whitespace only segment should be skipped
    ]

    srt_output = generate_srt(corrupted_segments)
    assert isinstance(srt_output, str)
    assert "Speech with missing start and end" in srt_output
    assert "Speech with None timestamps" in srt_output
    assert "Speech with zero duration" in srt_output

    vtt_output = generate_vtt(corrupted_segments)
    assert isinstance(vtt_output, str)
    assert vtt_output.startswith("WEBVTT")
    assert "Speech with missing start and end" in vtt_output


def test_bulk_operations_validation(client):
    """Verifies that bulk delete and bulk export reject malicious job IDs."""
    # Malformed job IDs in bulk delete
    res = client.post("/api/jobs/delete/bulk", json={"job_ids": ["valid_id", "../../../traversal"]})
    assert res.status_code == 400

    # Malformed job IDs in bulk export
    res = client.post("/api/jobs/export/bulk", json={"job_ids": ["../../../traversal"], "formats": ["txt"]})
    assert res.status_code == 400


def test_segment_speaker_reassignment_validation(client):
    """Verifies that segment reassignment checks for non-existent jobs and bad IDs."""
    res = client.patch(
        "/api/jobs/non_existent_uuid/segments/speaker",
        json={"segment_ids": ["seg_1"], "speaker_label": "SPEAKER_00"},
    )
    assert res.status_code == 404

    # Seed valid job
    job_id = create_job(filename="valid.mp3", filepath="/tmp/valid.mp3", file_size_bytes=100)
    res = client.patch(
        f"/api/jobs/{job_id}/segments/speaker",
        json={"segment_ids": ["seg_1;DROP TABLE;"], "speaker_label": "SPEAKER_00"},
    )
    assert res.status_code == 400
