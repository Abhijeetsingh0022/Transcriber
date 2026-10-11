"""
Job service: business logic for creating, listing, deleting, and cleaning up jobs.
Routes call this; this calls db/crud. No FastAPI dependencies here.
"""

import os
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any

import yt_dlp

from db.database import DATA_DIR
from db.crud import (
    create_job,
    get_job,
    list_jobs,
    count_jobs,
    update_job_status,
    reset_job_for_retry,
    delete_job,
    delete_jobs,
)


def service_create_upload_job(
    filename: str,
    filepath: str,
    file_size: int,
    mode: str,
    language: str,
    task: str,
    diarize: bool,
    num_speakers: Optional[int],
    restore_audio: bool,
    initial_prompt: Optional[str],
) -> Dict[str, Any]:
    """Creates a job record for an already-saved upload. Returns the full job dict."""
    job_id = create_job(
        filename=filename,
        filepath=filepath,
        file_size_bytes=file_size,
        mode=mode,
        language=language,
        task=task,
        diarize=diarize,
        num_speakers=num_speakers,
        restore_audio=restore_audio,
        initial_prompt=initial_prompt,
    )
    return get_job(job_id)


async def service_download_and_queue_url(
    url: str,
    mode: str,
    language: str,
    task: str,
    diarize: bool,
    num_speakers: Optional[int],
    restore_audio: bool,
    initial_prompt: Optional[str],
) -> Dict[str, Any]:
    from urllib.parse import urlparse

    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL: only HTTP and HTTPS schemes are supported.")

    parsed = urlparse(clean_url)
    hostname = (parsed.hostname or "").lower()
    blocked_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"}
    if hostname in blocked_hosts or hostname.endswith(".internal") or hostname.endswith(".local") or hostname.startswith("127."):
        raise ValueError("Access to local or private network addresses is forbidden.")

    upload_dir = DATA_DIR / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    out_prefix = str(upload_dir / f"{uuid.uuid4().hex[:8]}_%(id)s.%(ext)s")

    def _sync_download():
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": out_prefix,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 30,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=True)
            filepath = ydl.prepare_filename(info)
            if not os.path.exists(filepath):
                actual = info.get("_filename")
                if actual and os.path.exists(actual):
                    filepath = actual
                else:
                    base_id = info.get("id")
                    matches = list(upload_dir.glob(f"*{base_id}*"))
                    if matches:
                        filepath = str(matches[0])
            title = info.get("title", Path(filepath).stem)
            file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            ext = Path(filepath).suffix or ".m4a"
            return filepath, f"{title}{ext}", file_size

    filepath, filename, file_size = await asyncio.to_thread(_sync_download)
    job_id = create_job(
        filename=filename,
        filepath=filepath,
        file_size_bytes=file_size,
        mode=mode,
        language=language,
        task=task,
        diarize=diarize,
        num_speakers=num_speakers,
        restore_audio=restore_audio,
        initial_prompt=initial_prompt,
    )
    return get_job(job_id)


def service_list_jobs(status: Optional[str], page: int, limit: int) -> Dict[str, Any]:
    safe_page = max(1, page)
    safe_limit = max(1, min(limit, 200))
    offset = (safe_page - 1) * safe_limit
    jobs = list_jobs(status=status, limit=safe_limit, offset=offset)
    total = count_jobs(status=status)
    return {"total": total, "page": safe_page, "limit": safe_limit, "jobs": jobs}


def service_cancel_job(job_id: str) -> None:
    from engine.worker import QueueWorker
    QueueWorker.cancel_job_id(job_id)
    update_job_status(job_id, "cancelled")


def service_retry_job(job_id: str) -> None:
    reset_job_for_retry(job_id)


def service_delete_job(job_id: str) -> bool:
    """Deletes job record and cleans up all associated files on disk."""
    job = get_job(job_id)
    if not job:
        return False
    _cleanup_job_files(job_id, job)
    return delete_job(job_id)


def service_bulk_delete(job_ids: List[str]) -> int:
    """Deletes multiple jobs, cleans up associated files, and deletes records in a single batch transaction."""
    if not job_ids:
        return 0
    valid_ids = []
    for job_id in job_ids:
        job = get_job(job_id)
        if job:
            _cleanup_job_files(job_id, job)
            valid_ids.append(job_id)
    return delete_jobs(valid_ids)


def _cleanup_job_files(job_id: str, job: Dict[str, Any]) -> None:
    """Removes upload, media cache, and output files for a job."""
    upload_path = Path(job.get("filepath", ""))
    if upload_path.exists() and (DATA_DIR / "uploads") in upload_path.parents:
        upload_path.unlink(missing_ok=True)

    media_dir = DATA_DIR / "media" / job_id
    if media_dir.exists():
        shutil.rmtree(media_dir, ignore_errors=True)

    for ext in ("docx", "pdf"):
        f = DATA_DIR / "outputs" / f"{job_id}.{ext}"
        f.unlink(missing_ok=True)
