"""
Export endpoints: single-job and bulk ZIP export for all supported formats.
"""

import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from api.schemas import BulkExportRequest
from db.crud import get_job, get_transcript, is_safe_id
from db.database import DATA_DIR
from services.export_service import service_export, service_bulk_export

router = APIRouter()


@router.get("/jobs/{job_id}/export/{export_format}")
def export_job_transcript(
    job_id: str,
    export_format: str,
    style: Optional[str] = None,
    timestamps: Optional[str] = None,
    speaker_case: Optional[str] = "upper",
    include_stats: bool = True,
):
    """
    Exports transcript to requested format.
    Subtitles: srt, vtt
    Documents: txt, csv, json, docx, pdf, mp3
    Scripts: script, script_broadcast, script_screenplay, script_legal,
             script_podcast, script_shownotes, script_dialogue, script_md, script_html
    Topics: topic_flow, script_topicflow, topics_html, topic_flow_md, topics_md
    """
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    try:
        result = service_export(
            job_id=job_id,
            fmt=export_format,
            style=style,
            timestamps=timestamps,
            speaker_case=speaker_case,
            include_stats=include_stats,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if "file_path" in result:
        return FileResponse(
            path=result["file_path"],
            media_type=result["media_type"],
            headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
        )
    return Response(
        content=result["content"],
        media_type=result["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


@router.post("/jobs/export/bulk")
def export_bulk_transcripts(payload: BulkExportRequest):
    """Generates an in-memory ZIP package containing exports for requested jobs."""
    if not payload.job_ids:
        raise HTTPException(status_code=400, detail="No job IDs provided")
    if any(not is_safe_id(jid) for jid in payload.job_ids):
        raise HTTPException(status_code=400, detail="One or more invalid job IDs")
    zip_bytes = service_bulk_export(payload.job_ids, payload.formats)
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="transcripts_bulk.zip"'},
    )


from core.http_cache import send_cached_range_file


@router.get("/jobs/{job_id}/media")
def stream_job_audio(job_id: str, request: Request):
    """Streams audio file supporting browser seek (HTTP 206 partial content) and RFC 7231 / 7233 304 caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    wav_path = DATA_DIR / "media" / job_id / "audio_16k.wav"
    if not wav_path.exists():
        job = get_job(job_id)
        if job and Path(job["filepath"]).exists():
            wav_path = Path(job["filepath"])
        else:
            raise HTTPException(status_code=404, detail="Media file not found")
    mime_type, _ = mimetypes.guess_type(str(wav_path))
    return send_cached_range_file(
        file_path=str(wav_path),
        request=request,
        media_type=mime_type or "audio/wav",
    )

