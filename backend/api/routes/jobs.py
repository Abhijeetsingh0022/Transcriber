"""
Job CRUD endpoints: upload, URL queue, list, get, retry, cancel, delete.
"""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api.schemas import UrlJobRequest, BulkDeleteRequest
from core.http_cache import is_client_fresh
from db.crud import get_job, get_transcript, count_jobs, is_safe_id, get_jobs_state_hash
from db.database import DATA_DIR
from engine.hardware import get_system_telemetry
from engine.worker import QueueWorker
from services.job_service import (
    service_create_upload_job,
    service_download_and_queue_url,
    service_list_jobs,
    service_cancel_job,
    service_retry_job,
    service_delete_job,
    service_bulk_delete,
)

router = APIRouter()


@router.get("/system/status")
def get_status():
    """Returns detected hardware telemetry and worker status."""
    telemetry = get_system_telemetry()
    worker = QueueWorker.get_instance()
    telemetry["worker_status"] = "processing" if worker.is_busy else "idle"
    telemetry["active_job_id"] = worker.active_job_id
    telemetry["queued_jobs_count"] = count_jobs(status="queued")
    return telemetry


@router.post("/system/release_memory")
def release_system_memory():
    """Unloads cached Whisper model from RAM/VRAM and forces system garbage collection."""
    from engine.transcriber import TranscriberEngine
    unloaded = TranscriberEngine.release_model()
    telemetry = get_system_telemetry()
    return {
        "success": True,
        "model_unloaded": unloaded,
        "telemetry": telemetry,
    }


ALLOWED_MEDIA_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".ts", ".opus", ".wma", ".m4v"
}
MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB per file


@router.post("/jobs/upload")
async def upload_media_files(
    files: List[UploadFile] = File(...),
    mode: str = Form("whale"),
    language: str = Form("auto"),
    task: str = Form("transcribe"),
    diarize: bool = Form(False),
    num_speakers: Optional[int] = Form(None),
    restore_audio: bool = Form(False),
    initial_prompt: Optional[str] = Form(None),
):
    """Handles multipart upload of one or multiple media files into the queue."""
    import re

    upload_dir = (DATA_DIR / "uploads").resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    if num_speakers is not None and not (1 <= num_speakers <= 32):
        raise HTTPException(
            status_code=400,
            detail="num_speakers must be an integer between 1 and 32."
        )

    created_jobs = []
    for file in files:
        raw_name = Path(file.filename or "media_upload.wav").name or "media_upload.wav"
        safe_filename = re.sub(r"[^\w\s.-]", "_", raw_name)
        ext = Path(safe_filename).suffix.lower()

        if not ext or ext not in ALLOWED_MEDIA_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}'. Allowed media extensions: {', '.join(sorted(ALLOWED_MEDIA_EXTENSIONS))}"
            )

        unique_disk_name = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
        dest_path = (upload_dir / unique_disk_name).resolve()

        # Path traversal guard: must be strictly inside upload_dir
        if not str(dest_path).startswith(str(upload_dir)):
            raise HTTPException(status_code=400, detail="Invalid destination file path.")

        file_size = 0
        with open(dest_path, "wb") as buf:
            while chunk := await file.read(1024 * 1024):
                file_size += len(chunk)
                if file_size > MAX_UPLOAD_BYTES:
                    buf.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File '{safe_filename}' exceeds the 2 GB maximum upload limit."
                    )
                buf.write(chunk)

        if file_size == 0:
            dest_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"File '{safe_filename}' is empty (0 bytes).")

        job = service_create_upload_job(
            filename=safe_filename,
            filepath=str(dest_path),
            file_size=file_size,
            mode=mode,
            language=language,
            task=task,
            diarize=diarize,
            num_speakers=num_speakers,
            restore_audio=restore_audio,
            initial_prompt=initial_prompt,
        )
        created_jobs.append(job)

    return {"queued_count": len(created_jobs), "jobs": created_jobs}


@router.post("/jobs/url")
async def queue_url_job(payload: UrlJobRequest):
    """Downloads audio from YouTube/web URL via yt-dlp and queues job."""
    if payload.num_speakers is not None and not (1 <= payload.num_speakers <= 32):
        raise HTTPException(status_code=400, detail="num_speakers must be between 1 and 32.")
    try:
        job = await service_download_and_queue_url(
            url=payload.url,
            mode=payload.mode,
            language=payload.language,
            task=payload.task,
            diarize=payload.diarize,
            num_speakers=payload.num_speakers,
            restore_audio=payload.restore_audio,
            initial_prompt=payload.initial_prompt,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch media from URL: {str(e)}")
    return job


@router.get("/jobs")
def get_jobs(request: Request, status: Optional[str] = None, page: int = 1, limit: int = 50):
    """Retrieves paginated list of queued and processed jobs with sub-millisecond HTTP 304 caching."""
    state_hash = get_jobs_state_hash(status)
    etag = f'"{state_hash}:{page}:{limit}"'
    cache_control = "public, max-age=1, stale-while-revalidate=5"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    data = service_list_jobs(status, page, limit)
    return JSONResponse(content=data, headers={"ETag": etag, "Cache-Control": cache_control})


@router.get("/jobs/{job_id}")
def get_single_job(job_id: str, request: Request):
    """Retrieves details of a single job with conditional HTTP 304 caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    etag = f'"{job_id}:{job.get("status")}:{job.get("progress")}:{job.get("completed_at") or job.get("created_at")}"'
    cache_control = "public, max-age=1, stale-while-revalidate=5"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    return JSONResponse(content=job, headers={"ETag": etag, "Cache-Control": cache_control})


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str):
    """Re-queues a failed or cancelled job."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    service_retry_job(job_id)
    return {"status": "queued", "id": job_id}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    """Cancels a queued or active job."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    service_cancel_job(job_id)
    return {"status": "cancelled", "id": job_id}


@router.delete("/jobs/{job_id}")
def delete_single_job(job_id: str):
    """Deletes job and cleans up media and transcript records."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    service_delete_job(job_id)
    return {"success": True, "id": job_id}


@router.post("/jobs/delete/bulk")
def delete_bulk_jobs(payload: BulkDeleteRequest):
    """Deletes multiple jobs and associated assets in batch."""
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    if any(not is_safe_id(jid) for jid in payload.job_ids):
        raise HTTPException(status_code=400, detail="One or more invalid job IDs")
    deleted = service_bulk_delete(payload.job_ids)
    return {"deleted": deleted, "deleted_count": deleted}


@router.post("/jobs/{job_id}/polish_transcript")
def polish_job_transcript(job_id: str):
    """Polishes ASR transcript for Hindi / multilingual jobs to fix phonetic errors and normalize script."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    from engine.hindi_processor import polish_and_save_job_transcript
    from db.database import DB_PATH
    try:
        res = polish_and_save_job_transcript(str(DB_PATH), job_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to polish transcript: {str(e)}")

