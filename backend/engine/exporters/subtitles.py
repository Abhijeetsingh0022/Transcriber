import re
from typing import List, Dict, Any, Optional, Tuple
from engine.exporters.script import format_speaker_name

_VTT_CLEAN_SPEAKER_RE = re.compile(r"[<>\r\n]")


def _format_time_parts(seconds: Optional[float]) -> Tuple[int, int, int, int]:
    """Splits seconds into (hours, minutes, seconds, milliseconds) using C-speed divmod."""
    total_ms = int(round(float(seconds or 0.0) * 1000))
    total_sec, ms = divmod(total_ms, 1000)
    total_min, sec = divmod(total_sec, 60)
    hrs, min_ = divmod(total_min, 60)
    return hrs, min_, sec, ms


def format_timestamp_srt(seconds: Optional[float]) -> str:
    """Formats seconds to SRT format: HH:MM:SS,mmm"""
    hrs, min_, sec, ms = _format_time_parts(seconds)
    return f"{hrs:02d}:{min_:02d}:{sec:02d},{ms:03d}"


def format_timestamp_vtt(seconds: Optional[float]) -> str:
    """Formats seconds to WebVTT format: HH:MM:SS.mmm"""
    hrs, min_, sec, ms = _format_time_parts(seconds)
    return f"{hrs:02d}:{min_:02d}:{sec:02d}.{ms:03d}"


def generate_srt(segments: List[Dict[str, Any]], speakers: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Serializes transcript segments into a valid SubRip (.srt) subtitle string.
    """
    speaker_map = {
        s["speaker_label"]: format_speaker_name(s["speaker_label"], s.get("display_name"))
        for s in (speakers or [])
    }
    lines = []
    idx = 1

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        raw_speaker = seg.get("speaker_label")
        if raw_speaker:
            speaker = speaker_map.get(raw_speaker, format_speaker_name(raw_speaker))
            display_text = f"[{speaker}] {text}"
        else:
            display_text = text

        start_tc = format_timestamp_srt(seg.get("start_time"))
        end_tc = format_timestamp_srt(seg.get("end_time"))

        lines.append(f"{idx}")
        lines.append(f"{start_tc} --> {end_tc}")
        lines.append(display_text)
        lines.append("")  # Blank line separator
        idx += 1

    return "\n".join(lines)


def generate_vtt(segments: List[Dict[str, Any]], speakers: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Serializes transcript segments into a valid WebVTT (.vtt) subtitle string.
    """
    speaker_map = {
        s["speaker_label"]: format_speaker_name(s["speaker_label"], s.get("display_name"))
        for s in (speakers or [])
    }
    lines = ["WEBVTT\n"]
    idx = 1

    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        raw_speaker = seg.get("speaker_label")
        if raw_speaker:
            raw_name = speaker_map.get(raw_speaker, format_speaker_name(raw_speaker))
            clean_speaker = _VTT_CLEAN_SPEAKER_RE.sub("", str(raw_name)).strip() or "Speaker"
            display_text = f"<v {clean_speaker}>{text}</v>"
        else:
            display_text = text

        start_tc = format_timestamp_vtt(seg.get("start_time"))
        end_tc = format_timestamp_vtt(seg.get("end_time"))

        lines.append(f"{idx}")
        lines.append(f"{start_tc} --> {end_tc}")
        lines.append(display_text)
        lines.append("")  # Blank line separator
        idx += 1

    return "\n".join(lines)
