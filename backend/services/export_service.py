"""
Export service: dispatch to format generators, handle bulk ZIP packaging.
Routes call this; this calls engine exporters. No FastAPI dependencies here.
"""

import io
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List

from db.database import DATA_DIR
from db.crud import get_transcript, get_job
from engine.exporters.subtitles import generate_srt, generate_vtt
from engine.exporters.documents import generate_txt, generate_csv, generate_json, generate_docx, generate_pdf
from engine.exporters.script import (
    group_segments_into_dialogue_turns,
    generate_script_text,
    generate_script_markdown,
    generate_script_html,
)
from engine.topics import generate_topic_flow_html, generate_topic_flow_markdown
from engine.audio import convert_to_mp3


# ---------------------------------------------------------------------------
# Single-job export
# ---------------------------------------------------------------------------

def service_export(
    job_id: str,
    fmt: str,
    style: Optional[str] = None,
    timestamps: Optional[str] = None,
    speaker_case: Optional[str] = "upper",
    include_stats: bool = True,
) -> Dict[str, Any]:
    """
    Dispatches a single-job export to the correct generator.
    Returns a dict with keys: content (bytes|str), media_type, filename.
    Raises ValueError for unknown formats.
    """
    transcript = get_transcript(job_id)
    if not transcript:
        raise FileNotFoundError("Transcript not ready or not found")

    job = get_job(job_id)
    base_name = Path(job["filename"]).stem if job else "transcript"
    clean = base_name.replace('"', '_').replace('\r', '').replace('\n', '').strip() or "transcript"
    segments = transcript.get("segments", [])
    speakers = transcript.get("speakers", [])

    fmt = fmt.lower()

    if fmt == "srt":
        return _resp(generate_srt(segments, speakers), "application/x-subrip", f"{clean}_transcript.srt")
    if fmt == "vtt":
        return _resp(generate_vtt(segments, speakers), "text/vtt", f"{clean}_transcript.vtt")
    if fmt == "txt":
        return _resp(generate_txt(transcript), "text/plain; charset=utf-8", f"{clean}_transcript.txt")
    if fmt == "csv":
        return _resp(generate_csv(segments, speakers), "text/csv", f"{clean}_transcript.csv")
    if fmt == "json":
        return _resp(generate_json(transcript), "application/json", f"{clean}_transcript.json")
    if fmt in ("script", "script_txt", "script_broadcast"):
        content = generate_script_text(transcript, job=job, style=style or "broadcast",
                                       timestamp_format=timestamps or "range",
                                       speaker_case=speaker_case or "upper",
                                       include_stats=include_stats)
        return _resp(content, "text/plain; charset=utf-8", f"{clean}_broadcast_script.txt")
    if fmt == "script_screenplay":
        content = generate_script_text(transcript, job=job, style="screenplay",
                                       speaker_case=speaker_case or "upper", include_stats=include_stats)
        return _resp(content, "text/plain; charset=utf-8", f"{clean}_screenplay.txt")
    if fmt == "script_legal":
        content = generate_script_text(transcript, job=job, style="legal",
                                       speaker_case=speaker_case or "upper", include_stats=include_stats)
        return _resp(content, "text/plain; charset=utf-8", f"{clean}_legal_deposition.txt")
    if fmt in ("script_podcast", "script_shownotes"):
        content = generate_script_text(transcript, job=job, style="podcast",
                                       speaker_case=speaker_case or "title", include_stats=include_stats)
        return _resp(content, "text/plain; charset=utf-8", f"{clean}_shownotes.txt")
    if fmt == "script_dialogue":
        content = generate_script_text(transcript, job=job, style="dialogue",
                                       speaker_case=speaker_case or "title", include_stats=False)
        return _resp(content, "text/plain; charset=utf-8", f"{clean}_dialogue.txt")
    if fmt == "script_md":
        return _resp(generate_script_markdown(transcript, job=job), "text/markdown; charset=utf-8", f"{clean}_script.md")
    if fmt == "script_html":
        return _resp(generate_script_html(transcript, job=job), "text/html; charset=utf-8", f"{clean}_script.html")
    if fmt in ("topic_flow", "script_topicflow", "topics_html"):
        return _resp(generate_topic_flow_html(transcript, job=job), "text/html; charset=utf-8", f"{clean}_topic_flow.html")
    if fmt in ("topic_flow_md", "topics_md"):
        return _resp(generate_topic_flow_markdown(transcript, job=job), "text/markdown; charset=utf-8", f"{clean}_topic_flow.md")
    if fmt == "docx":
        out = DATA_DIR / "outputs" / f"{job_id}.docx"
        out.parent.mkdir(parents=True, exist_ok=True)
        generate_docx(transcript, str(out), job=job)
        return {"file_path": str(out), "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "filename": f"{clean}_transcript.docx"}
    if fmt in ("pdf", "topic_flow_pdf", "section_flow_pdf"):
        out = DATA_DIR / "outputs" / f"{job_id}.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        orientation = "portrait" if (style and style.lower() == "portrait") else "landscape"
        generate_pdf(transcript, str(out), job=job, orientation=orientation)
        return {"file_path": str(out), "media_type": "application/pdf", "filename": f"{clean}_section_flow.pdf"}
    if fmt == "mp3":
        wav_path = DATA_DIR / "media" / job_id / "audio_16k.wav"
        if not wav_path.exists() and job and Path(job["filepath"]).exists():
            wav_path = Path(job["filepath"])
        if not wav_path.exists():
            raise FileNotFoundError("Source audio file not found")
        mp3_path = DATA_DIR / "media" / job_id / "audio.mp3"
        mp3_path.parent.mkdir(parents=True, exist_ok=True)
        if not mp3_path.exists():
            convert_to_mp3(str(wav_path), str(mp3_path))
        return {"file_path": str(mp3_path), "media_type": "audio/mpeg", "filename": f"{clean}.mp3"}

    raise ValueError(f"Unsupported export format: {fmt}")


# ---------------------------------------------------------------------------
# Bulk ZIP export
# ---------------------------------------------------------------------------

def service_bulk_export(job_ids: List[str], formats: List[str]) -> bytes:
    """Builds an in-memory ZIP containing requested format exports for each job."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for job_id in job_ids:
            transcript = get_transcript(job_id)
            job = get_job(job_id)
            if not transcript or not job:
                continue
            clean = (Path(job["filename"]).stem
                     .replace('"', '_').replace('\r', '').replace('\n', '').strip() or "transcript")
            segments = transcript.get("segments", [])
            speakers = transcript.get("speakers", [])

            for fmt in formats:
                fmt_l = fmt.lower()
                try:
                    if fmt_l == "srt":
                        zf.writestr(f"{clean}_transcript.srt", generate_srt(segments, speakers))
                    elif fmt_l == "vtt":
                        zf.writestr(f"{clean}_transcript.vtt", generate_vtt(segments, speakers))
                    elif fmt_l == "txt":
                        zf.writestr(f"{clean}_transcript.txt", generate_txt(transcript))
                    elif fmt_l in ("script", "script_txt"):
                        zf.writestr(f"{clean}_script.txt", generate_script_text(transcript, job=job))
                    elif fmt_l == "script_md":
                        zf.writestr(f"{clean}_script.md", generate_script_markdown(transcript, job=job))
                    elif fmt_l == "script_html":
                        zf.writestr(f"{clean}_script.html", generate_script_html(transcript, job=job))
                    elif fmt_l == "csv":
                        zf.writestr(f"{clean}_transcript.csv", generate_csv(segments, speakers))
                    elif fmt_l == "json":
                        zf.writestr(f"{clean}_transcript.json", generate_json(transcript))
                    elif fmt_l == "docx":
                        tmp = DATA_DIR / "outputs" / f"bulk_{job_id}.docx"
                        tmp.parent.mkdir(parents=True, exist_ok=True)
                        generate_docx(transcript, str(tmp), job=job)
                        if tmp.exists():
                            zf.writestr(f"{clean}_transcript.docx", tmp.read_bytes())
                            tmp.unlink(missing_ok=True)
                    elif fmt_l == "pdf":
                        tmp = DATA_DIR / "outputs" / f"bulk_{job_id}.pdf"
                        tmp.parent.mkdir(parents=True, exist_ok=True)
                        generate_pdf(transcript, str(tmp), job=job)
                        if tmp.exists():
                            zf.writestr(f"{clean}_transcript.pdf", tmp.read_bytes())
                            tmp.unlink(missing_ok=True)
                except Exception as e:
                    # Don't abort the whole ZIP for one bad format
                    print(f"Bulk export: skipping {fmt} for {job_id}: {e}")

    buf.seek(0)
    return buf.getvalue()


def _resp(content, media_type: str, filename: str) -> Dict[str, Any]:
    return {"content": content, "media_type": media_type, "filename": filename}
