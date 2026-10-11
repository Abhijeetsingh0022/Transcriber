"""
Mux API routes: track management and mux trigger/status/download.

POST   /jobs/{job_id}/mux/tracks              — upload an audio track
GET    /jobs/{job_id}/mux/tracks              — list configured tracks
PATCH  /jobs/{job_id}/mux/tracks/{track_id}  — update track metadata
DELETE /jobs/{job_id}/mux/tracks/{track_id}  — remove a track

POST   /jobs/{job_id}/mux/start              — trigger mux (background)
GET    /jobs/{job_id}/mux/status             — poll mux job status
GET    /jobs/{job_id}/mux/download           — download the muxed file
"""

import mimetypes
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from services.mux_service import (
    service_add_track,
    service_delete_track,
    service_get_mux_output_path,
    service_get_mux_status,
    service_get_output_video_info,
    service_get_track_filepath,
    service_get_video_info,
    service_get_video_path,
    service_import_original_track,
    service_list_tracks,
    service_move_track,
    service_mute_all_tracks,
    service_reorder_tracks,
    service_reset_video,
    service_start_mux,
    service_update_track,
    service_upload_video,
)

router = APIRouter()


from core.http_cache import send_cached_range_file
from db.crud import is_safe_id


def _check_id(job_id: str, track_id: Optional[str] = None):
    """Enforces strict alphanumeric validation on path parameters to prevent traversal."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if track_id is not None and not is_safe_id(track_id):
        raise HTTPException(status_code=400, detail="Invalid track ID")


def _send_file_range(file_path: str, request: Request, media_type: str):
    """Streams a local media file supporting HTTP 206 Partial Content and RFC 7231 / 7233 304 caching."""
    return send_cached_range_file(file_path, request, media_type=media_type)




# ---------------------------------------------------------------------------
# Pydantic schemas (kept minimal — only what the route actually needs)
# ---------------------------------------------------------------------------

class TrackUpdateRequest(BaseModel):
    label: Optional[str] = None
    language: Optional[str] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    disposition: Optional[str] = None
    is_default: Optional[bool] = None
    gain: Optional[float] = None
    is_muted: Optional[bool] = None


class MuxStartRequest(BaseModel):
    output_format: str = "mp4"      # mp4 | mkv | mov
    include_video: bool = True
    faststart: bool = True
    mux_mode: str = "tracks"        # tracks | blend
    mute_all_audio: bool = False


class MuteAllRequest(BaseModel):
    muted: bool = True


# ---------------------------------------------------------------------------
# Track endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/mux/tracks")
@router.post("/jobs/{job_id}/mux/tracks/upload")
async def add_mux_track(
    job_id: str,
    file: UploadFile = File(...),
    label: str = Form(...),
    language: str = Form("und"),
    codec: str = Form("copy"),
    bitrate: int = Form(192_000),
    channels: int = Form(2),
    sample_rate: int = Form(44_100),
    disposition: str = Form("none"),
    is_default: bool = Form(False),
):
    """Uploads an audio file and registers it as a mux track for the job."""
    _check_id(job_id)
    try:
        track = await service_add_track(
            job_id=job_id,
            file=file,
            label=label,
            language=language,
            codec=codec,
            bitrate=bitrate,
            channels=channels,
            sample_rate=sample_rate,
            disposition=disposition,
            is_default=is_default,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return track


@router.get("/jobs/{job_id}/mux/tracks")
def list_mux_tracks(job_id: str):
    """Returns all configured audio tracks for a job."""
    _check_id(job_id)
    try:
        return service_list_tracks(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/jobs/{job_id}/mux/tracks/{track_id}")
def update_mux_track(job_id: str, track_id: str, payload: TrackUpdateRequest):
    """Partially updates a track's metadata (label, language, codec, etc.)."""
    _check_id(job_id, track_id)
    updates = payload.model_dump(exclude_none=True)
    try:
        return service_update_track(job_id, track_id, updates)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/jobs/{job_id}/mux/tracks/{track_id}")
def delete_mux_track(job_id: str, track_id: str):
    """Removes a track from the job (deletes file from disk and DB row)."""
    _check_id(job_id, track_id)
    try:
        service_delete_track(job_id, track_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"success": True, "track_id": track_id}


@router.get("/jobs/{job_id}/mux/tracks/{track_id}/audio")
@router.get("/jobs/{job_id}/mux/tracks/{track_id}/stream")
def stream_mux_track_audio(job_id: str, track_id: str, request: Request):
    """Streams the audio file of a specific mux track for previewing, supporting range requests."""
    _check_id(job_id, track_id)
    try:
        filepath = service_get_track_filepath(job_id, track_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    if not filepath or not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail="Track audio file not found.")
    mime_type, _ = mimetypes.guess_type(filepath)
    content_type = mime_type or "audio/mpeg"
    return _send_file_range(
        file_path=filepath,
        request=request,
        media_type=content_type,
    )


@router.post("/jobs/{job_id}/mux/tracks/import-original")
def import_original_track(job_id: str):
    """Imports the original media audio or extracted 16k wav as a track."""
    _check_id(job_id)
    try:
        return service_import_original_track(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/jobs/{job_id}/mux/tracks/{track_id}/move")
def move_mux_track(job_id: str, track_id: str, direction: str = "up"):
    """Moves a track up or down in order. direction = 'up' | 'down'."""
    _check_id(job_id, track_id)
    try:
        return service_move_track(job_id, track_id, direction)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class ReorderTracksPayload(BaseModel):
    track_ids: List[str]


@router.post("/jobs/{job_id}/mux/tracks/reorder")
def reorder_mux_tracks_route(job_id: str, payload: ReorderTracksPayload):
    """Sets track order given an explicit list of track IDs."""
    _check_id(job_id)
    if any(not is_safe_id(tid) for tid in payload.track_ids):
        raise HTTPException(status_code=400, detail="One or more invalid track IDs")
    try:
        return service_reorder_tracks(job_id, payload.track_ids)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# Video source & track batch endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/mux/video")
@router.post("/jobs/{job_id}/mux/video/upload")
async def upload_mux_video(
    job_id: str,
    file: UploadFile = File(...),
    extract_audio: bool = Form(True),
    audio_label: str = Form("Video Audio (Hindi)"),
    audio_language: str = Form("hi"),
):
    """Uploads a custom video file for muxing, optionally extracting its audio track."""
    _check_id(job_id)
    try:
        return await service_upload_video(
            job_id=job_id,
            file=file,
            extract_audio=extract_audio,
            audio_label=audio_label,
            audio_language=audio_language,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/jobs/{job_id}/mux/video")
@router.post("/jobs/{job_id}/mux/video/reset")
def reset_mux_video(job_id: str):
    """Resets the custom video back to the original project video file."""
    _check_id(job_id)
    try:
        return service_reset_video(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/mux/video/info")
def get_mux_video_info(job_id: str):
    """Returns video telemetric metadata (resolution, fps, duration, codec) for the active video."""
    _check_id(job_id)
    try:
        return service_get_video_info(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/mux/video/stream")
def stream_mux_video(job_id: str, request: Request):
    """Streams the active video file supporting HTTP 206 Partial Content (range requests)."""
    _check_id(job_id)
    try:
        video_path = service_get_video_path(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not video_path or not os.path.isfile(video_path):
        raise HTTPException(status_code=404, detail="No active video found for this job.")

    mime_type, _ = mimetypes.guess_type(video_path)
    content_type = mime_type or "video/mp4"

    return _send_file_range(
        file_path=video_path,
        request=request,
        media_type=content_type,
    )



@router.post("/jobs/{job_id}/mux/mute-all")
def mute_all_tracks(job_id: str, payload: MuteAllRequest):
    """Mutes or unmutes all audio tracks for this job."""
    _check_id(job_id)
    try:
        return service_mute_all_tracks(job_id, muted=payload.muted)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ---------------------------------------------------------------------------
# Mux operation endpoints
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/mux")
@router.post("/jobs/{job_id}/mux/start")
def start_mux(job_id: str, payload: MuxStartRequest):
    """Triggers the mux operation in a background thread. Returns immediately."""
    _check_id(job_id)
    try:
        mux_record = service_start_mux(
            job_id=job_id,
            output_format=payload.output_format,
            include_video=payload.include_video,
            faststart=payload.faststart,
            mux_mode=payload.mux_mode,
            mute_all_audio=payload.mute_all_audio,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return mux_record


@router.get("/jobs/{job_id}/mux/status")
def get_mux_status(job_id: str):
    """Returns current mux operation status: not_started | processing | completed | failed."""
    _check_id(job_id)
    try:
        return service_get_mux_status(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/mux/output/info")
def get_mux_output_info(job_id: str):
    """Returns telemetric metadata for the completed muxed video output."""
    _check_id(job_id)
    try:
        return service_get_output_video_info(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs/{job_id}/mux/output/stream")
def stream_mux_output(job_id: str, request: Request):
    """Streams the completed muxed video file supporting HTTP 206 Partial Content (range requests)."""
    _check_id(job_id)
    try:
        output_path = service_get_mux_output_path(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    mime_type, _ = mimetypes.guess_type(output_path)
    content_type = mime_type or "video/mp4"

    return _send_file_range(
        file_path=output_path,
        request=request,
        media_type=content_type,
    )


@router.get("/jobs/{job_id}/mux/download")
@router.get("/jobs/{job_id}/mux/output/download")
def download_mux_output(job_id: str):
    """Streams the completed muxed file as a download. 404 if not ready."""
    _check_id(job_id)
    try:
        output_path = service_get_mux_output_path(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    mime_type, _ = mimetypes.guess_type(output_path)
    from pathlib import Path
    filename = Path(output_path).name
    return FileResponse(
        path=output_path,
        media_type=mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
