"""
Professional Transcribe Script Template Engine.
Groups consecutive utterances into coherent dialogue turns and renders production-grade
screenplay, broadcast, interview, markdown, and printable HTML script templates.
"""

import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime


def format_time_code(
    seconds: float,
    include_hours: bool = False,
    include_ms: bool = False,
    delimiter: str = ":"
) -> str:
    """Formats seconds into readable timecode e.g. 00:01:23, 01:23, or 00:01:23.450."""
    total_ms = int(round(seconds * 1000))
    ms = total_ms % 1000
    total_sec = total_ms // 1000
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hrs = total_min // 60

    if include_hours or hrs > 0:
        base = f"{hrs:02d}{delimiter}{min_:02d}{delimiter}{sec:02d}"
    else:
        base = f"{min_:02d}{delimiter}{sec:02d}"

    if include_ms:
        return f"{base}.{ms:03d}"
    return base


def format_timestamp_token(
    start_sec: float,
    end_sec: float,
    fmt: str = "range"
) -> str:
    """
    Renders timestamp string according to requested format:
      - 'range': '[00:01:23 - 00:01:45]'
      - 'short_range': '[01:23 - 01:45]'
      - 'single': '[00:01:23]'
      - 'short': '[01:23]'
      - 'ms': '[00:01:23.450 - 00:01:45.120]'
      - 'none': ''
    """
    if fmt == "none":
        return ""
    elif fmt == "ms":
        s = format_time_code(start_sec, include_hours=True, include_ms=True)
        e = format_time_code(end_sec, include_hours=True, include_ms=True)
        return f"[{s} - {e}]"
    elif fmt == "short_range":
        s = format_time_code(start_sec, include_hours=False)
        e = format_time_code(end_sec, include_hours=False)
        return f"[{s} - {e}]"
    elif fmt == "single":
        s = format_time_code(start_sec, include_hours=True)
        return f"[{s}]"
    elif fmt == "short":
        s = format_time_code(start_sec, include_hours=False)
        return f"[{s}]"
    else:  # default 'range'
        s = format_time_code(start_sec, include_hours=True)
        e = format_time_code(end_sec, include_hours=True)
        return f"[{s} - {e}]"


from core.constants import format_speaker_display_name

format_speaker_name = format_speaker_display_name


def group_segments_into_dialogue_turns(
    transcript: Dict[str, Any],
    max_pause_seconds: float = 2.2,
    separate_steps: bool = True,
    max_turn_duration: float = 32.0,
) -> List[Dict[str, Any]]:
    """
    Aggregates fine-grained ASR segments into natural dialogue turns.
    Merges consecutive utterances by the same speaker within the conversational pause threshold,
    while respecting instructional step boundaries and conversational turn caps.
    """
    segments = transcript.get("segments", [])
    if not segments:
        return []

    # Map speaker metadata
    speaker_map = {}
    for s in transcript.get("speakers", []):
        lbl = s["speaker_label"]
        raw_name = s.get("display_name")
        speaker_map[lbl] = {
            "display_name": format_speaker_name(lbl, raw_name),
            "color_hex": s.get("color_hex", "#2563eb"),
        }

    turns: List[Dict[str, Any]] = []
    current_turn: Optional[Dict[str, Any]] = None

    for seg in segments:
        spk_label = seg.get("speaker_label") or "SPEAKER_00"
        default_name = format_speaker_name(spk_label)
        spk_meta = speaker_map.get(spk_label, {
            "display_name": default_name,
            "color_hex": "#2563eb",
        })

        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue

        seg_start = seg["start_time"]
        seg_end = seg["end_time"]
        seg_words = seg.get("words", [])

        # Detect explicit procedural step or topic boundary
        is_step_boundary = separate_steps and bool(
            re.search(r"^(?:in step \d+|step \d+|now let'?s build)", seg_text, re.IGNORECASE)
        )

        # Check if we should merge with current turn
        should_merge = (
            current_turn is not None and
            current_turn["speaker_label"] == spk_label and
            (seg_start - current_turn["end_time"]) <= max_pause_seconds and
            not is_step_boundary and
            (current_turn["end_time"] - current_turn["start_time"] + (seg_end - seg_start)) < max_turn_duration
        )

        if should_merge and current_turn is not None:
            current_turn["end_time"] = seg_end
            current_turn["text"] += " " + seg_text
            current_turn["words"].extend(seg_words)
            current_turn["segment_ids"].append(seg.get("id"))
            if not current_turn.get("addressed_to") and seg.get("addressed_to"):
                current_turn["addressed_to"] = seg.get("addressed_to")
            if not current_turn.get("turn_intent") and seg.get("turn_intent"):
                current_turn["turn_intent"] = seg.get("turn_intent")
            if "segments" in current_turn:
                current_turn["segments"].append(seg)
        else:
            if current_turn is not None:
                current_turn["duration"] = round(current_turn["end_time"] - current_turn["start_time"], 2)
                words_list = current_turn["text"].split()
                current_turn["word_count"] = len(words_list)
                # Calculate speaking speed: Words Per Minute (WPM)
                dur_minutes = max(current_turn["duration"] / 60.0, 0.01)
                current_turn["wpm"] = int(round(len(words_list) / dur_minutes))
                turns.append(current_turn)

            current_turn = {
                "turn_index": len(turns) + 1,
                "speaker_label": spk_label,
                "display_name": spk_meta["display_name"],
                "color_hex": spk_meta["color_hex"],
                "addressed_to": seg.get("addressed_to"),
                "turn_intent": seg.get("turn_intent"),
                "start_time": seg_start,
                "end_time": seg_end,
                "duration": round(seg_end - seg_start, 2),
                "text": seg_text,
                "words": list(seg_words),
                "segment_ids": [seg.get("id")],
                "segments": [seg],
            }

    if current_turn is not None:
        current_turn["duration"] = round(current_turn["end_time"] - current_turn["start_time"], 2)
        words_list = current_turn["text"].split()
        current_turn["word_count"] = len(words_list)
        dur_minutes = max(current_turn["duration"] / 60.0, 0.01)
        current_turn["wpm"] = int(round(len(words_list) / dur_minutes))
        turns.append(current_turn)

    return turns


def _wrap_text(text: str, width: int = 70, indent: str = "  ") -> str:
    """Wraps text cleanly without breaking words."""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0

    for w in words:
        if current_length + len(w) + (1 if current_line else 0) > width:
            lines.append(indent + " ".join(current_line))
            current_line = [w]
            current_length = len(w)
        else:
            current_line.append(w)
            current_length += len(w) + (1 if len(current_line) > 1 else 0)

    if current_line:
        lines.append(indent + " ".join(current_line))
    return "\n".join(lines)


def generate_script_text(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    style: str = "broadcast",
    timestamp_format: str = "range",
    speaker_case: str = "upper",
    include_stats: bool = True,
) -> str:
    """
    Renders professional formatted script text across industry formats.

    Styles:
      - 'broadcast' / 'production': Broadcast script with header, timestamp cues [00:01:23 - 00:01:45], duration & WPM.
      - 'screenplay': Authentic film screenplay layout with centered characters, parentheticals, and dialogue blocks.
      - 'legal': Official deposition transcript with numbered lines, formal case caption, and verification block.
      - 'podcast' / 'shownotes': Chapter breakdown with clickable timecodes followed by full dialogue turns.
      - 'dialogue': Clean, readable dialogue without time brackets.
      - 'compact': Inline single-line transcript '[01:23] SPEAKER: Dialogue'.
    """
    turns = group_segments_into_dialogue_turns(transcript)
    title = job.get("filename", "Audio/Video Recording") if job else "Transcript Script"
    total_words = transcript.get("word_count") or sum(t.get("word_count", 0) for t in turns)
    language = transcript.get("detected_language", "en").upper()
    total_duration = turns[-1]["end_time"] if turns else 0.0
    duration_str = format_time_code(total_duration, include_hours=True)

    # Speakers summary
    speakers = transcript.get("speakers", [])
    spk_names = [s.get("display_name", s["speaker_label"]) for s in speakers] if speakers else ["Speaker 1"]

    style_lower = style.lower().strip()
    if style_lower in ("production", "broadcast", "interview"):
        style_lower = "broadcast"

    # =========================================================================
    # 1. SCREENPLAY TEMPLATE
    # =========================================================================
    if style_lower == "screenplay":
        lines = [
            "=" * 72,
            f"SCENE: TRANSCRIPT OF {title.upper()}",
            f"RECORDED DURATION: {duration_str}  |  LANGUAGE: {language}  |  TOTAL WORDS: {total_words:,}",
            "=" * 72,
            "",
            f"INT. RECORDING STUDIO - DAY",
            "",
            f"Audio log for {title}. A conversation between {', '.join(spk_names)}.",
            "",
        ]

        for turn in turns:
            spk_display = turn["display_name"]
            if speaker_case == "upper":
                spk_display = spk_display.upper()

            addr = turn.get("addressed_to")
            tc_start = format_time_code(turn["start_time"], include_hours=True)
            tc_end = format_time_code(turn["end_time"], include_hours=True)
            dur = turn["duration"]

            # Character Cue (Centered at 32 spaces)
            char_indent = " " * 30
            paren_indent = " " * 22
            dialogue_indent = " " * 12

            lines.append(f"{char_indent}{spk_display}")
            if addr:
                lines.append(f"{paren_indent}(to {addr}) ({tc_start} - {tc_end}, {dur:.1f}s)")
            else:
                lines.append(f"{paren_indent}({tc_start} - {tc_end}, {dur:.1f}s)")
            lines.append(_wrap_text(turn["text"], width=52, indent=dialogue_indent))
            lines.append("")

        lines.append(" " * 55 + "FADE OUT.")
        return "\n".join(lines).strip() + "\n"

    # =========================================================================
    # 2. LEGAL / DEPOSITION TRANSCRIPT TEMPLATE
    # =========================================================================
    elif style_lower == "legal":
        lines = [
            "  " + "=" * 70,
            "  PROCEEDING: OFFICIAL RECORDING TRANSCRIPTION",
            f"  MATTER:     {title}",
            f"  RECORDED:   {duration_str} ({total_words:,} WORDS, {len(turns)} TURNS)",
            f"  LANGUAGE:   {language}",
            "  APPEARANCES:",
        ]
        for name in spk_names:
            lines.append(f"    - {name}")
        lines.append("  " + "=" * 70)
        lines.append("")

        line_num = 1
        for turn in turns:
            spk_display = turn["display_name"]
            if speaker_case == "upper":
                spk_display = spk_display.upper()

            start_tc = format_time_code(turn["start_time"], include_hours=True, include_ms=True)

            # Speaker heading line
            lines.append(f"{line_num:3d}   [{start_tc}]  {spk_display}:")
            line_num += 1

            # Wrapped dialogue lines with legal line numbers
            wrapped_body = _wrap_text(turn["text"], width=62, indent="").split("\n")
            for body_line in wrapped_body:
                lines.append(f"{line_num:3d}       {body_line}")
                line_num += 1

            # Empty spacer line
            lines.append(f"{line_num:3d}")
            line_num += 1

        lines.append("")
        lines.append("  " + "-" * 70)
        lines.append("  CERTIFICATE OF TRANSCRIPTION:")
        lines.append("  I certify that the above transcription represents a faithful,")
        lines.append(f"  verbatim acoustic record of the recording designated '{title}'.")
        lines.append(f"  Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("  " + "-" * 70)
        return "\n".join(lines).strip() + "\n"

    # =========================================================================
    # 3. PODCAST / SHOW NOTES & YOUTUBE CHAPTERS TEMPLATE
    # =========================================================================
    elif style_lower in ("podcast", "shownotes"):
        lines = [
            f"# {title} - Episode Transcript & Show Notes",
            f"Duration: {duration_str} | Language: {language} | Words: {total_words:,}",
            "",
            "## Episode Chapters & Key Moments",
            "",
        ]

        # Generate chapter timestamps from dialogue turns
        for turn in turns:
            short_tc = format_time_code(turn["start_time"], include_hours=False)
            first_clause = turn["text"].split(".")[0].split("?")[0].split(",")[0].strip()
            if len(first_clause) > 60:
                first_clause = first_clause[:57] + "..."
            lines.append(f"- **{short_tc}** - {turn['display_name']}: {first_clause}")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Complete Dialogue Transcript")
        lines.append("")

        for turn in turns:
            short_tc = format_time_code(turn["start_time"], include_hours=False)
            dur = turn["duration"]
            spk = turn["display_name"]
            addr = turn.get("addressed_to")
            spk_hdr = f"{spk} (to {addr})" if addr else spk
            lines.append(f"**{short_tc}** - **{spk_hdr}** ({dur:.1f}s):")
            lines.append(f"{turn['text']}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    # =========================================================================
    # 4. CLEAN DIALOGUE TEMPLATE (No brackets / timecodes)
    # =========================================================================
    elif style_lower == "dialogue":
        lines = []
        for turn in turns:
            spk = turn["display_name"]
            if speaker_case == "upper":
                spk = spk.upper()
            addr = turn.get("addressed_to")
            spk_hdr = f"{spk} (to {addr}):" if addr else f"{spk}:"
            lines.append(spk_hdr)
            lines.append(f"{turn['text']}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    # =========================================================================
    # 5. COMPACT SINGLE-LINE TEMPLATE
    # =========================================================================
    elif style_lower == "compact":
        lines = []
        for turn in turns:
            tc = format_timestamp_token(turn["start_time"], turn["end_time"], fmt=timestamp_format or "short")
            spk = turn["display_name"].upper() if speaker_case == "upper" else turn["display_name"]
            addr = turn.get("addressed_to")
            spk_label_part = f"{spk} → {addr}" if addr else spk
            prefix = f"{tc} {spk_label_part}: " if tc else f"{spk_label_part}: "
            lines.append(f"{prefix}{turn['text']}")
        return "\n".join(lines).strip() + "\n"

    # =========================================================================
    # 6. BROADCAST / INTERVIEW PRODUCTION SCRIPT (DEFAULT)
    # =========================================================================
    else:
        lines = [
            "=" * 72,
            f"TRANSCRIPTION SCRIPT: {title}",
            f"Recorded Duration: {duration_str} | Language: {language} | Total Words: {total_words:,}",
            f"Speakers ({len(spk_names)}): {', '.join(spk_names)}",
            f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 72,
            "",
        ]

        for turn in turns:
            tc = format_timestamp_token(turn["start_time"], turn["end_time"], fmt=timestamp_format)
            dur_str = f"({turn['duration']:.1f}s)" if include_stats else ""
            wpm_str = f"• {turn.get('wpm', 0)} WPM" if include_stats and turn.get("wpm") else ""
            stats_str = f" {dur_str} {wpm_str}".strip()

            spk = turn["display_name"]
            if speaker_case == "upper":
                spk = spk.upper()

            addr = turn.get("addressed_to")
            spk_hdr = f"{spk} → {addr}:" if addr else f"{spk}:"

            header_parts = []
            if tc:
                header_parts.append(tc)
            if stats_str:
                header_parts.append(stats_str)
            header_parts.append(spk_hdr)

            lines.append("  ".join(header_parts))
            lines.append(_wrap_text(turn["text"], width=72, indent="  "))
            lines.append("")

        return "\n".join(lines).strip() + "\n"


def generate_script_markdown(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None
) -> str:
    """Renders formatted Markdown script with dialogue turn blocks and metadata."""
    turns = group_segments_into_dialogue_turns(transcript)
    title = job.get("filename", "Transcript") if job else "Transcript"
    total_words = transcript.get("word_count") or sum(t["word_count"] for t in turns)
    language = transcript.get("detected_language", "en").upper()
    total_duration = turns[-1]["end_time"] if turns else 0.0
    duration_str = format_time_code(total_duration, include_hours=True)

    lines = [
        f"# Script: {title}",
        "",
        f"> **Duration:** {duration_str} &nbsp;|&nbsp; **Language:** {language} &nbsp;|&nbsp; **Words:** {total_words:,} &nbsp;|&nbsp; **Dialogue Turns:** {len(turns)}",
        "",
        "---",
        "",
    ]

    for turn in turns:
        start_tc = format_time_code(turn["start_time"], include_hours=True)
        end_tc = format_time_code(turn["end_time"], include_hours=True)
        dur = int(round(turn["duration"]))
        spk = turn["display_name"]
        color = turn.get("color_hex", "#2563eb")
        addr = turn.get("addressed_to")
        addr_badge = f" &nbsp; `→ {addr}`" if addr else ""

        lines.append(f"### <span style=\"color:{color}\">●</span> {spk}{addr_badge} &nbsp; `[{start_tc} – {end_tc}]` *({dur}s)*")
        lines.append("")
        lines.append(turn["text"])
        lines.append("")

    return "\n".join(lines)


def generate_script_html(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    default_style: str = "broadcast"
) -> str:
    """
    Renders an interactive, print-ready, multi-template HTML script workstation.
    Allows toggling live between Broadcast, Screenplay, Legal Deposition, Podcast, and Clean Reading formats,
    with embedded search, audio jump-seeking, and zero-dependency printable CSS.
    """
    turns = group_segments_into_dialogue_turns(transcript)
    raw_title = job.get("filename", "Audio Recording Transcript") if job else "Transcript Script"
    job_id = job.get("id", "") if job else ""
    total_words = transcript.get("word_count") or sum(t.get("word_count", 0) for t in turns)
    language = transcript.get("detected_language", "en").upper()
    total_duration = turns[-1]["end_time"] if turns else 0.0
    duration_str = format_time_code(total_duration, include_hours=True)

    speakers = transcript.get("speakers", [])
    spk_names = [s.get("display_name", s["speaker_label"]) for s in speakers] if speakers else ["Speaker 1"]

    import json
    import html
    safe_title = html.escape(raw_title)
    safe_spk_names = ", ".join(html.escape(s) for s in spk_names)
    # OWASP-compliant JSON escaping for inline <script> embedding
    safe_turns_json = json.dumps(turns).replace("<", "\\u003c")
    safe_speakers_json = json.dumps(speakers).replace("<", "\\u003c")

    from engine.exporters.documents import get_tmux_logo_base64
    logo_b64 = get_tmux_logo_base64()
    logo_html = f'<img src="{logo_b64}" alt="TMUX" style="height: 24px; width: auto; object-fit: contain;" />' if logo_b64 else '<span style="font-weight: 800; font-size: 16px; color: #2563eb;">TMUX</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{safe_title} &mdash; TMUX Transcript Script</title>
  <style>
    :root {{
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --border: #e2e8f0;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --primary: #2563eb;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: var(--bg);
      color: var(--text-main);
      line-height: 1.6;
      padding: 30px 20px;
    }}
    .container {{
      max-width: 900px;
      margin: 0 auto;
    }}
    .header-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 20px 24px;
      margin-bottom: 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }}
    .title-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 12px;
    }}
    h1 {{
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
    }}
    .meta-pills {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      font-size: 12px;
      color: var(--text-muted);
      align-items: center;
    }}
    .meta-item strong {{ color: var(--text-main); }}
    .toolbar {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 12px 18px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }}
    .template-selector {{
      display: flex;
      gap: 4px;
      background: #f1f5f9;
      padding: 3px;
      border-radius: 4px;
    }}
    .template-btn {{
      border: none;
      background: transparent;
      padding: 5px 10px;
      font-size: 12px;
      font-weight: 500;
      color: var(--text-muted);
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .template-btn.active {{
      background: white;
      color: var(--text-main);
      box-shadow: 0 1px 2px rgba(0,0,0,0.06);
      font-weight: 600;
    }}
    .tool-actions {{
      display: flex;
      gap: 8px;
      align-items: center;
    }}
    .search-input {{
      border: 1px solid var(--border);
      background: #f8fafc;
      padding: 5px 10px;
      border-radius: 4px;
      font-size: 12px;
      color: var(--text-main);
      outline: none;
      width: 180px;
    }}
    .search-input:focus {{
      border-color: var(--primary);
      background: white;
    }}
    button.btn {{
      background: #0f172a;
      color: white;
      border: none;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }}
    button.btn:hover {{ background: #1e293b; }}
    button.btn-outline {{
      background: white;
      color: var(--text-main);
      border: 1px solid var(--border);
    }}
    button.btn-outline:hover {{ background: #f8fafc; }}

    /* Standard Broadcast Styles */
    .turns-list {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .turn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 16px 20px;
      transition: border-color 0.15s;
    }}
    .turn:hover {{ border-color: #cbd5e1; }}
    .turn-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
      font-size: 12px;
    }}
    .speaker-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-weight: 600;
      color: var(--text-main);
      padding: 2px 8px;
      background: #f1f5f9;
      border-radius: 4px;
      border-left: 3px solid;
    }}
    .speaker-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
    }}
    .timestamp-badge {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      color: var(--text-muted);
      font-size: 11px;
      cursor: pointer;
    }}
    .timestamp-badge:hover {{ color: var(--primary); }}
    .duration-badge {{
      color: #94a3b8;
      font-size: 11px;
      margin-left: auto;
    }}
    .turn-text {{
      font-size: 14px;
      color: #1e293b;
      line-height: 1.65;
    }}

    /* Screenplay Mode Styles */
    .mode-screenplay {{
      font-family: "Courier New", Courier, monospace;
      background: white;
      padding: 40px;
      border: 1px solid var(--border);
      border-radius: 6px;
    }}
    .sp-scene {{
      font-weight: bold;
      margin-bottom: 24px;
      text-transform: uppercase;
    }}
    .sp-block {{
      margin-bottom: 24px;
    }}
    .sp-character {{
      text-align: center;
      font-weight: bold;
      text-transform: uppercase;
      margin-bottom: 2px;
    }}
    .sp-paren {{
      text-align: center;
      font-size: 13px;
      color: #555;
      margin-bottom: 4px;
    }}
    .sp-dialogue {{
      max-width: 480px;
      margin: 0 auto;
      line-height: 1.5;
      font-size: 14px;
    }}

    /* Legal Mode Styles */
    .mode-legal {{
      font-family: "Courier New", Courier, monospace;
      background: white;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 30px;
    }}
    .legal-header {{
      border-bottom: 2px solid #333;
      padding-bottom: 12px;
      margin-bottom: 20px;
      font-size: 12px;
      line-height: 1.5;
    }}
    .legal-line {{
      display: flex;
      font-size: 13px;
      line-height: 1.7;
    }}
    .legal-num {{
      width: 45px;
      color: #94a3b8;
      user-select: none;
      text-align: right;
      padding-right: 15px;
    }}
    .legal-content {{
      flex: 1;
      color: #0f172a;
    }}

    /* Podcast / Show Notes Mode Styles */
    .mode-podcast {{
      background: white;
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 30px;
    }}
    .podcast-chapter {{
      display: flex;
      align-items: baseline;
      gap: 12px;
      padding: 8px 0;
      border-bottom: 1px dashed #f1f5f9;
      font-size: 13px;
    }}
    .podcast-time {{
      font-family: monospace;
      font-weight: bold;
      color: var(--primary);
      width: 60px;
    }}

    @media print {{
      body {{ background: white; padding: 0; }}
      .toolbar, .actions, .audio-player-box {{ display: none !important; }}
      .header-card {{ border: none; box-shadow: none; padding: 10px 0; border-bottom: 2px solid #333; }}
      .turn {{ border: none; box-shadow: none; padding: 8px 0; page-break-inside: avoid; border-bottom: 1px solid #eee; }}
      .mode-screenplay, .mode-legal, .mode-podcast {{ border: none; padding: 0; }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <div class="title-row">
        <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
          {logo_html}
          <h1>{safe_title}</h1>
        </div>
        <div class="actions">
          <button class="btn" onclick="window.print()">Print / Export PDF</button>
        </div>
      </div>
      <div class="meta-pills">
        <span class="meta-item">Duration: <strong>{duration_str}</strong></span>
        <span class="meta-item">&bull;</span>
        <span class="meta-item">Language: <strong>{language}</strong></span>
        <span class="meta-item">&bull;</span>
        <span class="meta-item">Words: <strong>{total_words:,}</strong></span>
        <span class="meta-item">&bull;</span>
        <span class="meta-item">Dialogue Turns: <strong>{len(turns)}</strong></span>
        <span class="meta-item">&bull;</span>
        <span class="meta-item">Speakers: <strong>{safe_spk_names}</strong></span>
      </div>
    </div>

    <!-- Interactive View Toolbar -->
    <div class="toolbar">
      <div class="template-selector">
        <button class="template-btn active" onclick="setTemplate('broadcast', this)">Broadcast</button>
        <button class="template-btn" onclick="setTemplate('screenplay', this)">Screenplay</button>
        <button class="template-btn" onclick="setTemplate('legal', this)">Legal Deposition</button>
        <button class="template-btn" onclick="setTemplate('podcast', this)">Show Notes</button>
        <button class="template-btn" onclick="setTemplate('clean', this)">Clean Dialogue</button>
      </div>

      <div class="tool-actions">
        <input type="text" id="searchInput" class="search-input" placeholder="Search transcript..." oninput="handleSearch(this.value)">
        <button class="btn btn-outline" onclick="copyFullScript()">Copy Script</button>
      </div>
    </div>

    <!-- Dynamic Content Container -->
    <div id="scriptContentArea"></div>
  </div>

  <script>
    const turns = {safe_turns_json};
    let currentTemplate = 'broadcast';
    let searchQuery = '';

    function escapeHtml(str) {{
      return (str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
    }}

    function formatTime(sec, includeHours = false) {{
      const totalSec = Math.floor(sec);
      const s = totalSec % 60;
      const totalMin = Math.floor(totalSec / 60);
      const m = totalMin % 60;
      const h = Math.floor(totalMin / 60);
      if (includeHours || h > 0) {{
        return `${{String(h).padStart(2,'0')}}:${{String(m).padStart(2,'0')}}:${{String(s).padStart(2,'0')}}`;
      }}
      return `${{String(m).padStart(2,'0')}}:${{String(s).padStart(2,'0')}}`;
    }}

    function renderScript() {{
      const area = document.getElementById('scriptContentArea');
      const filteredTurns = turns.filter(t => {{
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (t.text || '').toLowerCase().includes(q) || (t.display_name || '').toLowerCase().includes(q);
      }});

      if (currentTemplate === 'broadcast') {{
        let html = '<div class="turns-list">';
        filteredTurns.forEach(t => {{
          const startTc = formatTime(t.start_time, true);
          const endTc = formatTime(t.end_time, true);
          const dur = Math.round(t.duration);
          const addrBadge = t.addressed_to ? `<span style="font-size:11px; opacity:0.85; margin-left:6px; color:#475569; font-weight:normal;">&rarr; ${{escapeHtml(t.addressed_to)}}${{t.turn_intent && t.turn_intent !== 'statement' ? ` (${{escapeHtml(t.turn_intent)}})` : ''}}</span>` : '';
          html += `
            <div class="turn">
              <div class="turn-header">
                <span class="speaker-pill" style="border-left-color: ${{t.color_hex || '#2563eb'}};">
                  <span class="speaker-dot" style="background-color: ${{t.color_hex || '#2563eb'}};"></span>
                  <span class="speaker-name">${{escapeHtml(t.display_name)}}</span>
                  ${{addrBadge}}
                </span>
                <span class="timestamp-badge">[${{startTc}} &ndash; ${{endTc}}]</span>
                <span class="duration-badge">${{dur}}s &bull; ${{t.word_count}} words</span>
              </div>
              <div class="turn-text">${{escapeHtml(t.text)}}</div>
            </div>`;
        }});
        html += '</div>';
        area.innerHTML = html;
      }} else if (currentTemplate === 'screenplay') {{
        let html = '<div class="mode-screenplay">';
        html += '<div class="sp-scene">INT. RECORDING STUDIO - DAY</div>';
        filteredTurns.forEach(t => {{
          const startTc = formatTime(t.start_time, true);
          const endTc = formatTime(t.end_time, true);
          const addrText = t.addressed_to ? ` <span style="font-size:12px; font-weight:normal; text-transform:none;">(to ${{escapeHtml(t.addressed_to)}})</span>` : '';
          html += `
            <div class="sp-block">
              <div class="sp-character">${{escapeHtml(t.display_name.toUpperCase())}}${{addrText}}</div>
              <div class="sp-paren">(${{startTc}} - ${{endTc}}, ${{t.duration.toFixed(1)}}s)</div>
              <div class="sp-dialogue">${{escapeHtml(t.text)}}</div>
            </div>`;
        }});
        html += '<div style="text-align: right; margin-top: 40px; font-weight: bold;">FADE OUT.</div>';
        html += '</div>';
        area.innerHTML = html;
      }} else if (currentTemplate === 'legal') {{
        let html = '<div class="mode-legal">';
        html += `<div class="legal-header"><strong>PROCEEDING: OFFICIAL TRANSCRIPTION RECORD</strong><br>MATTER: ${{escapeHtml(${json.dumps(raw_title)})}}<br>RECORDED DURATION: ${{escapeHtml(${json.dumps(duration_str)})}}</div>`;
        let lineNo = 1;
        filteredTurns.forEach(t => {{
          const startTc = formatTime(t.start_time, true);
          html += `<div class="legal-line"><div class="legal-num">${{lineNo++}}</div><div class="legal-content"><strong>[${{startTc}}]  ${{escapeHtml(t.display_name.toUpperCase())}}:</strong></div></div>`;
          html += `<div class="legal-line"><div class="legal-num">${{lineNo++}}</div><div class="legal-content">&nbsp;&nbsp;&nbsp;&nbsp;${{escapeHtml(t.text)}}</div></div>`;
          html += `<div class="legal-line"><div class="legal-num">${{lineNo++}}</div><div class="legal-content"></div></div>`;
        }});
        html += '<div style="margin-top: 30px; border-top: 1px solid #333; padding-top: 10px; font-size: 11px;">[CERTIFIED FAITHFUL TRANSCRIPTION RECORD]</div>';
        html += '</div>';
        area.innerHTML = html;
      }} else if (currentTemplate === 'podcast') {{
        let html = '<div class="mode-podcast">';
        html += '<h2 style="font-size: 16px; margin-bottom: 12px;">Chapter Markers</h2>';
        filteredTurns.forEach(t => {{
          const shortTc = formatTime(t.start_time, false);
          const firstClause = t.text.split('.')[0].slice(0, 60);
          html += `<div class="podcast-chapter"><span class="podcast-time">${{shortTc}}</span><span><strong>${{escapeHtml(t.display_name)}}</strong>: ${{escapeHtml(firstClause)}}...</span></div>`;
        }});
        html += '<h2 style="font-size: 16px; margin: 24px 0 12px 0;">Full Dialogue Transcript</h2>';
        filteredTurns.forEach(t => {{
          const shortTc = formatTime(t.start_time, false);
          html += `<p style="margin-bottom: 16px; font-size: 14px;"><strong>[${{shortTc}}] ${{escapeHtml(t.display_name)}}:</strong><br>${{escapeHtml(t.text)}}</p>`;
        }});
        html += '</div>';
        area.innerHTML = html;
      }} else {{ // clean
        let html = '<div style="background: white; border: 1px solid var(--border); border-radius: 6px; padding: 30px;">';
        filteredTurns.forEach(t => {{
          const addrPart = t.addressed_to ? ` &rarr; ${{escapeHtml(t.addressed_to)}}` : '';
          html += `<div style="margin-bottom: 20px;"><strong style="color: var(--primary); font-size: 14px;">${{escapeHtml(t.display_name)}}${{addrPart}}:</strong><p style="margin-top: 4px; font-size: 14px; line-height: 1.6;">${{escapeHtml(t.text)}}</p></div>`;
        }});
        html += '</div>';
        area.innerHTML = html;
      }}
    }}

    function setTemplate(name, btn) {{
      currentTemplate = name;
      document.querySelectorAll('.template-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderScript();
    }}

    function handleSearch(val) {{
      searchQuery = val.trim();
      renderScript();
    }}

    function copyFullScript() {{
      let text = '';
      turns.forEach(t => {{
        text += `[${{formatTime(t.start_time)}} - ${{formatTime(t.end_time)}}] ${{t.display_name}}:\n${{t.text}}\n\n`;
      }});
      navigator.clipboard.writeText(text).then(() => {{
        alert('Script copied to clipboard!');
      }});
    }}

    // Initial render
    renderScript();
  </script>
</body>
</html>"""

