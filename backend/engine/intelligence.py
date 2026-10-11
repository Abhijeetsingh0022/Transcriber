"""
Executive AI Intelligence Engine for Video & Dialogue Transcripts.
Generates:
1. Executive TL;DR and Narrative Summary
2. Key Takeaways & Decision Matrix
3. Action Items with Speaker Assignees and Seekable Timestamps
4. Smart Chronological Chapters & Show Notes
5. Key Q&A Discovery
6. Multi-tier Cloud AI fallback (Gemini -> OpenRouter -> TokenHarbor) with 100% offline heuristic fallback.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from db.crud import is_safe_id
from db.database import DATA_DIR
from engine.ai_client import call_ai_json
from core.constants import format_speaker_display_name


def format_tc(seconds: Optional[float]) -> str:
    """Formats seconds into MM:SS (or HH:MM:SS if >= 1 hour)."""
    total_sec = max(0, int(round(float(seconds or 0.0))))
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hrs = total_min // 60
    if hrs > 0:
        return f"{hrs:02d}:{min_:02d}:{sec:02d}"
    return f"{min_:02d}:{sec:02d}"


def _get_dialogue_context(transcript: Dict[str, Any], max_segments: int = 120) -> List[Dict[str, Any]]:
    """Extracts compact dialogue turns suitable for LLM context windows."""
    segments = transcript.get("segments", [])
    if not segments:
        return []

    # If transcript is very large, sample key sections while retaining flow
    step = 1
    if len(segments) > max_segments:
        step = max(1, len(segments) // max_segments)

    sampled = segments[::step][:max_segments]
    turns = []
    for s in sampled:
        speaker = format_speaker_display_name(s.get("speaker_label") or "SPEAKER_00")
        text = s.get("text", "").strip()
        t_start = round(float(s.get("start_time") or 0.0), 1)
        if text:
            turns.append({
                "time": format_tc(t_start),
                "seconds": t_start,
                "speaker": speaker,
                "text": text,
            })
    return turns


def _heuristic_executive_intelligence(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Offline zero-dependency heuristic fallback.
    Extracts summary, chapters, and tentative action items based on linguistic patterns.
    """
    segments = transcript.get("segments", [])
    filename = (job.get("filename") if job else "") or "Audio / Video Dialogue"
    duration = float(job.get("duration_seconds") or (segments[-1].get("end_time", 0.0) if segments else 0.0))
    full_text = transcript.get("full_text", "")

    # Group speakers
    speaker_set = sorted(list(set(
        format_speaker_display_name(s.get("speaker_label") or "SPEAKER_00")
        for s in segments if s.get("text")
    )))

    # Compute chapters at 3-5 minute intervals
    chapters = []
    if segments:
        chunk_interval = max(60.0, duration / max(2, min(6, len(segments) // 8 or 2)))
        curr_time = 0.0
        chap_num = 1
        for seg in segments:
            st = float(seg.get("start_time") or 0.0)
            if st >= curr_time:
                txt = seg.get("text", "").strip()
                title_words = [w for w in txt.split() if len(w) > 3][:6]
                title = " ".join(title_words).capitalize() if title_words else f"Discussion Part {chap_num}"
                chapters.append({
                    "title": title[:50],
                    "start_time": st,
                    "start_timestamp": format_tc(st),
                    "description": txt[:140],
                })
                curr_time += chunk_interval
                chap_num += 1

    # Extract rule-based action items (sentences with 'will', 'need to', 'must', 'let us', 'karna hai')
    action_items = []
    action_keywords = ("will ", "need to", "must ", "should ", "let's ", "please ", "karna ", "karenge", "bhej")
    for s in segments:
        txt = s.get("text", "").strip()
        lower = txt.lower()
        if any(kw in lower for kw in action_keywords) and len(txt) > 15:
            spk = format_speaker_display_name(s.get("speaker_label") or "SPEAKER_00")
            st = float(s.get("start_time") or 0.0)
            action_items.append({
                "task": txt[:160],
                "assignee": spk,
                "timestamp": format_tc(st),
                "time_seconds": st,
                "priority": "medium",
            })
            if len(action_items) >= 8:
                break

    # Build takeaways from early, middle, and late segments
    takeaways = []
    if segments:
        indices = [0, len(segments) // 3, (2 * len(segments)) // 3, len(segments) - 1]
        for idx in set(indices):
            if idx < len(segments):
                txt = segments[idx].get("text", "").strip()
                if txt and len(txt) > 20:
                    takeaways.append(txt[:140])

    tldr = f"Dialogue session spanning {format_tc(duration)} across {len(speaker_set)} speaker(s): {', '.join(speaker_set[:4])}."
    summary = (
        f"This recording covers a {format_tc(duration)} dialogue session featuring {len(speaker_set)} participant(s). "
        f"The conversation touches on core discussion points outlined in the transcript segments, "
        f"culminating in key dialogue exchanges and agreed-upon collaborative steps."
    )

    return {
        "job_id": job.get("id", "") if job else "",
        "filename": filename,
        "tldr": tldr,
        "executive_summary": summary,
        "key_takeaways": takeaways or [full_text[:160] + "..."],
        "action_items": action_items,
        "chapters": chapters,
        "key_questions": [],
        "sentiment_and_tone": "Constructive Dialogue",
        "generated_by": "Heuristic Local Engine (Offline)",
    }


def generate_executive_intelligence(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Extracts high-level executive intelligence, TL;DR, action items, and show notes.
    Checks disk cache first, calls multi-tier AI gateway if available, or falls back to heuristic engine.
    """
    job_id = (job.get("id") if job else "") or transcript.get("job_id", "")
    
    # 1. Check SQLite first, then disk cache
    if job_id and is_safe_id(job_id) and not force_refresh:
        try:
            from db.crud import get_intelligence, save_intelligence
            db_intel = get_intelligence(job_id)
            if db_intel and db_intel.get("executive_summary"):
                return db_intel
        except Exception:
            pass

        cache_path = DATA_DIR / "media" / job_id / "intelligence.json"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if isinstance(cached, dict) and cached.get("executive_summary"):
                        try:
                            save_intelligence(job_id, cached)
                        except Exception:
                            pass
                        return cached
            except Exception:
                pass

    turns = _get_dialogue_context(transcript)
    if not turns:
        return _heuristic_executive_intelligence(transcript, job)

    filename = (job.get("filename") if job else "") or "Session Audio"

    prompt = (
        "You are an executive chief of staff and high-level communications intelligence analyst.\n"
        f"Analyze this transcript of '{filename}' and generate an authoritative executive intelligence report.\n\n"
        "Input Dialogue Sample:\n"
        f"{json.dumps(turns[:90], ensure_ascii=False, indent=2)}\n\n"
        "Strict Requirements:\n"
        "1. 'tldr': A crisp 1-2 sentence high-impact summary of what occurred.\n"
        "2. 'executive_summary': A structured 2-3 paragraph narrative synthesis detailing the context, key discussions, and final resolutions.\n"
        "3. 'key_takeaways': A list of 4-6 bullet-point insights and core conclusions.\n"
        "4. 'action_items': A list of explicit next steps, each with: 'task', 'assignee' (the character/speaker name), 'timestamp' (e.g. '01:24'), 'time_seconds' (float), 'priority' ('high'|'medium'|'low').\n"
        "5. 'chapters': A list of 4-8 chronological chapters for video/show notes with: 'title', 'start_time' (float), 'start_timestamp' (MM:SS), 'description'.\n"
        "6. 'key_questions': 2-4 important questions asked during the session with: 'question', 'answer', 'asked_by', 'timestamp'.\n"
        "7. 'sentiment_and_tone': 2-4 words characterizing the tone (e.g. 'Collaborative Technical Planning', 'Urgent Incident Review').\n\n"
        "Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "tldr": "...",\n'
        '  "executive_summary": "...",\n'
        '  "key_takeaways": ["...", "..."],\n'
        '  "action_items": [{"task": "...", "assignee": "...", "timestamp": "...", "time_seconds": 0.0, "priority": "high"}],\n'
        '  "chapters": [{"title": "...", "start_time": 0.0, "start_timestamp": "00:00", "description": "..."}],\n'
        '  "key_questions": [{"question": "...", "answer": "...", "asked_by": "...", "timestamp": "..."}],\n'
        '  "sentiment_and_tone": "..."\n'
        "}"
    )

    try:
        res, provider = call_ai_json(prompt, task_tag="executive_intelligence", timeout=35.0)
        if res and isinstance(res, dict) and res.get("executive_summary"):
            res["job_id"] = job_id
            res["filename"] = filename
            res["generated_by"] = f"AI Intelligence Gateway ({provider})"

            # Persist to SQLite and disk cache
            if job_id and is_safe_id(job_id):
                try:
                    from db.crud import save_intelligence
                    save_intelligence(job_id, res)
                except Exception:
                    pass
                cache_file = DATA_DIR / "media" / job_id / "intelligence.json"
                cache_file.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)

            return res
    except Exception:
        pass

    # 3. Fallback to heuristic offline intelligence
    fallback = _heuristic_executive_intelligence(transcript, job)
    if job_id and is_safe_id(job_id):
        try:
            from db.crud import save_intelligence
            save_intelligence(job_id, fallback)
        except Exception:
            pass
        cache_file = DATA_DIR / "media" / job_id / "intelligence.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(fallback, f, ensure_ascii=False, indent=2)
    return fallback


def export_intelligence_markdown(
    intelligence: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
) -> str:
    """Renders formatted Markdown briefing document from intelligence dictionary."""
    filename = intelligence.get("filename") or (job.get("filename") if job else "Audio Transcript")
    tldr = intelligence.get("tldr", "")
    summary = intelligence.get("executive_summary", "")
    takeaways = intelligence.get("key_takeaways", [])
    actions = intelligence.get("action_items", [])
    chapters = intelligence.get("chapters", [])
    questions = intelligence.get("key_questions", [])
    tone = intelligence.get("sentiment_and_tone", "Professional")
    provider = intelligence.get("generated_by", "Transcriber AI Intelligence")

    lines = [
        f"# Executive Briefing & Intelligence Report",
        f"**Source Media:** {filename}  ",
        f"**Discourse Tone:** {tone}  ",
        f"**Engine:** {provider}  ",
        "",
        "---",
        "",
        "## TL;DR",
        f"> {tldr}",
        "",
        "## Executive Summary",
        summary,
        "",
        "## Key Takeaways",
    ]
    for tk in takeaways:
        lines.append(f"- {tk}")

    if actions:
        lines.extend([
            "",
            "## Action Items & Next Steps",
            "| Priority | Task | Assignee | Timestamp |",
            "| :--- | :--- | :--- | :--- |",
        ])
        for act in actions:
            prio = (act.get("priority") or "medium").upper()
            lines.append(
                f"| `{prio}` | {act.get('task', '')} | **{act.get('assignee', 'Unassigned')}** | [{act.get('timestamp', '00:00')}] |"
            )

    if chapters:
        lines.extend([
            "",
            "## Timestamped Chapters & Show Notes",
        ])
        for ch in chapters:
            lines.append(f"- **`[{ch.get('start_timestamp', '00:00')}]` {ch.get('title', 'Chapter')}**: {ch.get('description', '')}")

    if questions:
        lines.extend([
            "",
            "## Key Questions & Answers",
        ])
        for q in questions:
            lines.append(f"### Q: {q.get('question', '')} (`{q.get('timestamp', '')}` by {q.get('asked_by', 'Speaker')})")
            lines.append(f"**A:** {q.get('answer', '')}")
            lines.append("")

    lines.extend([
        "",
        "---",
        "*Generated automatically by Transcriber Executive AI Intelligence Suite.*",
    ])
    return "\n".join(lines)
