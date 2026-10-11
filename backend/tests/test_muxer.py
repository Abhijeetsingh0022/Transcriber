"""
Self-check for engine/muxer.py.
Tests the pure _build_ffmpeg_mux_cmd and validate_track_configs functions
without spawning an actual FFmpeg process.
Run: uv run python tests/test_muxer.py
"""

import os
import sys
import tempfile
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.muxer import (
    TrackConfig,
    _build_ffmpeg_mux_cmd,
    validate_track_configs,
    MuxError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path: str, duration_s: float = 0.1, rate: int = 44100):
    """Writes a minimal valid WAV file for testing."""
    n_frames = int(rate * duration_s)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00" * n_frames * 2 * 2)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_validate_empty():
    errors = validate_track_configs([])
    assert len(errors) == 1 and "one audio track" in errors[0].lower(), errors


def test_validate_multiple_defaults():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [
            TrackConfig(filepath=f.name, label="A", is_default=True),
            TrackConfig(filepath=f.name, label="B", is_default=True),
        ]
    try:
        errors = validate_track_configs(tracks)
        assert any("is_default" in e for e in errors), errors
    finally:
        os.unlink(f.name)


def test_validate_missing_file():
    tracks = [TrackConfig(filepath="/nonexistent/file.wav", label="Missing")]
    errors = validate_track_configs(tracks)
    assert any("not found" in e for e in errors), errors


def test_validate_bad_codec():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [TrackConfig(filepath=f.name, label="X", codec="wma")]
    try:
        errors = validate_track_configs(tracks)
        assert any("codec" in e for e in errors), errors
    finally:
        os.unlink(f.name)


def test_validate_bad_channels():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [TrackConfig(filepath=f.name, label="X", channels=3)]
    try:
        errors = validate_track_configs(tracks)
        assert any("channels" in e for e in errors), errors
    finally:
        os.unlink(f.name)


def test_validate_ok():
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [TrackConfig(filepath=f.name, label="English", language="en", is_default=True)]
    try:
        errors = validate_track_configs(tracks)
        assert errors == [], errors
    finally:
        os.unlink(f.name)


def test_build_cmd_two_tracks_mp4():
    """Verify -map, -metadata, -disposition, and -movflags are present and correct."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f1, \
         tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f2:
        _make_wav(f1.name)
        _make_wav(f2.name)
        tracks = [
            TrackConfig(filepath=f1.name, label="English", language="en",
                        codec="aac", is_default=True, disposition="default"),
            TrackConfig(filepath=f2.name, label="French Dub", language="fr",
                        codec="aac", disposition="dub"),
        ]
        warnings: list = []
        cmd = _build_ffmpeg_mux_cmd(
            ffmpeg_bin="ffmpeg",
            video_path=None,
            tracks=tracks,
            output_path="/tmp/out.mp4",
            output_format="mp4",
            faststart=True,
            warnings=warnings,
        )
    try:
        os.unlink(f1.name)
        os.unlink(f2.name)
    except FileNotFoundError:
        pass

    cmd_str = " ".join(cmd)
    assert "-map 0:a:0" in cmd_str, "First track map missing"
    assert "-map 1:a:0" in cmd_str, "Second track map missing"
    assert "language=en" in cmd_str, "Track 0 language missing"
    assert "language=fr" in cmd_str, "Track 1 language missing"
    assert "title=English" in cmd_str, "Track 0 title missing"
    assert "title=French Dub" in cmd_str, "Track 1 title missing"
    assert "-disposition:a:0 default" in cmd_str, "Track 0 disposition missing"
    assert "-disposition:a:1 dub" in cmd_str, "Track 1 disposition missing"
    assert "+faststart" in cmd_str, "-movflags +faststart missing"
    assert "-f mp4" in cmd_str, "-f mp4 format missing"
    print("  cmd OK:", " ".join(cmd[:6]), "...")


def test_build_cmd_with_video():
    """Video input should produce map 0:v:0 and audio from index 1+."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [TrackConfig(filepath=f.name, label="Audio", codec="aac")]
        warnings: list = []
        cmd = _build_ffmpeg_mux_cmd(
            ffmpeg_bin="ffmpeg",
            video_path="/fake/video.mp4",
            tracks=tracks,
            output_path="/tmp/out.mp4",
            output_format="mp4",
            faststart=False,
            warnings=warnings,
        )
    os.unlink(f.name)
    cmd_str = " ".join(cmd)
    assert "-i /fake/video.mp4" in cmd_str, "Video input missing"
    assert "-map 0:v:0" in cmd_str, "Video map missing"
    assert "-map 1:a:0" in cmd_str, "Audio map should be index 1 when video is 0"
    assert "-c:v copy" in cmd_str, "-c:v copy missing"
    assert "-max_muxing_queue_size" in cmd, "-max_muxing_queue_size missing"
    last_input_idx = max(i for i, arg in enumerate(cmd) if arg == "-i")
    queue_idx = cmd.index("-max_muxing_queue_size")
    assert queue_idx > last_input_idx, "-max_muxing_queue_size must be placed after all -i inputs"


def test_build_cmd_mkv_no_faststart():
    """MKV output must NOT include -movflags +faststart."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        _make_wav(f.name)
        tracks = [TrackConfig(filepath=f.name, label="Audio", codec="aac")]
        warnings: list = []
        cmd = _build_ffmpeg_mux_cmd(
            ffmpeg_bin="ffmpeg",
            video_path=None,
            tracks=tracks,
            output_path="/tmp/out.mkv",
            output_format="mkv",
            faststart=True,  # should be ignored for MKV
            warnings=warnings,
        )
    os.unlink(f.name)
    assert "+faststart" not in " ".join(cmd), "faststart must NOT appear for MKV"
    assert "-f matroska" in " ".join(cmd), "-f matroska format missing"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_validate_empty,
        test_validate_multiple_defaults,
        test_validate_missing_file,
        test_validate_bad_codec,
        test_validate_bad_channels,
        test_validate_ok,
        test_build_cmd_two_tracks_mp4,
        test_build_cmd_with_video,
        test_build_cmd_mkv_no_faststart,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"   {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"   {t.__name__}: {e}")
        except Exception as e:
            print(f"   {t.__name__} (exception): {e}")

    total = len(tests)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)
