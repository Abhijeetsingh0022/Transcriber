"""
Mux Service — business logic layer for multi-audio track muxing.

Keeps API routes thin: all file I/O, DB mutations, and background threading
live here.  Follows the same pattern as job_service.py and export_service.py.
"""

import os
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from db.crud import (
    delete_mux_track,
    get_job,
    get_mux_job,
    get_mux_track,
    get_mux_tracks,
    insert_mux_track,
    reorder_mux_tracks,
    reorder_mux_tracks_list,
    swap_mux_track_indices,
    update_mux_track,
    upsert_mux_job,
)
from db.database import DATA_DIR, get_db
import av
from engine.audio import find_ffmpeg_binary
from engine.muxer import MuxError, TrackConfig, mux_multi_audio_tracks, _get_job_lock


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STEMS_DIR_NAME = "stems"          # relative to DATA_DIR/media/{job_id}/
_OUTPUTS_DIR_NAME = "mux_output"   # relative to DATA_DIR/media/{job_id}/

_ALLOWED_AUDIO_EXTENSIONS = {
    ".wav", ".mp3", ".aac", ".m4a", ".ogg", ".opus", ".flac", ".aif", ".aiff"
}


# ---------------------------------------------------------------------------
# Track management
# ---------------------------------------------------------------------------

async def service_add_track(
    job_id: str,
    file: UploadFile,
    label: str,
    language: str = "und",
    codec: str = "copy",
    bitrate: int = 192_000,
    channels: int = 2,
    sample_rate: int = 44_100,
    disposition: str = "none",
    is_default: bool = False,
) -> Dict[str, Any]:
    """
    Saves the uploaded audio file to data/media/{job_id}/stems/ and inserts
    a mux_tracks row.  Returns the newly created track dict.
    """
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")

    # Validate extension
    original_name = file.filename or "track.wav"
    suffix = Path(original_name).suffix.lower()
    if suffix not in _ALLOWED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format {suffix!r}. "
            f"Accepted: {sorted(_ALLOWED_AUDIO_EXTENSIONS)}"
        )

    stems_dir = DATA_DIR / "media" / job_id / _STEMS_DIR_NAME
    stems_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(original_name).name}"
    dest_path = stems_dir / safe_name

    # Stream upload to disk
    file_size = 0
    with open(dest_path, "wb") as buf:
        while chunk := await file.read(1024 * 1024):
            buf.write(chunk)
            file_size += len(chunk)

    if file_size == 0:
        dest_path.unlink(missing_ok=True)
        raise ValueError(f"Uploaded file {original_name!r} is empty (0 bytes).")

    track = insert_mux_track(
        job_id=job_id,
        label=label,
        filepath=str(dest_path),
        language=language,
        codec=codec,
        bitrate=bitrate,
        channels=channels,
        sample_rate=sample_rate,
        disposition=disposition,
        is_default=is_default,
    )
    return track


def service_list_tracks(job_id: str) -> List[Dict[str, Any]]:
    """Returns all mux tracks for a job, ordered by track_index."""
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")
    return get_mux_tracks(job_id)


def service_get_track_filepath(job_id: str, track_id: str) -> str:
    """Returns absolute filepath for a single mux track, verifying existence."""
    track = get_mux_track(track_id)
    if not track or track["job_id"] != job_id:
        raise FileNotFoundError(f"Track {track_id!r} not found for job {job_id!r}.")
    if not os.path.isfile(track["filepath"]):
        raise FileNotFoundError(f"Track audio file is missing on disk: {track['filepath']}")
    return track["filepath"]


def _has_video_stream(filepath: str) -> bool:
    """Checks if a media file contains at least one active video stream using PyAV."""
    try:
        container = av.open(filepath)
        try:
            return any(s.type == "video" for s in container.streams)
        finally:
            container.close()
    except Exception:
        return False


def _has_audio_stream(filepath: str) -> bool:
    """Checks if a media file contains at least one active audio stream using PyAV."""
    try:
        container = av.open(filepath)
        try:
            return any(s.type == "audio" for s in container.streams)
        finally:
            container.close()
    except Exception:
        return False


async def service_upload_video(
    job_id: str,
    file: UploadFile,
    extract_audio: bool = True,
    audio_label: str = "Video Audio (Hindi)",
    audio_language: str = "hi",
) -> Dict[str, Any]:
    """
    Saves an uploaded video file to data/media/{job_id}/mux_video/ and sets it
    as the active custom video for the mux job.
    Optionally extracts its audio stream and registers it as a stem track.
    """
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")

    original_name = file.filename or "video.mp4"
    suffix = Path(original_name).suffix.lower()
    allowed_video = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
    if suffix not in allowed_video:
        raise ValueError(f"Unsupported video format {suffix!r}. Accepted: {sorted(allowed_video)}")

    video_dir = DATA_DIR / "media" / job_id / "mux_video"
    video_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(original_name).name}"
    dest_path = video_dir / safe_name

    file_size = 0
    with open(dest_path, "wb") as buf:
        while chunk := await file.read(1024 * 1024):
            buf.write(chunk)
            file_size += len(chunk)

    if file_size == 0 or not dest_path.is_file():
        dest_path.unlink(missing_ok=True)
        raise ValueError("Uploaded video file is empty (0 bytes).")

    if not _has_video_stream(str(dest_path)):
        dest_path.unlink(missing_ok=True)
        raise ValueError("The uploaded file does not contain a valid video stream.")

    # Persist custom video path in mux_jobs
    upsert_mux_job(
        job_id=job_id,
        custom_video_path=str(dest_path),
    )

    extracted_track = None
    has_audio = _has_audio_stream(str(dest_path))
    if extract_audio and has_audio:
        stems_dir = DATA_DIR / "media" / job_id / _STEMS_DIR_NAME
        stems_dir.mkdir(parents=True, exist_ok=True)
        extracted_audio_name = f"{uuid.uuid4().hex[:8]}_{Path(original_name).stem}_audio.wav"
        extracted_audio_path = stems_dir / extracted_audio_name

        ffmpeg_bin = find_ffmpeg_binary()
        extracted_ok = False
        if ffmpeg_bin:
            try:
                subprocess.run(
                    [
                        ffmpeg_bin, "-y", "-i", str(dest_path),
                        "-vn", "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2",
                        str(extracted_audio_path)
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                    timeout=120,
                )
                extracted_ok = extracted_audio_path.is_file() and extracted_audio_path.stat().st_size > 0
            except Exception:
                pass

        if not extracted_ok:
            # PyAV fallback
            in_c = None
            out_c = None
            try:
                in_c = av.open(str(dest_path))
                out_c = av.open(str(extracted_audio_path), mode="w", format="wav")
                in_a = next((s for s in in_c.streams if s.type == "audio"), None)
                if in_a:
                    out_a = out_c.add_stream("pcm_s16le", rate=44100)
                    resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)
                    for frame in in_c.decode(in_a):
                        for rf in resampler.resample(frame):
                            for pkt in out_a.encode(rf):
                                out_c.mux(pkt)
                    for rf in resampler.resample(None):
                        for pkt in out_a.encode(rf):
                            out_c.mux(pkt)
                    for pkt in out_a.encode(None):
                        out_c.mux(pkt)
                extracted_ok = extracted_audio_path.is_file() and extracted_audio_path.stat().st_size > 0
            except Exception:
                pass
            finally:
                if out_c is not None:
                    try:
                        out_c.close()
                    except Exception:
                        pass
                if in_c is not None:
                    try:
                        in_c.close()
                    except Exception:
                        pass

        if extracted_ok:
            existing_tracks = get_mux_tracks(job_id)
            is_def = len(existing_tracks) == 0
            extracted_track = insert_mux_track(
                job_id=job_id,
                label=audio_label,
                filepath=str(extracted_audio_path),
                language=audio_language,
                codec="copy",
                bitrate=192_000,
                channels=2,
                sample_rate=44_100,
                disposition="default" if is_def else "none",
                is_default=is_def,
                gain=1.0,
                is_muted=False,
            )

    return {
        "custom_video_path": str(dest_path),
        "video_filename": Path(original_name).name,
        "file_size": file_size,
        "has_audio": has_audio,
        "extracted_track": extracted_track,
    }


def service_reset_video(job_id: str) -> Dict[str, Any]:
    """Resets the custom video back to the original project media file."""
    with get_db() as conn:
        conn.execute("UPDATE mux_jobs SET custom_video_path = NULL WHERE job_id = ?", (job_id,))
    return {"success": True, "custom_video_path": None}


def service_get_video_path(job_id: str) -> Optional[str]:
    """
    Returns the absolute path to the active video file for this job.
    Prefers custom_video_path if configured, otherwise falls back to the job's
    original media file if it contains an active video stream.
    """
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")

    mux_job = get_mux_job(job_id)
    custom_video_path = mux_job.get("custom_video_path") if mux_job else None
    if custom_video_path and os.path.isfile(custom_video_path) and _has_video_stream(custom_video_path):
        return custom_video_path

    original_filepath = job.get("filepath", "")
    if original_filepath and os.path.isfile(original_filepath):
        video_ext = Path(original_filepath).suffix.lower()
        if video_ext in {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"} and _has_video_stream(original_filepath):
            return original_filepath

    return None


def _probe_video_file(video_path: str) -> Dict[str, Any]:
    """Extracts telemetric video metadata (dimensions, fps, duration, codec) using PyAV."""
    info: Dict[str, Any] = {
        "has_video": True,
        "filepath": video_path,
        "filename": Path(video_path).name,
        "file_size": os.path.getsize(video_path) if os.path.isfile(video_path) else 0,
        "width": None,
        "height": None,
        "fps": None,
        "duration": None,
        "codec": None,
        "has_audio": False,
    }
    try:
        container = av.open(video_path)
        try:
            video_stream = next((s for s in container.streams if s.type == "video"), None)
            if video_stream:
                info["width"] = video_stream.width
                info["height"] = video_stream.height
                info["codec"] = video_stream.codec_context.name if video_stream.codec_context else None
                if video_stream.average_rate:
                    info["fps"] = round(float(video_stream.average_rate), 2)
                elif video_stream.base_rate:
                    info["fps"] = round(float(video_stream.base_rate), 2)

            info["has_audio"] = any(s.type == "audio" for s in container.streams)

            if container.duration is not None:
                info["duration"] = round(float(container.duration) / av.time_base, 3)
        finally:
            container.close()
    except Exception:
        pass

    return info


def service_get_video_info(job_id: str) -> Dict[str, Any]:
    """Extracts telemetric video metadata for the active source video."""
    video_path = service_get_video_path(job_id)
    if not video_path:
        return {"has_video": False}

    info = _probe_video_file(video_path)
    mux_job = get_mux_job(job_id)
    info["is_custom"] = bool(mux_job and mux_job.get("custom_video_path") == video_path)
    return info


def service_get_output_video_info(job_id: str) -> Dict[str, Any]:
    """Extracts telemetric video metadata for the completed muxed video output."""
    output_path = service_get_mux_output_path(job_id)
    info = _probe_video_file(output_path)
    info["is_output"] = True
    return info




def service_mute_all_tracks(job_id: str, muted: bool = True) -> List[Dict[str, Any]]:
    """Toggles mute state for all audio tracks belonging to the job."""
    with get_db() as conn:
        conn.execute("UPDATE mux_tracks SET is_muted = ? WHERE job_id = ?", (1 if muted else 0, job_id))
    return get_mux_tracks(job_id)


def service_import_original_track(job_id: str) -> Dict[str, Any]:
    """
    Imports the job's original media audio or extracted 16k wav as a track.
    Enables preserving original audio dialogue when muxing with additional stems.
    """
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")

    source_path: Optional[str] = None
    orig_path = job.get("filepath", "")
    if orig_path and os.path.isfile(orig_path):
        video_exts = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
        ext = Path(orig_path).suffix.lower()
        if ext in video_exts:
            if _has_audio_stream(orig_path):
                source_path = orig_path
            else:
                extracted = DATA_DIR / "media" / job_id / "audio_16k.wav"
                if extracted.is_file() and extracted.stat().st_size > 0:
                    source_path = str(extracted)
        else:
            source_path = orig_path
    else:
        extracted = DATA_DIR / "media" / job_id / "audio_16k.wav"
        if extracted.is_file() and extracted.stat().st_size > 0:
            source_path = str(extracted)

    if not source_path:
        raise FileNotFoundError(f"No source audio file found on disk for job {job_id!r}.")

    existing_tracks = get_mux_tracks(job_id)
    # Prevent duplicate imports
    for t in existing_tracks:
        if t.get("label") == "Original Audio" or t.get("filepath") == source_path:
            return t

    is_default = len(existing_tracks) == 0

    track = insert_mux_track(
        job_id=job_id,
        label="Original Audio",
        filepath=source_path,
        language=job.get("language") if job.get("language") and job.get("language") != "auto" else "und",
        codec="copy",
        bitrate=192_000,
        channels=2,
        sample_rate=44_100,
        disposition="default" if is_default else "none",
        is_default=is_default,
    )
    return track


def service_move_track(job_id: str, track_id: str, direction: str) -> List[Dict[str, Any]]:
    """
    Moves a track up or down in track_index order by swapping with its neighbor.
    Returns the refreshed list of tracks.
    """
    if direction not in ("up", "down"):
        raise ValueError(f"Invalid direction {direction!r}. Use 'up' or 'down'.")

    tracks = get_mux_tracks(job_id)
    idx = next((i for i, t in enumerate(tracks) if t["id"] == track_id), -1)
    if idx == -1:
        raise FileNotFoundError(f"Track {track_id!r} not found for job {job_id!r}.")

    target_idx = idx - 1 if direction == "up" else idx + 1
    if 0 <= target_idx < len(tracks):
        curr_track = tracks[idx]
        other_track = tracks[target_idx]
        swap_mux_track_indices(job_id, curr_track["id"], other_track["id"])

    return get_mux_tracks(job_id)


def service_reorder_tracks(job_id: str, track_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Sets track_index in the exact order of track_ids list.
    Returns the refreshed list of tracks.
    """
    reorder_mux_tracks_list(job_id, track_ids)
    return get_mux_tracks(job_id)


def service_update_track(
    job_id: str,
    track_id: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Partially updates a mux_tracks row. Returns updated track dict."""
    track = get_mux_track(track_id)
    if not track or track["job_id"] != job_id:
        raise FileNotFoundError(f"Track {track_id!r} not found for job {job_id!r}.")
    updated = update_mux_track(track_id, updates)
    if updated is None:
        raise FileNotFoundError(f"Track {track_id!r} disappeared during update.")
    return updated


def service_delete_track(job_id: str, track_id: str) -> bool:
    """Removes the track file from disk and its DB row. Returns True on success."""
    track = get_mux_track(track_id)
    if not track or track["job_id"] != job_id:
        raise FileNotFoundError(f"Track {track_id!r} not found for job {job_id!r}.")

    # Only remove from disk if file is inside this job's stems directory (never delete original job file)
    file_path = Path(track["filepath"])
    stems_dir = (DATA_DIR / "media" / job_id / _STEMS_DIR_NAME).resolve()
    try:
        if file_path.exists() and stems_dir in file_path.resolve().parents:
            file_path.unlink()
    except OSError:
        pass

    deleted = delete_mux_track(track_id)
    if deleted:
        reorder_mux_tracks(job_id)  # close index gap
    return deleted


# ---------------------------------------------------------------------------
# Mux trigger
# ---------------------------------------------------------------------------

import time

# ---------------------------------------------------------------------------
# Real-time in-memory progress and live activity logs
# ---------------------------------------------------------------------------

_MUX_RUNTIMES: Dict[str, Dict[str, Any]] = {}
_MUX_RUNTIMES_LOCK = threading.Lock()


def _update_runtime_progress(
    job_id: str,
    progress: float,
    stage: str,
    log_line: Optional[str] = None,
) -> None:
    with _MUX_RUNTIMES_LOCK:
        if job_id not in _MUX_RUNTIMES:
            _MUX_RUNTIMES[job_id] = {
                "progress": 0.0,
                "stage": "Initializing...",
                "logs": [],
                "updated_at": time.time(),
            }
        rt = _MUX_RUNTIMES[job_id]
        rt["progress"] = min(100.0, max(0.0, progress))
        rt["stage"] = stage
        rt["updated_at"] = time.time()
        if log_line:
            timestamp = time.strftime("%H:%M:%S")
            rt["logs"].append(f"[{timestamp}] {log_line}")
            if len(rt["logs"]) > 50:
                rt["logs"] = rt["logs"][-50:]


def service_start_mux(
    job_id: str,
    output_format: str = "mp4",
    include_video: bool = True,
    faststart: bool = True,
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> Dict[str, Any]:
    """
    Validates configured tracks, creates/resets a mux_jobs row, and
    launches the mux in a background thread.

    Returns the mux_jobs row immediately (status="processing").
    """
    # Prevent concurrent execution race condition
    lock = _get_job_lock(job_id)
    if lock.locked():
        raise ValueError("A mux operation is already in progress for this job.")

    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")

    mux_job = get_mux_job(job_id)
    custom_video_path = mux_job.get("custom_video_path") if mux_job else None

    # Video source: custom video if uploaded, otherwise original uploaded file
    video_path: Optional[str] = None
    if include_video:
        if custom_video_path and os.path.isfile(custom_video_path) and _has_video_stream(custom_video_path):
            video_path = custom_video_path
        else:
            original_filepath = job.get("filepath", "")
            if original_filepath and os.path.isfile(original_filepath):
                video_ext = Path(original_filepath).suffix.lower()
                if video_ext in {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}:
                    if _has_video_stream(original_filepath):
                        video_path = original_filepath

    tracks_rows = get_mux_tracks(job_id)
    if not tracks_rows and not (mute_all_audio and video_path):
        raise ValueError("No audio tracks configured. Add at least one track before muxing (or choose Mute All Audio with video).")

    if output_format not in ("mp4", "mkv", "mov"):
        raise ValueError(f"Unsupported output format {output_format!r}. Use mp4, mkv, or mov.")

    if mux_mode not in ("tracks", "blend"):
        mux_mode = "tracks"

    # Build TrackConfig objects from DB rows
    track_configs: List[TrackConfig] = [
        TrackConfig(
            filepath=row["filepath"],
            label=row["label"],
            language=row["language"],
            codec=row["codec"],
            bitrate=row["bitrate"],
            channels=row["channels"],
            sample_rate=row["sample_rate"],
            disposition=row["disposition"],
            is_default=bool(row["is_default"]),
            gain=float(row.get("gain") if row.get("gain") is not None else 1.0),
            is_muted=bool(row.get("is_muted", False)),
        )
        for row in tracks_rows
    ]

    # Output path
    output_dir = DATA_DIR / "media" / job_id / _OUTPUTS_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"muxed_{job_id[:8]}.{output_format}"
    output_path = str(output_dir / output_filename)

    # Initialize live runtime progress tracker
    mode_desc = "Blended Audio Mix" if mux_mode == "blend" else "Multi-Track Streams"
    mute_desc = " (All Audio Muted)" if mute_all_audio else ""
    _update_runtime_progress(
        job_id,
        0.0,
        "Initializing pipeline…",
        f"Queued mux job with {len(track_configs)} track(s) in {output_format.upper()} format [{mode_desc}{mute_desc}]"
    )

    # Mark as processing
    mux_record = upsert_mux_job(
        job_id=job_id,
        status="processing",
        output_format=output_format,
        mux_mode=mux_mode,
        mute_all_audio=mute_all_audio,
    )

    # Launch background thread (same pattern as QueueWorker)
    t = threading.Thread(
        target=_run_mux_background,
        args=(job_id, video_path, track_configs, output_path, output_format, faststart, mux_mode, mute_all_audio),
        name=f"MuxWorker-{job_id[:8]}",
        daemon=True,
    )
    t.start()

    return {
        **mux_record,
        "progress": 0.0,
        "stage": "Initializing pipeline…",
        "logs": [f"[{time.strftime('%H:%M:%S')}] Queued mux job with {len(track_configs)} track(s)"],
    }


def _run_mux_background(
    job_id: str,
    video_path: Optional[str],
    tracks: List[TrackConfig],
    output_path: str,
    output_format: str,
    faststart: bool,
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> None:
    """Background thread target — runs the mux and updates DB on completion."""
    def on_progress(pct: float, stage: str, log_line: Optional[str] = None):
        _update_runtime_progress(job_id, pct, stage, log_line)

    mode_label = "Blended Mix" if mux_mode == "blend" else "Multi-Track"
    if mute_all_audio:
        mode_label += " (Muted Audio)"
    _update_runtime_progress(
        job_id,
        2.0,
        "Preparing mux pipeline…",
        f"Queued {len(tracks)} track(s) for muxing [{mode_label}] in {output_format.upper()} format"
    )
    try:
        result = mux_multi_audio_tracks(
            video_path=video_path,
            tracks=tracks,
            output_path=output_path,
            output_format=output_format,
            faststart=faststart,
            progress_callback=on_progress,
            mux_mode=mux_mode,
            mute_all_audio=mute_all_audio,
        )
        upsert_mux_job(
            job_id=job_id,
            status="completed",
            output_path=result.output_path,
            output_format=output_format,
            mux_mode=mux_mode,
            mute_all_audio=mute_all_audio,
        )
        _update_runtime_progress(
            job_id,
            100.0,
            "Completed",
            f"Container generated and verified successfully ({result.file_size_bytes / (1024*1024):.2f} MB)"
        )
    except (MuxError, ValueError) as exc:
        upsert_mux_job(
            job_id=job_id,
            status="failed",
            error_message=str(exc),
            output_format=output_format,
            mux_mode=mux_mode,
            mute_all_audio=mute_all_audio,
        )
        _update_runtime_progress(job_id, 0.0, "Failed", f"Error: {exc}")
    except Exception as exc:
        upsert_mux_job(
            job_id=job_id,
            status="failed",
            error_message=f"Unexpected error: {exc}",
            output_format=output_format,
            mux_mode=mux_mode,
            mute_all_audio=mute_all_audio,
        )
        _update_runtime_progress(job_id, 0.0, "Failed", f"Unexpected error: {exc}")


# ---------------------------------------------------------------------------
# Status + download
# ---------------------------------------------------------------------------

def service_get_mux_status(job_id: str) -> Dict[str, Any]:
    """Returns the mux_jobs row for a job, enriched with real-time progress and logs."""
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")
    mux_record = get_mux_job(job_id)
    if not mux_record:
        return {
            "job_id": job_id,
            "status": "not_started",
            "output_path": None,
            "output_format": None,
            "error_message": None,
            "custom_video_path": None,
            "custom_video_name": None,
            "mux_mode": "tracks",
            "mute_all_audio": False,
            "progress": 0.0,
            "stage": "",
            "logs": [],
        }

    with _MUX_RUNTIMES_LOCK:
        rt = _MUX_RUNTIMES.get(job_id)

    # Check for stale / orphaned execution (e.g. server restarted while processing)
    if mux_record.get("status") == "processing":
        lock = _get_job_lock(job_id)
        if not lock.locked() and not rt:
            mux_record["status"] = "failed"
            mux_record["error_message"] = "Process was interrupted by a server restart. Click Start Multi-Track Mux to restart."
            upsert_mux_job(
                job_id=job_id,
                status="failed",
                error_message=mux_record["error_message"],
                output_format=mux_record.get("output_format", "mp4"),
                mux_mode=mux_record.get("mux_mode", "tracks"),
                mute_all_audio=bool(mux_record.get("mute_all_audio", False)),
            )
            return {
                **mux_record,
                "progress": 0.0,
                "stage": "Interrupted",
                "logs": ["Mux process was interrupted. Ready to restart."],
            }

    progress = rt.get("progress", 100.0 if mux_record.get("status") == "completed" else 0.0) if rt else (100.0 if mux_record.get("status") == "completed" else 0.0)
    stage = rt.get("stage", "Completed" if mux_record.get("status") == "completed" else "") if rt else ("Completed" if mux_record.get("status") == "completed" else "")
    logs = rt.get("logs", []) if rt else []

    custom_video_path = mux_record.get("custom_video_path")
    custom_video_name = Path(custom_video_path).name if custom_video_path else None

    return {
        **mux_record,
        "custom_video_path": custom_video_path,
        "custom_video_name": custom_video_name,
        "mux_mode": mux_record.get("mux_mode", "tracks"),
        "mute_all_audio": bool(mux_record.get("mute_all_audio", False)),
        "progress": round(progress, 1),
        "stage": stage,
        "logs": logs,
    }


def service_get_mux_output_path(job_id: str) -> str:
    """Returns the output file path if the mux completed successfully."""
    job = get_job(job_id)
    if not job:
        raise FileNotFoundError(f"Job {job_id!r} not found.")
    mux_record = get_mux_job(job_id)
    if not mux_record or mux_record.get("status") != "completed":
        raise FileNotFoundError("Mux output is not ready. Start the mux operation first.")
    output_path = mux_record.get("output_path")
    if not output_path or not os.path.isfile(output_path):
        raise FileNotFoundError("Mux output file is missing from disk.")
    return output_path
