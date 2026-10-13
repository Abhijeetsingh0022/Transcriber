"""
Speaker and segment management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api.schemas import (
    SegmentSpeakerUpdateRequest,
    SegmentAddresseeUpdateRequest,
    IdentifySpeakersRequest,
    SpeakerUpdateItem,
    SegmentTextUpdateRequest,
)
from core.http_cache import is_client_fresh
from db.crud import (
    get_job,
    get_transcript,
    update_speakers,
    update_transcript_segment,
    update_segments_speaker,
    update_segments_addressee,
    is_safe_id,
)
from db.database import DB_PATH

router = APIRouter()


@router.get("/jobs/{job_id}/transcript")
def get_job_transcript(job_id: str, request: Request):
    """Returns complete structured transcript with segments, words, and speakers with HTTP 304 caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not ready or not found")

    etag = f'"{job_id}:{transcript.get("updated_at") or transcript.get("created_at")}:{transcript.get("word_count", 0)}:{transcript.get("segment_count", 0)}"'
    cache_control = "public, max-age=3600, stale-while-revalidate=300"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    return JSONResponse(content=transcript, headers={"ETag": etag, "Cache-Control": cache_control})


@router.patch("/jobs/{job_id}/speakers")
def patch_speakers(job_id: str, updates: List[SpeakerUpdateItem]):
    """Updates display names or colors of speaker tags."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    update_speakers(job_id, [u.model_dump() for u in updates])
    return {"success": True}


@router.patch("/jobs/{job_id}/segments/speaker")
def reassign_segments_speaker(job_id: str, payload: SegmentSpeakerUpdateRequest):
    """Reassigns the speaker label for one or multiple segments."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    if any(not is_safe_id(sid) for sid in payload.segment_ids):
        raise HTTPException(status_code=400, detail="One or more invalid segment IDs")
    update_segments_speaker(payload.segment_ids, payload.speaker_label)
    return {"success": True, "count": len(payload.segment_ids), "speaker_label": payload.speaker_label}


@router.patch("/jobs/{job_id}/segments/addressee")
def reassign_segments_addressee(job_id: str, payload: SegmentAddresseeUpdateRequest):
    """Reassigns the addressed_to character name for one or multiple segments."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    if any(not is_safe_id(sid) for sid in payload.segment_ids):
        raise HTTPException(status_code=400, detail="One or more invalid segment IDs")
    update_segments_addressee(payload.segment_ids, payload.addressed_to)
    return {"success": True, "count": len(payload.segment_ids), "addressed_to": payload.addressed_to}


@router.post("/jobs/{job_id}/identify_speakers")
def trigger_smart_speaker_identification(
    job_id: str,
    payload: Optional[IdentifySpeakersRequest] = None,
):
    """
    Identifies speakers using Tier 1 (local state graph) or Tier 2 (Gemini AI).
    Updates speaker records, segment assignments, and addressee mappings.
    """
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    from engine.speaker_id import smart_identify_and_save_job
    from services.settings_service import get_raw_gemini_key, get_raw_openrouter_key

    tier = payload.tier if payload else "auto"
    api_key = (payload.gemini_api_key if payload and payload.gemini_api_key else None) or get_raw_gemini_key()
    openrouter_key = (payload.openrouter_api_key if payload and payload.openrouter_api_key else None) or get_raw_openrouter_key()

    res = smart_identify_and_save_job(
        str(DB_PATH),
        job_id,
        tier=tier,
        gemini_api_key=api_key,
        openrouter_api_key=openrouter_key,
    )
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res


@router.put("/jobs/{job_id}/segments/{segment_id}")
@router.patch("/jobs/{job_id}/segments/{segment_id}")
def update_segment_text(job_id: str, segment_id: str, payload: SegmentTextUpdateRequest):
    """Updates text content of an individual segment."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    if not is_safe_id(segment_id):
        raise HTTPException(status_code=400, detail="Invalid segment ID")
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    update_transcript_segment(segment_id, payload.text)
    return {"success": True, "segment_id": segment_id}

