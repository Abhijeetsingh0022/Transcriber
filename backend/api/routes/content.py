"""
Script preview, dialogues, topics, and acoustic waveform endpoints.
"""

import hashlib
import json
import os
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from core.http_cache import is_client_fresh
from db.crud import (
    get_job,
    get_transcript,
    is_safe_id,
    get_markers,
    create_marker,
    delete_marker,
    search_transcripts_fts,
)
from db.database import DATA_DIR
from engine.audio import generate_waveform_peaks
from engine.exporters.script import group_segments_into_dialogue_turns, generate_script_text
from engine.topics import extract_video_topics

router = APIRouter()

# High-performance in-memory LRU cache for waveforms (instant RAM access)
_WAVEFORM_MEM_CACHE: OrderedDict = OrderedDict()
_MAX_WAVEFORM_CACHE = 100


def _transcript_etag(job_id: str, transcript: Dict[str, Any], extra: str = "") -> str:
    """Computes a deterministic ETag based on transcript state and request parameters."""
    raw = f"{job_id}:{transcript.get('updated_at', '')}:{transcript.get('duration', 0)}:{extra}"
    return f'"{hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]}"'


@router.get("/jobs/{job_id}/dialogues")
def get_job_dialogues(job_id: str, request: Request, max_pause: float = 3.5):
    """Returns transcript aggregated into dialogue turns with speaker metadata and ETag caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    etag = _transcript_etag(job_id, transcript, f"dialogues:{max_pause}")
    cache_control = "public, max-age=3600, stale-while-revalidate=300"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    turns = group_segments_into_dialogue_turns(transcript, max_pause_seconds=max_pause)
    payload = {"job_id": job_id, "turn_count": len(turns), "dialogues": turns}
    return JSONResponse(content=payload, headers={"ETag": etag, "Cache-Control": cache_control})


@router.get("/jobs/{job_id}/script/preview")
def preview_job_script(
    job_id: str,
    request: Request,
    style: str = "broadcast",
    timestamps: str = "range",
    speaker_case: str = "upper",
    include_stats: bool = True,
    max_pause: float = 2.5,
):
    """Renders formatted script text per requested template with HTTP caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    etag = _transcript_etag(job_id, transcript, f"script:{style}:{timestamps}:{speaker_case}:{include_stats}:{max_pause}")
    cache_control = "public, max-age=3600, stale-while-revalidate=300"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    job = get_job(job_id)
    content = generate_script_text(
        transcript,
        job=job,
        style=style,
        timestamp_format=timestamps,
        speaker_case=speaker_case,
        include_stats=include_stats,
    )
    payload = {
        "job_id": job_id,
        "style": style,
        "timestamps": timestamps,
        "speaker_case": speaker_case,
        "content": content,
    }
    return JSONResponse(content=payload, headers={"ETag": etag, "Cache-Control": cache_control})


@router.get("/jobs/{job_id}/topics")
def get_job_topics(job_id: str, request: Request):
    """Extracts hierarchical Sections and Topics with timestamps from the transcript."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    job = get_job(job_id)
    topics = extract_video_topics(transcript, job=job)
    payload = {"job_id": job_id, "total_topics": len(topics), "topics": topics}
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
    )


@router.get("/jobs/{job_id}/waveform")
def get_job_waveform(job_id: str, request: Request, points: int = 128):
    """
    Returns downsampled acoustic waveform peaks for instantaneous UI audio visualizers.
    Reads pre-cached JSON or computes from 16kHz audio stream on demand.
    Supports in-memory LRU caching and RFC 7231 / 7233 conditional ETag validation (304 Not Modified).
    """
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    safe_points = max(16, min(int(points), 2048))
    cache_file = DATA_DIR / "media" / job_id / "waveform.json"
    cache_control = "public, max-age=86400, stale-while-revalidate=3600"

    # Fast path: compute ETag from disk cache if present
    if cache_file.exists():
        try:
            stat = os.stat(cache_file)
            etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}-{safe_points}"'

            if is_client_fresh(request, etag, stat.st_mtime):
                return Response(
                    status_code=304,
                    headers={"ETag": etag, "Cache-Control": cache_control},
                )

            mem_key = f"{job_id}:{safe_points}:{stat.st_mtime_ns}"
            if mem_key in _WAVEFORM_MEM_CACHE:
                _WAVEFORM_MEM_CACHE.move_to_end(mem_key)
                return JSONResponse(
                    content=_WAVEFORM_MEM_CACHE[mem_key],
                    headers={"ETag": etag, "Cache-Control": cache_control},
                )

            with open(cache_file, "r") as f:
                data = json.load(f)

            if len(_WAVEFORM_MEM_CACHE) >= _MAX_WAVEFORM_CACHE:
                _WAVEFORM_MEM_CACHE.popitem(last=False)
            _WAVEFORM_MEM_CACHE[mem_key] = data

            return JSONResponse(
                content=data,
                headers={"ETag": etag, "Cache-Control": cache_control},
            )
        except Exception:
            pass

    wav_path = DATA_DIR / "media" / job_id / "audio_16k.wav"
    if not wav_path.exists():
        job = get_job(job_id)
        if job and job.get("filepath") and Path(job["filepath"]).exists():
            wav_path = Path(job["filepath"])

    if wav_path.exists():
        peaks = generate_waveform_peaks(str(wav_path), num_peaks=safe_points)
        payload = {"job_id": job_id, "peaks": peaks}
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(payload, f)
            stat = os.stat(cache_file)
            etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}-{safe_points}"'
        except Exception:
            etag = f'"{hashlib.sha256(job_id.encode()).hexdigest()[:16]}"'

        mem_key = f"{job_id}:{safe_points}"
        if len(_WAVEFORM_MEM_CACHE) >= _MAX_WAVEFORM_CACHE:
            _WAVEFORM_MEM_CACHE.popitem(last=False)
        _WAVEFORM_MEM_CACHE[mem_key] = payload

        return JSONResponse(
            content=payload,
            headers={"ETag": etag, "Cache-Control": cache_control},
        )

    fallback = {"job_id": job_id, "peaks": [0.2] * safe_points}
    return JSONResponse(
        content=fallback,
        headers={"Cache-Control": "public, max-age=60"},
    )


@router.get("/jobs/{job_id}/intelligence")
def get_job_executive_intelligence(job_id: str, request: Request):
    """
    Returns Executive AI Intelligence report: TL;DR, key takeaways, action items,
    and timestamped show notes. Caches result on disk and supports HTTP 304 revalidation.
    """
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    etag = _transcript_etag(job_id, transcript, "intelligence")
    cache_control = "public, max-age=3600, stale-while-revalidate=300"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    job = get_job(job_id)
    from engine.intelligence import generate_executive_intelligence
    result = generate_executive_intelligence(transcript, job=job, force_refresh=False)
    return JSONResponse(content=result, headers={"ETag": etag, "Cache-Control": cache_control})


@router.post("/jobs/{job_id}/intelligence/generate")
def force_generate_job_intelligence(job_id: str):
    """Forces regeneration of the Executive AI Intelligence report."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    job = get_job(job_id)
    from engine.intelligence import generate_executive_intelligence
    return generate_executive_intelligence(transcript, job=job, force_refresh=True)


@router.get("/jobs/{job_id}/intelligence/export")
def export_job_intelligence_briefing(job_id: str, format: str = "markdown"):
    """Exports Executive Briefing document as formatted Markdown or text."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    transcript = get_transcript(job_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    job = get_job(job_id)
    from engine.intelligence import generate_executive_intelligence, export_intelligence_markdown
    intel = generate_executive_intelligence(transcript, job=job, force_refresh=False)
    md_text = export_intelligence_markdown(intel, job=job)
    return {"job_id": job_id, "format": format, "content": md_text}


# ---------------------------------------------------------------------------
# Markers & Bookmarks Endpoints
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/markers")
def get_job_markers(job_id: str, request: Request):
    """Returns all saved audio markers/pins for a job with conditional HTTP 304 caching."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    markers = get_markers(job_id)
    last_mod = markers[-1].get("created_at", "") if markers else "none"
    etag = f'"{job_id}:{len(markers)}:{last_mod}"'
    cache_control = "public, max-age=60, stale-while-revalidate=300"

    if is_client_fresh(request, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": cache_control})

    return JSONResponse(content=markers, headers={"ETag": etag, "Cache-Control": cache_control})


@router.post("/jobs/{job_id}/markers")
async def add_job_marker(job_id: str, request: Request):
    """Creates or updates a persistent timestamp bookmark/marker for a job."""
    if not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    time_pos = float(body.get("time", 0.0))
    label = str(body.get("label", "Bookmark")).strip() or "Bookmark"
    tag = str(body.get("tag", "note")).strip() or "note"
    marker_id = body.get("id")
    if marker_id and not is_safe_id(marker_id):
        marker_id = None

    return create_marker(job_id, time_pos, label, tag, marker_id)


@router.delete("/jobs/{job_id}/markers/{marker_id}")
def remove_job_marker(job_id: str, marker_id: str):
    """Deletes an audio marker/pin by ID."""
    if not is_safe_id(job_id) or not is_safe_id(marker_id):
        raise HTTPException(status_code=400, detail="Invalid ID")
    deleted = delete_marker(job_id, marker_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Marker not found")
    return {"success": True, "marker_id": marker_id}


# ---------------------------------------------------------------------------
# FTS5 Full-Text Search Endpoint
# ---------------------------------------------------------------------------

@router.get("/search")
def search_transcripts(q: str, job_id: Optional[str] = None, limit: int = 50):
    """
    Sub-millisecond full-text search across transcripts using SQLite FTS5.
    Returns matched utterances with BM25 relevance ranking and HTML highlighted snippets.
    """
    if not q or not q.strip():
        return {"query": "", "count": 0, "results": []}
    if job_id and not is_safe_id(job_id):
        raise HTTPException(status_code=400, detail="Invalid job ID")

    safe_limit = max(1, min(limit, 200))
    results = search_transcripts_fts(q, job_id=job_id, limit=safe_limit)
    return {
        "query": q,
        "count": len(results),
        "job_id": job_id,
        "results": results,
    }


