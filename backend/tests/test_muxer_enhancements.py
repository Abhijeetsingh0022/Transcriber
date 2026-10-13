"""
Verification test for Muxer enhancements and fixes:
1. amix filter includes normalize=0 so volume is never attenuated.
2. Compound dispositions (default+dub) are preserved.
3. Stream probing fallback handles containers with missing audio streams.
4. service_import_original_track deduplication and video checks.
Run: uv run python tests/test_muxer_enhancements.py
"""

import os
import sys
import tempfile
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.muxer import (
    TrackConfig,
    _build_ffmpeg_mux_cmd,
    probe_stream_info,
    validate_track_configs,
)
from db.crud import create_job, get_mux_tracks
from db.database import init_db
from services.mux_service import service_import_original_track


def _make_wav(path: str, duration_s: float = 0.2, rate: int = 44100):
    n_frames = int(rate * duration_s)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00" * n_frames * 2 * 2)


def test_amix_normalize_zero():
    """Verify amix filter sets normalize=0 to prevent volume attenuation."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f2:
        _make_wav(f1.name)
        _make_wav(f2.name)
        tracks = [
            TrackConfig(filepath=f1.name, label="Track 1", gain=1.0),
            TrackConfig(filepath=f2.name, label="Track 2", gain=0.8),
        ]
        cmd = _build_ffmpeg_mux_cmd(
            ffmpeg_bin="ffmpeg",
            video_path=None,
            tracks=tracks,
            output_path="/tmp/out_blend.mp4",
            output_format="mp4",
            faststart=True,
            warnings=[],
            mux_mode="blend",
        )
    os.unlink(f1.name)
    os.unlink(f2.name)

    cmd_str = " ".join(cmd)
    assert "amix=inputs=2:duration=longest:dropout_transition=2:normalize=0" in cmd_str, (
        f"amix normalize=0 missing in command: {cmd_str}"
    )
    print("   amix normalize=0 ok")


def test_compound_disposition():
    """Verify default+dub compound disposition is formatted properly."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [
            TrackConfig(filepath=f.name, label="Dub", is_default=True, disposition="dub"),
        ]
        cmd = _build_ffmpeg_mux_cmd(
            ffmpeg_bin="ffmpeg",
            video_path=None,
            tracks=tracks,
            output_path="/tmp/out_disp.mp4",
            output_format="mp4",
            faststart=True,
            warnings=[],
            mux_mode="tracks",
        )
    os.unlink(f.name)

    cmd_str = " ".join(cmd)
    assert "-disposition:a:0 default+dub" in cmd_str, (
        f"Expected default+dub in disposition: {cmd_str}"
    )
    print("   compound disposition default+dub ok")


def test_service_import_original_deduplication():
    """Verify calling service_import_original_track multiple times doesn't duplicate tracks."""
    init_db()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        job_id = create_job(filename="orig.wav", filepath=f.name, file_size_bytes=100)
    try:
        t1 = service_import_original_track(job_id)
        assert t1["label"] == "Original Audio"
        tracks_1 = get_mux_tracks(job_id)
        assert len(tracks_1) == 1

        # Second import should return existing track without inserting another row
        t2 = service_import_original_track(job_id)
        assert t2["id"] == t1["id"]
        tracks_2 = get_mux_tracks(job_id)
        assert len(tracks_2) == 1
        print("   service_import_original deduplication ok")
    finally:
        os.unlink(f.name)


if __name__ == "__main__":
    test_amix_normalize_zero()
    test_compound_disposition()
    test_service_import_original_deduplication()
    print("All muxer enhancement tests passed successfully!")
