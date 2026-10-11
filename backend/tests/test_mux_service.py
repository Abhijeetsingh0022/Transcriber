"""
Integration test for services/mux_service.py and DB layer.
Tests track addition, updating, listing, deletion, and mux status handling.
Run: uv run python tests/test_mux_service.py
"""

import os
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

from db.crud import create_job, get_mux_tracks
from db.database import init_db
from fastapi import UploadFile
from services.mux_service import (
    service_add_track,
    service_delete_track,
    service_get_mux_status,
    service_get_track_filepath,
    service_import_original_track,
    service_list_tracks,
    service_move_track,
    service_update_track,
)


def _make_dummy_upload(filename: str, content: bytes = b"RIFF....WAVEfmt ") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


def test_mux_service_workflow():
    init_db()

    # Create dummy job
    job_id = create_job(filename="sample_video.mp4", filepath="/tmp/sample_video.mp4", file_size_bytes=1024)

    # 1. Add Track 1
    upload1 = _make_dummy_upload("stem_vocals.wav", b"RIFFdummydata1234567890")
    import asyncio
    t1 = asyncio.run(service_add_track(
        job_id=job_id,
        file=upload1,
        label="Vocals",
        language="en",
        codec="copy",
        is_default=True,
    ))
    assert t1["label"] == "Vocals"
    assert t1["language"] == "en"
    assert t1["is_default"] == 1
    assert t1["track_index"] == 0
    assert os.path.isfile(t1["filepath"])
    assert service_get_track_filepath(job_id, t1["id"]) == t1["filepath"]
    print("   add track 1 ok")

    # 2. Add Track 2 (marked as default - should demote Track 1)
    upload2 = _make_dummy_upload("stem_music.wav", b"RIFFmusicdata1234567890")
    t2 = asyncio.run(service_add_track(
        job_id=job_id,
        file=upload2,
        label="Background Music",
        language="und",
        codec="copy",
        is_default=True,
    ))
    assert t2["track_index"] == 1
    assert t2["is_default"] == 1

    tracks = service_list_tracks(job_id)
    assert len(tracks) == 2
    # Verify t1 was demoted
    assert tracks[0]["is_default"] == 0
    assert tracks[1]["is_default"] == 1
    print("   add track 2 & default mutual exclusivity ok")

    # 3. Update track 1
    updated = service_update_track(job_id, t1["id"], {"label": "Lead Vocals", "is_default": True})
    assert updated["label"] == "Lead Vocals"
    tracks_after = service_list_tracks(job_id)
    assert tracks_after[0]["is_default"] == 1
    assert tracks_after[1]["is_default"] == 0
    print("   update track ok")

    # 4. Check initial mux status
    status = service_get_mux_status(job_id)
    assert status["status"] == "not_started"
    print("   initial mux status ok")

    # 5. Delete track 1 and check index reordering
    deleted = service_delete_track(job_id, t1["id"])
    assert deleted is True
    remaining = service_list_tracks(job_id)
    assert len(remaining) == 1
    assert remaining[0]["id"] == t2["id"]
    assert remaining[0]["track_index"] == 0
    print("   delete track & reorder index ok")

    # 6. Test move track
    upload3 = _make_dummy_upload("stem_fx.wav", b"RIFFfxdata1234567890")
    t3 = asyncio.run(service_add_track(job_id=job_id, file=upload3, label="Sound FX", is_default=False))
    # remaining: [t2 (idx 0), t3 (idx 1)]
    reordered = service_move_track(job_id, t3["id"], "up")
    assert reordered[0]["id"] == t3["id"]
    assert reordered[0]["track_index"] == 0
    assert reordered[1]["id"] == t2["id"]
    assert reordered[1]["track_index"] == 1
    print("   move track up ok")

    # 7. Test import original track
    # create a mock original media file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_orig:
        tmp_orig.write(b"RIFForiginalmedia1234567890")
        tmp_orig_path = tmp_orig.name

    from db.crud import update_job_status
    from db.database import get_db
    with get_db() as conn:
        conn.execute("UPDATE jobs SET filepath = ? WHERE id = ?", (tmp_orig_path, job_id))

    orig_track = service_import_original_track(job_id)
    assert orig_track["label"] == "Original Audio"
    assert orig_track["filepath"] == tmp_orig_path
    print("   import original track ok")

    # 8. Test deleting imported original track must NOT delete the original file from disk
    service_delete_track(job_id, orig_track["id"])
    assert os.path.isfile(tmp_orig_path), "Original media file was mistakenly deleted by delete_track!"
    os.unlink(tmp_orig_path)
    print("   delete imported track preserves original media file ok")

    # Cleanup remaining tracks
    service_delete_track(job_id, t2["id"])
    service_delete_track(job_id, t3["id"])
    print("   cleanup ok")


if __name__ == "__main__":
    print("Running mux service integration test...")
    test_mux_service_workflow()
    print("All service integration tests passed successfully!")
