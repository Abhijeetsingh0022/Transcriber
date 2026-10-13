"""
Multi-Audio Track Muxing Engine.

Muxes multiple independent audio files into a single container alongside an
optional video stream, using FFmpeg -map / -disposition / -metadata per-track
flags.  Falls back to a PyAV-based encoder when no external FFmpeg binary
is available.

Public API:
    probe_stream_info(filepath) -> dict
    validate_track_configs(tracks) -> list[str]
    mux_multi_audio_tracks(video_path, tracks, output_path, ...) -> MuxResult
"""

import os
import json
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import av

from engine.audio import find_ffmpeg_binary


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------

class MuxError(Exception):
    """All mux-specific failures.  Always carries a user-facing message."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class TrackConfig:
    """Describes one audio track to include in the muxed output."""
    filepath: str                       # Absolute path to the source audio file
    label: str                          # Human-readable name, e.g. "English Dub"
    language: str = "und"               # ISO 639-1/2, e.g. "en", "fr"
    codec: str = "copy"                 # copy | aac | libopus | libmp3lame
    bitrate: int = 192_000              # bits/s; ignored when codec == "copy"
    channels: int = 2
    sample_rate: int = 44_100
    disposition: str = "none"           # default | dub | comment | hearing_impaired
    is_default: bool = False
    gain: float = 1.0                   # Volume multiplier (0.0 to 1.5+)
    is_muted: bool = False              # Whether this track is silenced in the mux


@dataclass
class MuxResult:
    """Returned by mux_multi_audio_tracks on success."""
    output_path: str
    track_count: int
    duration_seconds: float
    file_size_bytes: int
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Codec compatibility: output_format -> copy-safe source codecs
# ---------------------------------------------------------------------------
_COPY_SAFE: dict = {
    "mp4": {"aac", "mp4a"},
    "mkv": {"aac", "mp4a", "opus", "vorbis", "mp3", "ac3", "eac3", "flac", "pcm_s16le"},
    "mov": {"aac", "mp4a", "pcm_s16le", "pcm_s24le", "pcm_f32le"},
}
_PREFERRED_CODEC: dict = {
    "mp4": "aac",
    "mkv": "aac",
    "mov": "aac",
}
_CONTAINER_FORMAT_MAP: dict = {
    "mp4": "mp4",
    "mkv": "matroska",
    "mov": "mov",
}


# ---------------------------------------------------------------------------
# Per-job mux lock (prevents double-mux race)
# ---------------------------------------------------------------------------
_MUX_LOCKS: dict = {}
_MUX_LOCKS_MUTEX = threading.Lock()


def _get_job_lock(key: str) -> threading.Lock:
    with _MUX_LOCKS_MUTEX:
        if key not in _MUX_LOCKS:
            _MUX_LOCKS[key] = threading.Lock()
        return _MUX_LOCKS[key]


# ---------------------------------------------------------------------------
# Stream probing with in-memory caching
# ---------------------------------------------------------------------------

_PROBE_CACHE: dict = {}
_PROBE_CACHE_LOCK = threading.Lock()


def probe_stream_info(filepath: str) -> dict:
    """
    Returns stream metadata for an audio/video file.
    Caches results by (filepath, st_mtime_ns, st_size) to avoid repeated I/O.
    Uses ffprobe if available, falls back to PyAV.
    Result keys: codec_name, duration, channels, sample_rate, bit_rate.
    """
    cache_key = None
    try:
        st = os.stat(filepath)
        cache_key = (filepath, st.st_mtime_ns, st.st_size)
        with _PROBE_CACHE_LOCK:
            if cache_key in _PROBE_CACHE:
                return dict(_PROBE_CACHE[cache_key])
    except OSError:
        pass

    res = None
    ffmpeg_bin = find_ffmpeg_binary()
    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin and ffmpeg_bin:
        candidate = str(Path(ffmpeg_bin).parent / "ffprobe")
        if os.path.isfile(candidate):
            ffprobe_bin = candidate

    if ffprobe_bin and os.path.isfile(ffprobe_bin):
        try:
            result = subprocess.run(
                [
                    ffprobe_bin, "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-select_streams", "a:0",
                    filepath,
                ],
                capture_output=True, text=True, timeout=30, check=True,
            )
            streams = json.loads(result.stdout).get("streams", [])
            if streams:
                s = streams[0]
                res = {
                    "codec_name": s.get("codec_name", "unknown"),
                    "duration": float(s.get("duration", 0)),
                    "channels": int(s.get("channels", 2)),
                    "sample_rate": int(s.get("sample_rate", 44100)),
                    "bit_rate": int(s.get("bit_rate", 0)),
                }
        except Exception:
            pass  # fall through to PyAV

    if res is None:
        # PyAV fallback
        try:
            container = av.open(filepath)
            try:
                audio = next((s for s in container.streams if s.type == "audio"), None)
                if audio:
                    tb = float(audio.time_base) if audio.time_base else 1.0
                    duration = float(audio.duration or 0) * tb
                    if duration <= 0 and container.duration:
                        duration = float(container.duration) / av.time_base
                    res = {
                        "codec_name": audio.codec_context.name,
                        "duration": duration,
                        "channels": audio.codec_context.channels,
                        "sample_rate": audio.codec_context.sample_rate,
                        "bit_rate": audio.bit_rate or 0,
                    }
                else:
                    # Video-only or silent container fallback
                    video = next((s for s in container.streams if s.type == "video"), None)
                    if video:
                        dur = float(container.duration or 0) / av.time_base if container.duration else 0.0
                        res = {
                            "codec_name": video.codec_context.name if video.codec_context else "video",
                            "duration": dur,
                            "channels": 0,
                            "sample_rate": 0,
                            "bit_rate": container.bit_rate or 0,
                        }
                    else:
                        raise MuxError(f"No audio or video stream in file: {filepath}")
            finally:
                container.close()
        except MuxError:
            raise
        except Exception as exc:
            raise MuxError(f"Cannot probe stream info for {filepath}: {exc}") from exc

    if cache_key and res:
        with _PROBE_CACHE_LOCK:
            _PROBE_CACHE[cache_key] = res

    return dict(res)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_track_configs(
    tracks: List[TrackConfig],
    mute_all_audio: bool = False,
    video_path: Optional[str] = None,
) -> List[str]:
    """
    Returns a list of human-readable error strings.
    Empty list = all configs are valid.  Does NOT raise.
    """
    errors: List[str] = []
    if not tracks and not (mute_all_audio and video_path):
        errors.append("At least one audio track is required (or mute_all_audio with video).")
        return errors

    default_count = sum(1 for t in tracks if t.is_default)
    if default_count > 1:
        errors.append(f"At most one track may be marked is_default; found {default_count}.")

    valid_dispositions = {"none", "default", "dub", "comment", "hearing_impaired", "lyrics", "karaoke"}
    valid_codecs = {"copy", "aac", "libopus", "libmp3lame", "ac3", "eac3", "flac", "pcm_s16le"}

    for i, track in enumerate(tracks):
        prefix = f"Track {i} ({track.label!r})"
        if not track.filepath or not os.path.isfile(track.filepath):
            errors.append(f"{prefix}: file not found at {track.filepath!r}.")
        if track.codec not in valid_codecs:
            errors.append(f"{prefix}: unsupported codec {track.codec!r}.")
        if track.disposition not in valid_dispositions:
            errors.append(f"{prefix}: unsupported disposition {track.disposition!r}.")
        if not (8_000 <= track.bitrate <= 2_000_000):
            errors.append(f"{prefix}: bitrate {track.bitrate} out of range [8000, 2000000].")
        if track.channels not in (1, 2, 6, 8):
            errors.append(f"{prefix}: channels must be 1, 2, 6, or 8 (got {track.channels}).")

    return errors


# ---------------------------------------------------------------------------
# FFmpeg command construction  (pure function — fully unit-testable)
# ---------------------------------------------------------------------------

def _build_ffmpeg_mux_cmd(
    ffmpeg_bin: str,
    video_path: Optional[str],
    tracks: List[TrackConfig],
    output_path: str,
    output_format: str,
    faststart: bool,
    warnings: List[str],
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> List[str]:
    """
    Pure function that assembles the complete FFmpeg command list.
    Supports:
      - mute_all_audio: creates a muted video stream (-an)
      - mux_mode="tracks": multi-audio selectable stream container
      - mux_mode="blend": blends multiple audio stems via amix into one stream
      - individual track gains and mute states
    """
    cmd = [
        ffmpeg_bin,
        "-y",
        "-loglevel", "error",
        "-threads", "0",
    ]

    active_tracks: List[TrackConfig] = []
    if not mute_all_audio:
        active_tracks = [t for t in tracks if not t.is_muted and t.gain > 0.001]

    # Case A: All audio muted or no active tracks
    if not active_tracks:
        if video_path:
            cmd += [
                "-i", video_path,
                "-map", "0:v:0",
                "-c:v", "copy",
                "-an",
            ]
            if faststart and output_format == "mp4":
                cmd += ["-movflags", "+faststart"]
            mux_fmt = _CONTAINER_FORMAT_MAP.get(output_format, output_format)
            cmd += ["-f", mux_fmt]
            cmd += ["-max_muxing_queue_size", "2048"]
            cmd += ["-progress", "pipe:1"]
            cmd.append(output_path)
            return cmd
        else:
            raise MuxError("Cannot generate output: video is absent and all audio is muted.")

    # Inputs
    input_index = 0
    audio_input_indices: List[int] = []

    if video_path:
        cmd += ["-i", video_path]
        input_index += 1

    for track in active_tracks:
        cmd += ["-i", track.filepath]
        audio_input_indices.append(input_index)
        input_index += 1

    # Video stream mapping (lossless copy)
    if video_path:
        cmd += ["-map", "0:v:0", "-c:v", "copy"]

    copy_safe = _COPY_SAFE.get(output_format, set())
    preferred = _PREFERRED_CODEC.get(output_format, "aac")

    # Mode 1: Multi-Audio Track Streams (Selectable)
    if mux_mode == "tracks" or len(active_tracks) == 1:
        for i, (idx, track) in enumerate(zip(audio_input_indices, active_tracks)):
            cmd += ["-map", f"{idx}:a:0"]

            # If gain is altered, re-encode to apply volume filter
            if abs(track.gain - 1.0) > 0.01:
                cmd += [
                    f"-filter:a:{i}", f"volume={track.gain:.2f}",
                    f"-c:a:{i}", "aac",
                    f"-b:a:{i}", str(track.bitrate),
                    f"-ar:{i}", str(track.sample_rate),
                    f"-ac:{i}", str(track.channels),
                ]
            else:
                effective_codec = track.codec
                if effective_codec == "copy":
                    try:
                        src_codec = probe_stream_info(track.filepath).get("codec_name", "")
                        if src_codec not in copy_safe:
                            effective_codec = preferred
                            warnings.append(
                                f"Track {i} ({track.label!r}): '{src_codec}' not copy-safe in "
                                f"{output_format!r}; re-encoding as {preferred!r}."
                            )
                    except MuxError:
                        effective_codec = preferred
                        warnings.append(
                            f"Track {i} ({track.label!r}): could not probe codec; re-encoding as {preferred!r}."
                        )

                if effective_codec == "copy":
                    cmd += [f"-c:a:{i}", "copy"]
                else:
                    cmd += [
                        f"-c:a:{i}", effective_codec,
                        f"-b:a:{i}", str(track.bitrate),
                        f"-ar:{i}", str(track.sample_rate),
                        f"-ac:{i}", str(track.channels),
                    ]

            # Per-track metadata & disposition
            cmd += [f"-metadata:s:a:{i}", f"language={track.language}"]
            cmd += [f"-metadata:s:a:{i}", f"title={track.label}"]
            if track.is_default and track.disposition not in ("none", "default"):
                disposition_arg = f"default+{track.disposition}"
            elif track.is_default:
                disposition_arg = "default"
            else:
                disposition_arg = "0" if track.disposition == "none" else track.disposition
            cmd += [f"-disposition:a:{i}", disposition_arg]

    # Mode 2: Blended Audio Mix (Simultaneous multi-audio overlay)
    else:
        filter_parts: List[str] = []
        mix_inputs: List[str] = []
        for i, (idx, track) in enumerate(zip(audio_input_indices, active_tracks)):
            vlabel = f"a{i}"
            filter_parts.append(f"[{idx}:a:0]volume={track.gain:.2f}[{vlabel}]")
            mix_inputs.append(f"[{vlabel}]")

        filter_parts.append(
            f"{''.join(mix_inputs)}amix=inputs={len(active_tracks)}:duration=longest:dropout_transition=2:normalize=0[aout]"
        )
        default_track = next((t for t in active_tracks if t.is_default), active_tracks[0] if active_tracks else None)
        blend_lang = default_track.language if default_track and default_track.language else "und"
        labels = [t.label for t in active_tracks if t.label]
        blend_title = f"Blended Mix ({' + '.join(labels)})" if (labels and len(labels) <= 3) else "Blended Audio Mix"

        cmd += [
            "-filter_complex", ";".join(filter_parts),
            "-map", "[aout]",
            "-c:a", "aac",
            "-b:a", "192000",
            "-ar", "44100",
            "-ac", "2",
            "-metadata:s:a:0", f"language={blend_lang}",
            "-metadata:s:a:0", f"title={blend_title}",
            "-disposition:a:0", "default",
        ]

    # Container flags & output options (must be placed after all -i inputs)
    if faststart and output_format == "mp4":
        cmd += ["-movflags", "+faststart"]

    mux_fmt = _CONTAINER_FORMAT_MAP.get(output_format, output_format)
    cmd += ["-f", mux_fmt]

    cmd += ["-max_muxing_queue_size", "2048"]
    cmd += ["-progress", "pipe:1"]
    cmd.append(output_path)
    return cmd


# ---------------------------------------------------------------------------
# Progress reporting helper
# ---------------------------------------------------------------------------

def _notify_progress(
    cb: Optional[Callable],
    pct: float,
    stage: str,
    log_line: Optional[str] = None,
) -> None:
    """Safe callback dispatcher supporting 2-arg or 3-arg progress callbacks."""
    if not cb:
        return
    try:
        cb(pct, stage, log_line)
    except TypeError:
        try:
            cb(pct, stage)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# FFmpeg execution with live progress streaming
# ---------------------------------------------------------------------------

def _mux_via_ffmpeg(
    cmd: List[str],
    total_duration_s: float = 0.0,
    progress_callback: Optional[Callable] = None,
    timeout: int = 3600,
) -> None:
    """Runs the assembled FFmpeg command, parsing stdout line-by-line for live progress."""
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )
    except OSError as exc:
        raise MuxError(f"Failed to launch FFmpeg: {exc}") from exc

    last_notify_time = 0.0
    latest_speed = "1.0x"

    if proc.stdout:
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line or "=" not in line:
                continue
            key, _, val = line.partition("=")
            if key == "speed" and val != "N/A":
                latest_speed = val.strip()
            elif key == "out_time":
                now = time.time()
                if now - last_notify_time >= 0.35:
                    last_notify_time = now
                    time_str = val.split(".")[0]
                    pct = 35.0
                    if total_duration_s > 0:
                        parts = time_str.split(":")
                        if len(parts) == 3:
                            try:
                                el_s = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                                pct = min(88.0, 25.0 + (el_s / total_duration_s) * 63.0)
                            except ValueError:
                                pass
                    _notify_progress(
                        progress_callback,
                        round(pct, 1),
                        f"Multiplexing streams ({time_str}, {latest_speed})",
                        f"Muxing position: {time_str} (speed: {latest_speed})"
                    )

    stderr_text = proc.stderr.read() if proc.stderr else ""
    proc.wait(timeout=timeout)

    if proc.returncode != 0:
        stderr_tail = "\n".join(stderr_text.strip().splitlines()[-30:])
        raise MuxError(f"FFmpeg exited with code {proc.returncode}:\n{stderr_tail}")


# ---------------------------------------------------------------------------
# PyAV fallback (audio-only, no faststart)
# ---------------------------------------------------------------------------

def _mux_via_pyav_fallback(
    video_path: Optional[str],
    tracks: List[TrackConfig],
    output_path: str,
    output_format: str,
) -> None:
    """
    Re-encodes all tracks to AAC and muxes using PyAV.
    Used when no external FFmpeg binary is installed.

    ponytail: no video passthrough and no -movflags faststart in this path;
    upgrade by ensuring FFmpeg is installed (the preferred path always wins).
    """
    if video_path:
        raise MuxError(
            "Video muxing requires an external FFmpeg binary. "
            "Install FFmpeg and retry, or set include_video=False."
        )

    preferred_codec = _PREFERRED_CODEC.get(output_format, "aac")
    target_fmt = "mp4" if output_format in ("mp4", "mov") else "matroska"

    in_containers: List[av.container.InputContainer] = []
    container_out = av.open(output_path, mode="w", format=target_fmt)
    try:
        out_streams = []
        resamplers = []

        for track in tracks:
            cin = av.open(track.filepath)
            in_containers.append(cin)
            audio_in = next((s for s in cin.streams if s.type == "audio"), None)
            if not audio_in:
                raise MuxError(f"Track {track.label!r}: no audio stream in {track.filepath!r}.")
            out_stream = container_out.add_stream(preferred_codec, rate=track.sample_rate)
            out_stream.bit_rate = track.bitrate
            out_streams.append(out_stream)
            resamplers.append(av.AudioResampler(format="fltp", layout="stereo", rate=track.sample_rate))

        for cin, out_stream, resampler in zip(in_containers, out_streams, resamplers):
            audio_in = next(s for s in cin.streams if s.type == "audio")
            for frame in cin.decode(audio_in):
                for rf in resampler.resample(frame):
                    for pkt in out_stream.encode(rf):
                        container_out.mux(pkt)
            for rf in resampler.resample(None):
                for pkt in out_stream.encode(rf):
                    container_out.mux(pkt)
            for pkt in out_stream.encode(None):
                container_out.mux(pkt)
    finally:
        container_out.close()
        for cin in in_containers:
            cin.close()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def mux_multi_audio_tracks(
    video_path: Optional[str],
    tracks: List[TrackConfig],
    output_path: str,
    output_format: str = "mp4",
    faststart: bool = True,
    job_id: Optional[str] = None,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> MuxResult:
    """
    Muxes multiple audio tracks (and an optional video) into a single output file.

    Writes to a .tmp file first, then atomically renames on success so the
    output_path is either complete or absent — never partially written.
    """
    lock = _get_job_lock(job_id or output_path)
    if not lock.acquire(blocking=False):
        raise MuxError("A mux operation for this job is already in progress.")
    try:
        return _do_mux(
            video_path, tracks, output_path, output_format,
            faststart, progress_callback, mux_mode, mute_all_audio
        )
    finally:
        lock.release()


def _do_mux(
    video_path: Optional[str],
    tracks: List[TrackConfig],
    output_path: str,
    output_format: str,
    faststart: bool,
    progress_callback: Optional[Callable[[float, str], None]],
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> MuxResult:
    errors = validate_track_configs(tracks, mute_all_audio=mute_all_audio, video_path=video_path)
    if errors:
        raise ValueError("Track validation failed:\n" + "\n".join(f"  • {e}" for e in errors))

    if video_path and not os.path.isfile(video_path):
        raise MuxError(f"Video file not found: {video_path!r}")

    if output_format not in ("mp4", "mkv", "mov"):
        raise MuxError(f"Unsupported output format: {output_format!r}. Use mp4, mkv, or mov.")

    out_path = Path(output_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f"{out_path.stem}.tmp{out_path.suffix}")

    warnings: List[str] = []

    _notify_progress(progress_callback, 5.0, "Validating stream configs & probing inputs…", "Validating stream configs and input audio tracks...")

    # Probe duration for progress calculation
    total_duration_s = 0.0
    if video_path:
        try:
            total_duration_s = float(probe_stream_info(video_path).get("duration", 0.0))
            _notify_progress(progress_callback, 10.0, "Probed video stream container…", f"Video stream detected ({total_duration_s:.1f}s)")
        except Exception:
            pass
    if total_duration_s <= 0 and tracks:
        try:
            total_duration_s = float(probe_stream_info(tracks[0].filepath).get("duration", 0.0))
        except Exception:
            pass

    _notify_progress(progress_callback, 15.0, f"Configuring {len(tracks)} audio track(s)…", f"Configuring {len(tracks)} audio channel mappings")

    try:
        ffmpeg_bin = find_ffmpeg_binary()

        if ffmpeg_bin:
            cmd = _build_ffmpeg_mux_cmd(
                ffmpeg_bin=ffmpeg_bin,
                video_path=video_path,
                tracks=tracks,
                output_path=str(tmp_path),
                output_format=output_format,
                faststart=faststart,
                warnings=warnings,
                mux_mode=mux_mode,
                mute_all_audio=mute_all_audio,
            )
            _notify_progress(
                progress_callback,
                22.0,
                f"Starting FFmpeg mux engine ({len(tracks)} track(s))…",
                f"Spawned FFmpeg mux pipeline in {output_format.upper()} format"
            )
            _mux_via_ffmpeg(
                cmd=cmd,
                total_duration_s=total_duration_s,
                progress_callback=progress_callback,
            )
        else:
            _notify_progress(
                progress_callback,
                22.0,
                "FFmpeg not found — using PyAV fallback…",
                "FFmpeg binary not detected; using PyAV fallback"
            )
            _mux_via_pyav_fallback(video_path, tracks, str(tmp_path), output_format)

        # Atomic rename: output_path is either complete or absent
        _notify_progress(progress_callback, 90.0, "Finalizing container file…", "Atomic swap: renaming temporary container to final path")
        tmp_path.replace(out_path)

    except (MuxError, ValueError):
        tmp_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        tmp_path.unlink(missing_ok=True)
        raise MuxError(f"Disk/IO error during mux: {exc}") from exc
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise MuxError(f"Unexpected error during mux: {exc}") from exc

    _notify_progress(progress_callback, 95.0, "Probing output container…", "Probing output file header and verifying integrity")

    try:
        duration = probe_stream_info(str(out_path)).get("duration", 0.0)
    except MuxError:
        duration = 0.0

    file_size = out_path.stat().st_size
    size_mb = file_size / (1024 * 1024)

    _notify_progress(
        progress_callback,
        100.0,
        "Mux completed.",
        f"Mux complete! Generated {size_mb:.2f} MB file with {len(tracks)} audio track(s)"
    )

    return MuxResult(
        output_path=str(out_path),
        track_count=len(tracks),
        duration_seconds=duration,
        file_size_bytes=file_size,
        warnings=warnings,
    )
