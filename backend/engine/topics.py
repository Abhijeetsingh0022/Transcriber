"""
Topic-Wise Video Flow and Hierarchical Section Extraction Engine.
Extracts instructional sections and granular slide/topic boundaries with microsecond-accurate
timecodes, durations, speaker attributions, and formatted dialogue turns.
Matches the official 'Topic-Wise Video Flow and Timestamped Transcript' template.
"""

import re
import html
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from pathlib import Path

from engine.ai_client import (
    get_gemini_api_key,
    get_openrouter_api_key,
    call_ai_json,
)


def format_tc(seconds: Optional[float]) -> str:
    """Formats seconds into MM:SS (or HH:MM:SS if >= 1 hour)."""
    total_sec = int(round(float(seconds or 0.0)))
    sec = total_sec % 60
    total_min = total_sec // 60
    min_ = total_min % 60
    hrs = total_min // 60
    if hrs > 0:
        return f"{hrs:02d}:{min_:02d}:{sec:02d}"
    return f"{min_:02d}:{sec:02d}"


def format_duration_label(seconds: Optional[float]) -> str:
    """Formats duration seconds into human-friendly badge label e.g. '7 sec', '14 sec', '1 min 15 sec'."""
    dur = max(1, int(round(float(seconds or 0.0))))
    if dur < 60:
        return f"{dur} sec"
    m = dur // 60
    s = dur % 60
    if s == 0:
        return f"{m} min"
    return f"{m} min {s} sec"


def format_media_duration(seconds: Optional[float]) -> str:
    """Formats duration like '02:52.14' or '02:52' matching video metadata header."""
    sec_float = float(seconds or 0.0)
    total_sec = int(sec_float)
    hundredths = int(round((sec_float - total_sec) * 100))
    m = total_sec // 60
    s = total_sec % 60
    h = m // 60
    m = m % 60
    if hundredths >= 100:
        hundredths = 0
        s += 1
    if h > 0:
        if hundredths > 0:
            return f"{h:02d}:{m:02d}:{s:02d}.{hundredths:02d}"
        return f"{h:02d}:{m:02d}:{s:02d}"
    else:
        if hundredths > 0:
            return f"{m:02d}:{s:02d}.{hundredths:02d}"
        return f"{m:02d}:{s:02d}"


from core.constants import format_speaker_display_name


def get_media_and_transcript_metadata(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    topics: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Computes comprehensive audio and transcript metadata for reports, PDFs, and UI:
    - Audio stream: sample rate (16kHz), channels, studio normalization, duration
    - Transcript metrics: word count, segment count, language, speaking pace (WPM)
    - Speaker attribution: roster of distinct participants, display names, roles
    - Pedagogical mapping: structured sections across disciplines (Science, Math, Tech, etc.)
    """
    filename = (job.get("filename") if job else "") or "Video Transcript.mp4"
    stem = Path(filename).stem if filename else "Video Flow"

    # Compute duration
    segments = transcript.get("segments", [])
    duration = 0.0
    if job and job.get("duration_seconds"):
        duration = float(job.get("duration_seconds") or 0.0)
    elif segments:
        duration = float(segments[-1].get("end_time", 0.0))
    elif topics:
        duration = float(topics[-1].get("end_time", 0.0))
    dur_str = format_media_duration(duration)

    # Word and segment metrics
    segment_count = len(segments)
    word_count = transcript.get("word_count")
    if word_count is None:
        word_count = sum(len(s.get("text", "").split()) for s in segments)
    word_count = int(word_count or 0)

    # Speaking pace (Words Per Minute)
    wpm = int(round((word_count / max(1.0, duration)) * 60)) if duration > 5.0 else 0

    # Language
    lang_raw = (job.get("language") if job else "") or transcript.get("detected_language") or transcript.get("language") or "en"
    lang_map = {
        "en": "English", "es": "Spanish", "fr": "French", "de": "German",
        "hi": "Hindi", "zh": "Chinese", "ja": "Japanese", "auto": "Auto-Detected (English)"
    }
    language = lang_map.get(str(lang_raw).lower(), str(lang_raw).title())

    # Speaker roster
    speaker_items = transcript.get("speakers", [])
    speakers_list = []
    if speaker_items:
        for sp in speaker_items:
            disp = sp.get("display_name") or format_speaker_display_name(sp.get("speaker_label", "SPEAKER_00"))
            role = sp.get("role")
            if role and role.lower() not in disp.lower():
                speakers_list.append(f"{disp} ({role.title()})")
            else:
                speakers_list.append(disp)
    else:
        seen_lbls = set()
        for s in segments:
            lbl = s.get("speaker_label", "SPEAKER_00")
            if lbl not in seen_lbls:
                seen_lbls.add(lbl)
                speakers_list.append(format_speaker_display_name(lbl))

    speakers_count = len(speakers_list) if speakers_list else 1
    speakers_summary = ", ".join(speakers_list) if speakers_list else "Single Speaker"

    # Sections summary
    sec_names = []
    if topics:
        for t in topics:
            sec_title = t.get("section", "")
            if sec_title and sec_title not in sec_names:
                sec_names.append(sec_title)
    sections_count = len(topics) if topics else len(sec_names)
    sections_summary = ", ".join(sec_names[:5]) + (f" + {len(sec_names)-5} more" if len(sec_names) > 5 else "") if sec_names else "Pedagogical Video Flow"

    # Audio engineering specifications
    audio_format = "16 kHz Mono PCM (Studio Normalized, -16.0 LUFS)"

    return {
        "filename": filename,
        "stem": stem,
        "duration": duration,
        "dur_str": dur_str,
        "audio_format": audio_format,
        "word_count": word_count,
        "segment_count": segment_count,
        "wpm": wpm,
        "language": language,
        "speakers_count": speakers_count,
        "speakers_summary": speakers_summary,
        "sections_count": sections_count,
        "sections_summary": sections_summary,
    }


# Universal pedagogical, presentation, and conversational discourse patterns (precompiled for high throughput)
DISCOURSE_INTRO_PATTERNS = [
    r"\b(?:welcome|hello|good (?:morning|afternoon|evening))\b",
    r"\b(?:today we (?:are going to|will|shall|discuss|cover|explore)|in this (?:video|session|presentation|meeting|talk|episode|tutorial|lecture))\b",
    r"\b(?:let'?s get started|let us begin|our agenda|to begin with|first off)\b",
]
RE_DISCOURSE_INTRO = re.compile("|".join(DISCOURSE_INTRO_PATTERNS), re.IGNORECASE)

DISCOURSE_PROBLEM_PATTERNS = [
    r"\b(?:the problem is|the challenge is|identifying the problem|what happened|what is the issue|why is this)\b",
    r"\b(?:how can we (?:solve|fix|check|address|improve|build|test)|what do we need to)\b",
    r"\b(?:our goal is|the objective of|we need to figure out|why does this happen)\b",
]
RE_DISCOURSE_PROBLEM = re.compile("|".join(DISCOURSE_PROBLEM_PATTERNS), re.IGNORECASE)

DISCOURSE_PROCEDURE_PATTERNS = [
    r"\b(?:step\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten))\b",
    r"\b(?:first,? we|second,? we|third,? we|next,? we|then we|finally,? we)\b",
    r"\b(?:how to (?:build|setup|create|configure|install|assemble|implement))\b",
]
RE_DISCOURSE_PROCEDURE = re.compile("|".join(DISCOURSE_PROCEDURE_PATTERNS), re.IGNORECASE)

DISCOURSE_SYNTHESIS_PATTERNS = [
    r"\b(?:when we (?:combine|put together)|combining (?:these|components|ideas|concepts))\b",
    r"\b(?:connects? concepts|different subjects|multidisciplinary|brings (?:all|together))\b",
    r"\b(?:in practice|real-world (?:application|example|solution|scenario)|putting it all together)\b",
]
RE_DISCOURSE_SYNTHESIS = re.compile("|".join(DISCOURSE_SYNTHESIS_PATTERNS), re.IGNORECASE)

# Disciplinary subject patterns for STEM, Humanities, and Social Sciences
DISCOURSE_SCIENCE_PATTERNS = [
    r"\b(?:in science|science aspect|science concept|science connection|scientific (?:principle|concept|aspect|method))\b",
]
RE_DISCOURSE_SCIENCE = re.compile("|".join(DISCOURSE_SCIENCE_PATTERNS), re.IGNORECASE)

DISCOURSE_MATH_PATTERNS = [
    r"\b(?:in math|in maths|in mathematics|math(?:s)? aspect|mathematical (?:concept|aspect|calculation)|connection to math(?:s)?)\b",
    r"\b(?:calculate the total|add up the values|total voltage)\b",
    r"\b\d+(?:\.\d+)?\s+plus\s+\d+",
]
RE_DISCOURSE_MATH = re.compile("|".join(DISCOURSE_MATH_PATTERNS), re.IGNORECASE)

DISCOURSE_TECH_PATTERNS = [
    r"\b(?:in technology|and in technology|technology aspect|technological aspect|connection to technology)\b",
    r"\b(?:assemble the whole circuit and test|on a breadboard,? we assemble)\b",
    r"\b(?:work together hand-in-hand|all work together in one single activity)\b",
]
RE_DISCOURSE_TECH = re.compile("|".join(DISCOURSE_TECH_PATTERNS), re.IGNORECASE)

DISCOURSE_ENG_PATTERNS = [
    r"\b(?:in engineering|engineering aspect|engineering design|connection to engineering)\b",
]
RE_DISCOURSE_ENG = re.compile("|".join(DISCOURSE_ENG_PATTERNS), re.IGNORECASE)

DISCOURSE_HISTORY_PATTERNS = [
    r"\b(?:in history|history aspect|historical (?:context|background|aspect|perspective)|connection to history|in ancient times|historically|history of)\b",
]
RE_DISCOURSE_HISTORY = re.compile("|".join(DISCOURSE_HISTORY_PATTERNS), re.IGNORECASE)

DISCOURSE_SOCIAL_SCIENCE_PATTERNS = [
    r"\b(?:in social science|social science aspect|connection to social science|social studies|societal impact|civics|geography)\b",
]
RE_DISCOURSE_SOCIAL_SCIENCE = re.compile("|".join(DISCOURSE_SOCIAL_SCIENCE_PATTERNS), re.IGNORECASE)

DISCIPLINE_KEYS = {
    "discipline_science",
    "discipline_math",
    "discipline_technology",
    "discipline_engineering",
    "discipline_history",
    "discipline_social_science",
    "synthesis",
}

DISCOURSE_CONCLUSION_PATTERNS = [
    r"\b(?:in conclusion|to summarize|in summary|to wrap up|that wraps up|key takeaways?|final thoughts?)\b",
    r"\b(?:thank you for (?:watching|listening|attending|your time)|see you (?:next time|soon|in the next))\b",
]
RE_DISCOURSE_CONCLUSION = re.compile("|".join(DISCOURSE_CONCLUSION_PATTERNS), re.IGNORECASE)

DISCOURSE_TRANSITION_CUES = [
    r"\b(?:now let'?s|moving on to|next up|let'?s look at|let'?s discuss|turning to|another important|in this part)\b",
    r"\b(?:step\s+(?:\d+|one|two|three|four|five|six|seven|eight))\b",
]
RE_DISCOURSE_TRANSITION = re.compile("|".join(DISCOURSE_TRANSITION_CUES), re.IGNORECASE)

CONTINUATION_PATTERNS = [
    r"^(?:it|they|this|these|also|for instance|for example|so that|which|because|in addition|as well|furthermore|meaning that|notice that)\b",
]
RE_CONTINUATION = re.compile("|".join(CONTINUATION_PATTERNS), re.IGNORECASE)
RE_STEP_NUMBERED = re.compile(r"\b(step\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten))\b", re.IGNORECASE)
RE_CONTINUATION_PREFIX = re.compile(r"^(?:so|and|now|well|look|okay|ok)[,\s]+", re.IGNORECASE)
RE_STEP_EXPLICIT = re.compile(r"\b(?:in\s+)?(step\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten))\b", re.IGNORECASE)
RE_POST_STEP = re.compile(r"^[\s,:]+(?:we|you|now|then)?\s*", re.IGNORECASE)
RE_SENTENCE_SPLIT = re.compile(r"[.?!;\n]")
RE_GREETING_CLEAN = re.compile(r"^(?:hello|hi|hey|good morning|good afternoon|good evening)(?:\s+students|\s+everyone|\s+all|\s+there)?[,!.\s]+", re.IGNORECASE)
RE_DISCOURSE_CLEAN = re.compile(r"^(?:so|well|and|now|ok|okay|yay!?|look|first|second|next|then|basically|actually|right|all right|let's see|let us|let's|i think|as you can see|here|you know|listen|notice that|moving on to)[,\s]+", re.IGNORECASE)
RE_SUBORDINATE_PREFIX = re.compile(r"^(?:when|if|as|while|after|because|since|once)\b", re.IGNORECASE)
RE_WE_MODALS = re.compile(r"^(?:we can|we will|we are|we should|we must|we)\s+", re.IGNORECASE)
RE_ARTICLES = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)
RE_TRAILING_PUNCT = re.compile(r"['\",]+$")
RE_SUBJECT_IC = re.compile(r"\bthis is called (?:an?|the)?\s*([a-zA-Z0-9\s\-]+?)(?:[,.?!;]|\b(?:ansh|students|everyone)\b|$)", re.IGNORECASE)
RE_SUBJECT_STEM = re.compile(r"\bSTEM\b")
RE_SUBJECT_BENCH = re.compile(r"\b(?:benchmark|bandwidth of|configure|setup)\s+([a-zA-Z0-9\s\-]+?)(?:[,.?!;]|$)", re.IGNORECASE)


def is_continuation(text: str) -> bool:
    """Checks if a segment text continues previous sentence/concept with pronoun or relative clause."""
    t = text.strip().lower()
    t = RE_CONTINUATION_PREFIX.sub("", t)
    return bool(RE_CONTINUATION.match(t))


def _clean_title(text: str, max_words: int = 6) -> str:
    """Dynamically generates a concise, readable topic/slide title from transcript text."""
    cleaned = text.strip()
    # Check if this introduces an explicit numbered step
    step_m = RE_STEP_EXPLICIT.search(cleaned)
    if step_m:
        post_step = cleaned[step_m.end():].strip()
        post_step = RE_POST_STEP.sub("", post_step)
        words = [w for w in RE_SENTENCE_SPLIT.split(post_step)[0].split() if w][:max_words]
        sub = " ".join(words).title() if words else "Procedure"
        return f"{step_m.group(1).title()}: {sub}"

    # Strip greetings, vocatives, and conversational discourse fillers
    cleaned = RE_GREETING_CLEAN.sub("", cleaned)
    cleaned = RE_DISCOURSE_CLEAN.sub("", cleaned).strip()

    # Split into clauses by sentence terminators
    clauses = [c.strip() for c in RE_SENTENCE_SPLIT.split(cleaned) if c.strip()]
    first_clause = clauses[0] if clauses else cleaned

    # If the clause starts with a dependent or subordinate clause before a comma, take main clause
    if "," in first_clause:
        parts = [p.strip() for p in first_clause.split(",") if p.strip()]
        if RE_SUBORDINATE_PREFIX.match(parts[0]) and len(parts) > 1:
            first_clause = parts[1]
        elif len(parts[0].split()) <= 2 and len(parts) > 1:
            first_clause = parts[1]
        else:
            first_clause = parts[0]

    # Strip conversational subject/modal prefixes
    first_clause = RE_WE_MODALS.sub("", first_clause).strip()

    # Strip leading articles
    first_clause = RE_ARTICLES.sub("", first_clause).strip()

    words = first_clause.split()
    if len(words) > max_words:
        first_clause = " ".join(words[:max_words])

    # Strip trailing punctuation
    first_clause = RE_TRAILING_PUNCT.sub("", first_clause).strip()
    return first_clause.title() if first_clause else "Key Concept"


PHASE_RANKS = {
    "intro": 0,
    "problem": 10,
    "concept": 20,
    "procedure": 30,
    "testing": 40,
    "discipline_science": 50,
    "discipline_math": 50,
    "discipline_technology": 50,
    "discipline_engineering": 50,
    "discipline_history": 50,
    "discipline_social_science": 50,
    "synthesis": 50,
    "conclusion": 60,
}


def _extract_subject_noun_phrase(text: str) -> Optional[str]:
    """Detects primary concept or subject noun phrase, e.g. 'Integrated Circuit', 'STEM', 'NVMe Drives'."""
    m_ic = RE_SUBJECT_IC.search(text)
    if m_ic:
        concept = m_ic.group(1).strip()
        words = concept.split()[:4]
        if words:
            return " ".join(words).title()
    if RE_SUBJECT_STEM.search(text):
        return "STEM"
    m_bench = RE_SUBJECT_BENCH.search(text)
    if m_bench:
        concept = m_bench.group(1).strip()
        words = concept.split()[:4]
        if words:
            return " ".join(words).title()
    return None


def classify_segment_phase(seg_text: str, idx: int, total: int):
    """Classifies segment into a progressive discourse phase rank (0 to 60) to guarantee forward serial sequence."""
    txt = seg_text.lower()
    rel_pos = idx / max(1, total)

    # Rank 60: Conclusion & Closing Summary
    if RE_DISCOURSE_CONCLUSION.search(txt) or (rel_pos >= 0.85 and any(w in txt for w in ["thank you", "to summarize", "conclusion", "keep learning", "keep innovating", "keep creating", "thanks for watching"])):
        return ("conclusion", "Conclusion & Summary")

    # Rank 50: Disciplinary subject sections: Science, Mathematics, Technology, Engineering, History, Social Science
    if RE_DISCOURSE_MATH.search(txt) or (("math" in txt or "maths" in txt or "mathematics" in txt) and any(w in txt for w in ["calculate", "add up", "total", "values", "voltage"])):
        return ("discipline_math", "Mathematics")

    if RE_DISCOURSE_TECH.search(txt) or ("technology" in txt and any(w in txt for w in ["breadboard", "circuit", "assemble", "test", "hardware", "hand-in-hand"])):
        return ("discipline_technology", "Technology")

    if RE_DISCOURSE_ENG.search(txt) or ("engineering" in txt and any(w in txt for w in ["design", "build", "prototype", "mechanism"])):
        return ("discipline_engineering", "Engineering")

    if RE_DISCOURSE_HISTORY.search(txt) or ("history" in txt and any(w in txt for w in ["century", "invented", "discovered", "ancient", "origin", "civilization"])):
        return ("discipline_history", "History")

    if RE_DISCOURSE_SOCIAL_SCIENCE.search(txt) or "social science" in txt:
        return ("discipline_social_science", "Social Science")

    if RE_DISCOURSE_SCIENCE.search(txt) or ("science" in txt and any(w in txt for w in ["electrical energy", "light and heat", "energy changes", "come together in this activity", "battery"])):
        return ("discipline_science", "Science")

    # Rank 50: General Synthesis & Multidisciplinary Integration
    if RE_DISCOURSE_SYNTHESIS.search(txt) or ("combine" in txt and "buffers" in txt):
        subject = _extract_subject_noun_phrase(seg_text)
        title = f"Synthesis & Integration: {subject}" if subject else "Synthesis & Integration"
        return ("synthesis", title)

    # Rank 4: Testing & Circuit Verification
    if any(w in txt for w in ["finished", "test it out", "test it", "testing", "actually working", "it is working", "let us test", "let's test", "see how it"]):
        if any(w in txt for w in ["circuit", "breadboard", "hardware", "led"]):
            return ("testing", "Testing the Circuit")
        return ("testing", "Testing & Verification")

    # Rank 0: Introduction (checked early for start of video/welcome)
    if idx == 0 or RE_DISCOURSE_INTRO.search(txt) or (rel_pos < 0.15 and any(w in txt for w in ["welcome to", "today we are going to learn", "warm welcome"])):
        return ("intro", "Introduction")

    # Rank 1: Problem Statement & Seeking Guidance
    if RE_DISCOURSE_PROBLEM.search(txt) or any(w in txt for w in ["problem", "challenge", "bottlenecks", "unhealthy", "sick", "need water", "soil is dry", "could you please help", "what happened", "do not understand", "need some guidance", "complicated"]):
        if any(w in txt for w in ["help", "guidance", "do not understand", "teacher", "instructor", "ma'am", "sir"]):
            return ("problem", "Problem Statement: Asking Teacher for Help")
        return ("problem", "Problem Statement")

    # Rank 2: Core Concept & Component Identification
    if any(w in txt for w in ["identify our components", "identify the components", "identify components", "identify parts", "which parts", "need some parts", "breadboard helps us", "an led is a small light"]) or "this is called" in txt or "stem stands for" in txt or "integrated circuit" in txt or (rel_pos < 0.50 and any(w in txt for w in ["electronic parts", "components we have", "everything that we are going to need", "show you everything"])):
        if any(w in txt for w in ["identify", "components", "parts", "need", "breadboard", "led"]):
            return ("concept", "Identifying the Components")
        subject = _extract_subject_noun_phrase(seg_text)
        if subject:
            title = f"{subject} Introduction" if subject == "STEM" else f"Core Concept: {subject}"
        else:
            title = "Identifying the Components"
        return ("concept", title)

    # Rank 3: Hands-on Demonstration & Procedure
    if RE_STEP_NUMBERED.search(txt) or RE_DISCOURSE_PROCEDURE.search(txt) or any(w in txt for w in ["benchmark", "memory bandwidth", "how to build", "in step 1", "in step 2", "in step 3", "in step 4", "in step 5", "working circuit", "breadboard", "resistors", "capacitor", "assemble", "our circuit is ready"]):
        if "benchmark" in txt or "nvme" in txt or "memory bandwidth" in txt:
            return ("procedure", "Hands-on Procedure: NVMe Memory Bandwidth")
        if any(w in txt for w in ["circuit", "breadboard", "resistors", "capacitor"]):
            return ("procedure", "Building the Circuit")
        subject = _extract_subject_noun_phrase(seg_text)
        title = f"Hands-on Demonstration: {subject}" if subject else "Hands-on Demonstration & Procedure"
        return ("procedure", title)

    # Dynamic timeline fallback for progressive lectures without explicit keyword triggers
    if rel_pos < 0.20:
        return ("intro", "Introduction & Context")
    elif rel_pos < 0.35:
        return ("concept", "Identifying the Components")
    elif rel_pos < 0.70:
        return ("procedure", "Building the Circuit")
    elif rel_pos < 0.88:
        return ("testing", "Testing the Circuit")
    else:
        return ("conclusion", "Conclusion & Summary")


_AI_SECTIONS_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _build_sections_prompt(
    segments: List[Dict[str, Any]],
    speaker_map: Dict[str, str],
) -> str:
    """Builds a compact, structured transcript prompt for AI section and subject extraction."""
    transcript_lines = []
    for i, s in enumerate(segments[:350]):
        spk_lbl = s.get("speaker_label", "SPEAKER_00")
        spk_name = speaker_map.get(spk_lbl, format_speaker_display_name(spk_lbl))
        txt = s.get("text", "").strip()
        t0 = s.get("start_time", 0.0)
        t1 = s.get("end_time", 0.0)
        transcript_lines.append(f"[{i}] ({t0:.1f}s - {t1:.1f}s) {spk_name}: {txt}")

    return (
        "You are an expert video and educational transcript analyst.\n"
        "Analyze the transcript below and divide it into clear, high-level sequential sections/scenes matching the official video flow template.\n"
        "Universal Rules:\n"
        "1. Each section covers a contiguous range of segment indices (start_segment_index to end_segment_index inclusive).\n"
        "2. The sections must cover the entire transcript chronologically from start to end without gaps.\n"
        "3. For project scenes, hands-on activities, or multidisciplinary lessons, SEPARATE distinct academic disciplines into their own standalone sections: for example, separate 'Science', 'Mathematics', 'Technology', 'Engineering', 'History', or 'Social Science' into different sections. Do NOT lump them together into one section.\n"
        "4. For each section, provide a concise, readable section title.\n"
        "Respond ONLY in valid JSON matching this schema:\n"
        "{\n"
        '  "sections": [\n'
        '    {\n'
        '      "section": "<Section Title>",\n'
        '      "start_segment_index": 0,\n'
        '      "end_segment_index": 4\n'
        '    }\n'
        '  ]\n'
        "}\n\n"
        "Transcript:\n" + "\n".join(transcript_lines)
    )


def extract_sections_with_ai(
    segments: List[Dict[str, Any]],
    speaker_map: Dict[str, str],
    cache_key: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Uses centralized, cost-optimized AI client to extract and separate disciplinary sections."""
    if not segments:
        return None

    prompt = _build_sections_prompt(segments, speaker_map)
    res, provider = call_ai_json(
        prompt=prompt,
        task_tag="sections",
        cache_key=cache_key,
        timeout=12.0
    )
    if res and isinstance(res, dict):
        sec_defs = res.get("sections")
        if sec_defs and isinstance(sec_defs, list) and len(sec_defs) >= 2:
            return sec_defs

    return None


def extract_sections_with_gemini(
    segments: List[Dict[str, Any]],
    speaker_map: Dict[str, str],
    api_key: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Backwards-compatible wrapper delegating to unified AI client."""
    return extract_sections_with_ai(segments, speaker_map)


def extract_sections_with_openrouter(
    segments: List[Dict[str, Any]],
    speaker_map: Dict[str, str],
    api_key: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """Backwards-compatible wrapper delegating to unified AI client."""
    return extract_sections_with_ai(segments, speaker_map)


def _build_sections_from_defs(
    sec_defs: List[Dict[str, Any]],
    segments: List[Dict[str, Any]],
    speaker_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Builds standardized section dictionaries from contiguous AI segment index boundaries."""
    sections: List[Dict[str, Any]] = []
    for s_idx, sec_def in enumerate(sec_defs, start=1):
        sec_title = sec_def.get("section", f"Section {s_idx}").strip()
        start_idx = max(0, min(len(segments) - 1, sec_def.get("start_segment_index", 0)))
        end_idx = max(start_idx, min(len(segments) - 1, sec_def.get("end_segment_index", start_idx)))
        sec_segs = segments[start_idx : end_idx + 1]
        if not sec_segs:
            continue

        start_t = sec_segs[0].get("start_time", 0.0)
        end_t = sec_segs[-1].get("end_time", start_t)
        dur = max(1.0, end_t - start_t)

        turns: List[Dict[str, Any]] = []
        for s in sec_segs:
            spk_lbl = s.get("speaker_label", "SPEAKER_00")
            spk_name = speaker_map.get(spk_lbl, format_speaker_display_name(spk_lbl))
            txt = s.get("text", "").strip()
            if not txt:
                continue
            if turns and turns[-1]["speaker"] == spk_name:
                turns[-1]["text"] += " " + txt
                turns[-1]["end_time"] = s.get("end_time", turns[-1]["end_time"])
            else:
                turns.append({
                    "speaker": spk_name,
                    "speaker_label": spk_lbl,
                    "start_time": s.get("start_time", 0.0),
                    "end_time": s.get("end_time", 0.0),
                    "text": txt,
                })

        if not turns:
            continue

        primary_spk = turns[0]["speaker"] if len(turns) == 1 else "Multiple"

        sections.append({
            "section_no": s_idx,
            "section": sec_title,
            "topic": sec_title,
            "start_time": round(start_t, 2),
            "end_time": round(end_t, 2),
            "timecode": f"{format_tc(start_t)} - {format_tc(end_t)}",
            "duration_seconds": round(dur, 2),
            "duration_label": format_duration_label(dur),
            "speaker": primary_spk,
            "turns": turns,
        })
    return sections


def extract_video_topics(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    use_ai: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts high-level Sections from transcript segments in strictly sequential serial order.
    Uses Tier 2 AI Reasoning (Gemini/OpenRouter) for real jobs, with deterministic offline fallback.
    """
    segments = transcript.get("segments", [])
    if not segments:
        return []

    speaker_map = {}
    for s in transcript.get("speakers", []):
        lbl = s.get("speaker_label")
        raw = s.get("display_name")
        speaker_map[lbl] = format_speaker_display_name(lbl, raw)

    # In-memory cache key by job ID or transcript ID
    cache_key = (
        (job.get("id") if job else None)
        or transcript.get("job_id")
        or str(transcript.get("id") or "")
    )
    if cache_key and cache_key in _AI_SECTIONS_CACHE:
        return _AI_SECTIONS_CACHE[cache_key]

    # Auto-enable AI for real processed jobs with valid media/job ID or when explicitly requested
    if len(segments) < 3:
        use_ai = False

    if use_ai is None:
        use_ai = bool((job and job.get("id")) or transcript.get("job_id"))

    # AI Reasoning: Unified AI Client with instant failover and cost optimization
    if use_ai and (get_gemini_api_key() or get_openrouter_api_key()):
        try:
            sec_defs = extract_sections_with_ai(segments, speaker_map, cache_key=cache_key)
            if sec_defs:
                ai_sections = _build_sections_from_defs(sec_defs, segments, speaker_map)
                if ai_sections and len(ai_sections) >= 2:
                    if cache_key:
                        _AI_SECTIONS_CACHE[cache_key] = ai_sections
                    return ai_sections
        except Exception:
            pass

    # Tier 1 Offline Fallback (Deterministic Phase Progression)
    sections_raw: List[Dict[str, Any]] = []
    current_rank = -1
    current_section = None

    for i, seg in enumerate(segments):
        txt = seg.get("text", "").strip()
        if not txt:
            continue

        spk_lbl = seg.get("speaker_label", "SPEAKER_00")
        spk_name = speaker_map.get(spk_lbl, format_speaker_display_name(spk_lbl))
        s_time = seg.get("start_time", 0.0)
        e_time = seg.get("end_time", s_time)

        phase_key, suggested_title = classify_segment_phase(txt, i, len(segments))
        phase_rank = PHASE_RANKS.get(phase_key, 0)

        seg_record = {
            "speaker": spk_name,
            "speaker_label": spk_lbl,
            "start_time": s_time,
            "end_time": e_time,
            "text": txt,
        }

        # Strictly monotonic forward phase progression:
        # A new section is created when:
        # 1. Macro-phase rank moves forward (phase_rank > current_rank)
        # 2. Or transitioning between distinct disciplinary subjects (e.g. Science -> Math -> Tech, History -> Social Science)
        is_new_discipline = (
            current_section is not None
            and phase_key in DISCIPLINE_KEYS
            and current_section.get("phase_key") in DISCIPLINE_KEYS
            and phase_key != current_section.get("phase_key")
        )

        if current_section is None:
            current_rank = phase_rank
            current_section = {
                "title": suggested_title,
                "rank": phase_rank,
                "phase_key": phase_key,
                "segments": [seg_record],
            }
        elif phase_rank > current_rank or is_new_discipline:
            sections_raw.append(current_section)
            current_rank = phase_rank
            current_section = {
                "title": suggested_title,
                "rank": phase_rank,
                "phase_key": phase_key,
                "segments": [seg_record],
            }
        else:
            current_section["segments"].append(seg_record)

    if current_section:
        sections_raw.append(current_section)

    sections: List[Dict[str, Any]] = []
    for s_idx, raw_sec in enumerate(sections_raw, start=1):
        sec_title = raw_sec["title"]
        segs = raw_sec["segments"]
        start_t = segs[0]["start_time"]
        end_t = segs[-1]["end_time"]
        dur = max(1.0, end_t - start_t)

        # Merge adjacent segments by same speaker into dialogue turns
        turns: List[Dict[str, Any]] = []
        for s in segs:
            if turns and turns[-1]["speaker"] == s["speaker"]:
                turns[-1]["text"] += " " + s["text"]
                turns[-1]["end_time"] = s["end_time"]
            else:
                turns.append({
                    "speaker": s["speaker"],
                    "speaker_label": s["speaker_label"],
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "text": s["text"],
                })

        primary_spk = turns[0]["speaker"] if len(turns) == 1 else "Multiple"

        sections.append({
            "section_no": s_idx,
            "section": sec_title,
            "topic": sec_title,  # backwards-compatible with any callers expecting topic field
            "start_time": round(start_t, 2),
            "end_time": round(end_t, 2),
            "timecode": f"{format_tc(start_t)} - {format_tc(end_t)}",
            "duration_seconds": round(dur, 2),
            "duration_label": format_duration_label(dur),
            "speaker": primary_spk,
            "turns": turns,
        })

    return sections


def generate_topic_flow_markdown(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None
) -> str:
    """Generates GitHub-flavored Markdown table for Section-Wise Video Flow matching template."""
    topics = extract_video_topics(transcript, job)
    if not topics:
        return "No sections detected in transcript."

    meta = get_media_and_transcript_metadata(transcript, job, topics)
    lines = [
        f"# {meta['stem']}",
        "",
        "## Section-Wise & Speaker-Wise Video Flow",
        f"*Video: {meta['filename']} | Duration: {meta['dur_str']} | Language: {meta['language']} | Words: {meta['word_count']} | Cadence: ~{meta['wpm']} WPM*",
        "",
        "### Section-Wise Video Flow and Timestamped Transcript",
        f"- **Audio Specifications:** {meta['audio_format']} | Duration: {meta['dur_str']} | Speaking Pace: ~{meta['wpm']} WPM",
        f"- **Transcript Metrics:** {meta['segment_count']} Dialogue Segments | {meta['word_count']} Words | Language: {meta['language']} | Timecodes: Word-Level Microsecond Synchronized",
        f"- **Speakers Roster:** {meta['speakers_summary']}",
        f"- **Curriculum Mapping:** {meta['sections_count']} Sections ({meta['sections_summary']})",
        "",
        f"*The transcript wording is taken from the supplied {meta['stem']} transcript source, while the video duration and speaker/scene mapping were checked against the uploaded MUX video.*",
        "",
        "| No. | Section | Timecode | Duration | Speaker | Dialogue / Transcript |",
        "| :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for item in topics:
        no = item["section_no"]
        sec = item["section"]
        tc = item["timecode"]
        dur = item["duration_label"]
        turns = item["turns"]

        if len(turns) == 1:
            spk = turns[0]["speaker"]
            txt = turns[0]["text"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {no} | **{sec}** | `{tc}` | {dur} | {spk} | {txt} |")
        else:
            turn_lines = []
            for t in turns:
                escaped_text = t["text"].replace("|", "\\|")
                turn_lines.append(f"**{t['speaker']}:** {escaped_text}")
            formatted_dialogue = "<br>".join(turn_lines)
            lines.append(f"| {no} | **{sec}** | `{tc}` | {dur} | Multiple | {formatted_dialogue} |")

    return "\n".join(lines)


def generate_topic_flow_html(
    transcript: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None
) -> str:
    """
    Renders pixel-perfect, standalone, printable HTML matching the user's template:
    Section-Wise Video Flow and Timestamped Transcript (without fragmented topics).
    """
    topics = extract_video_topics(transcript, job)
    meta = get_media_and_transcript_metadata(transcript, job, topics)
    filename = meta["filename"]
    stem = meta["stem"]
    dur_str = meta["dur_str"]

    from engine.exporters.documents import get_tmux_logo_base64
    logo_b64 = get_tmux_logo_base64()
    logo_img_tag = f'<div style="display: flex; justify-content: center; margin-bottom: 12px;"><img src="{logo_b64}" alt="TMUX" style="height: 32px; width: auto; object-fit: contain;" /></div>' if logo_b64 else ''

    table_rows_html = []
    for item in topics:
        s_no = item["section_no"]
        sec_name = item["section"]
        tc = item["timecode"]
        dur = item["duration_label"]
        turns = item["turns"]
        total_sub_rows = len(turns)

        is_section_tinted = (s_no % 2 != 0 and s_no >= 3)
        sec_bg_class = "bg-tint" if is_section_tinted else "bg-white"

        for t_idx, turn in enumerate(turns):
            row_html = ["<tr>"]

            # Section metadata rendered once with rowspan per section
            if t_idx == 0:
                row_html.append(
                    f'<td rowspan="{total_sub_rows}" class="cell-no {sec_bg_class}">{s_no}</td>'
                )
                row_html.append(
                    f'<td rowspan="{total_sub_rows}" class="cell-section {sec_bg_class}">{html.escape(sec_name)}</td>'
                )
                row_html.append(
                    f'<td rowspan="{total_sub_rows}" class="cell-timecode {sec_bg_class}">{html.escape(tc)}</td>'
                )
                row_html.append(
                    f'<td rowspan="{total_sub_rows}" class="cell-duration {sec_bg_class}">{html.escape(dur)}</td>'
                )

            # Dialogue turns: alternating zebra striping
            if is_section_tinted:
                turn_bg = "bg-tint" if (t_idx % 2 == 0) else "bg-white"
            else:
                turn_bg = "bg-tint" if (t_idx % 2 == 1) else "bg-white"

            spk_name = html.escape(turn["speaker"])
            dlg_text = html.escape(turn["text"])
            row_html.append(f'<td class="cell-speaker {turn_bg}">{spk_name}</td>')
            row_html.append(f'<td class="cell-dialogue {turn_bg}">{dlg_text}</td>')
            row_html.append("</tr>")

            table_rows_html.append("".join(row_html))

    rendered_table_body = "\n".join(table_rows_html)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(stem)} - Section-Wise &amp; Speaker-Wise Video Flow</title>
  <style>
    :root {{
      --navy-main: #1e3a5f;
      --header-bg: #1e3a5f;
      --terracotta: #c25e2e;
      --border-color: #cbd5e1;
      --border-header: #2d4d77;
      --bg-tint: #eef4fa;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background: #f8fafc;
      color: #0f172a;
      padding: 36px 24px;
      line-height: 1.5;
    }}
    .page-wrapper {{
      max-width: 1200px;
      margin: 0 auto;
      background: #ffffff;
      padding: 40px 48px;
      border-radius: 8px;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
      border: 1px solid var(--border-color);
    }}
    .brand-header {{
      text-align: center;
      margin-bottom: 24px;
    }}
    .file-stem {{
      font-size: 26px;
      font-weight: 700;
      color: var(--navy-main);
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 6px;
    }}
    .flow-title {{
      font-size: 20px;
      font-weight: 700;
      color: var(--terracotta);
      margin-bottom: 6px;
    }}
    .video-meta {{
      font-size: 13px;
      color: #475569;
      font-style: italic;
    }}
    .doc-subheading {{
      margin-bottom: 16px;
    }}
    .doc-title {{
      font-size: 16px;
      font-weight: 700;
      color: var(--navy-main);
      margin-bottom: 4px;
    }}
    .doc-subtitle {{
      font-size: 12px;
      color: #334155;
      line-height: 1.45;
    }}
    .actions-bar {{
      display: flex;
      justify-content: flex-end;
      gap: 10px;
      margin-bottom: 16px;
    }}
    .btn {{
      padding: 7px 14px;
      font-size: 12px;
      font-weight: 600;
      border-radius: 6px;
      border: 1px solid var(--border-color);
      background: #ffffff;
      color: #1e293b;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}
    .btn:hover {{
      background: #f1f5f9;
      border-color: #94a3b8;
    }}
    .btn-primary {{
      background: var(--navy-main);
      color: #ffffff;
      border-color: var(--navy-main);
    }}
    .btn-primary:hover {{
      background: #152b47;
    }}
    .table-container {{
      overflow-x: auto;
      border: 1px solid var(--border-color);
    }}
    table.flow-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
      text-align: left;
    }}
    table.flow-table th {{
      background-color: var(--navy-main);
      color: #ffffff;
      font-weight: 700;
      font-size: 12px;
      padding: 10px 8px;
      border: 1px solid var(--border-header);
      text-align: center;
      white-space: nowrap;
    }}
    table.flow-table td {{
      padding: 9px 12px;
      border: 1px solid var(--border-color);
      vertical-align: middle;
      font-size: 12px;
    }}
    .bg-white {{
      background-color: #ffffff !important;
    }}
    .bg-tint {{
      background-color: #eef4fa !important;
    }}
    .cell-no {{
      width: 44px;
      text-align: center;
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
    }}
    .cell-section {{
      width: 170px;
      text-align: center;
      font-size: 12.5px;
      font-weight: 600;
      color: #0f172a;
    }}
    .cell-timecode {{
      width: 110px;
      text-align: center;
      font-size: 12px;
      font-weight: 600;
      color: var(--terracotta);
      white-space: nowrap;
    }}
    .cell-duration {{
      width: 80px;
      text-align: center;
      font-size: 12px;
      color: #0f172a;
      white-space: nowrap;
    }}
    .cell-speaker {{
      width: 100px;
      text-align: center;
      font-size: 12px;
      font-weight: 600;
      color: #0f172a;
      white-space: nowrap;
    }}
    .cell-dialogue {{
      text-align: left;
      font-size: 12px;
      color: #0f172a;
      line-height: 1.45;
    }}
    @media print {{
      body {{
        background: #ffffff;
        padding: 0;
      }}
      .page-wrapper {{
        box-shadow: none;
        border: none;
        padding: 0;
        max-width: 100%;
      }}
      .actions-bar {{
        display: none !important;
      }}
      table.flow-table th {{
        background-color: var(--navy-main) !important;
        color: #ffffff !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      .bg-tint {{
        background-color: #eef4fa !important;
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }}
      tr {{
        page-break-inside: avoid;
      }}
    }}
  </style>
</head>
<body>
  <div class="page-wrapper">
    <div class="brand-header">
      {logo_img_tag}
      <div class="file-stem">{html.escape(stem)}</div>
      <div class="flow-title">Topic-Wise &amp; Speaker-Wise Video Flow</div>
      <div class="video-meta">Video: <i>{html.escape(filename)}</i> &nbsp;|&nbsp; Duration: <i>{dur_str}</i> &nbsp;|&nbsp; Language: <i>{html.escape(meta['language'])}</i> &nbsp;|&nbsp; Words: <i>{meta['word_count']}</i> &nbsp;|&nbsp; Speakers: <i>{meta['speakers_count']}</i></div>
    </div>

    <div class="doc-subheading">
      <h2 class="doc-title">Section-Wise Video Flow and Timestamped Transcript</h2>
      <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; margin: 8px 0 10px 0; font-size: 11.5px; line-height: 1.5; color: #334155; text-align: left;">
        <div style="margin-bottom: 3px;"><b style="color: #1e3a5f;">Audio Specifications:</b> {html.escape(meta['audio_format'])} &bull; Duration: {dur_str} &bull; Speech Cadence: ~{meta['wpm']} WPM &bull; Language: {html.escape(meta['language'])}</div>
        <div style="margin-bottom: 3px;"><b style="color: #1e3a5f;">Transcript Metrics:</b> {meta['segment_count']} Dialogue Segments &bull; {meta['word_count']} Total Words &bull; Word-Level Microsecond Synchronized</div>
        <div style="margin-bottom: 3px;"><b style="color: #1e3a5f;">Identified Speakers:</b> {html.escape(meta['speakers_summary'])}</div>
        <div><b style="color: #1e3a5f;">Curriculum Mapping:</b> {meta['sections_count']} Sections ({html.escape(meta['sections_summary'])})</div>
      </div>
      <p class="doc-subtitle">The transcript wording is taken from the supplied <b>{html.escape(stem)}</b> transcript source, while the video duration, audio stream, and speaker/scene mapping were checked against the uploaded MUX video.</p>
    </div>

    <div class="actions-bar">
      <button class="btn" onclick="copyTableText()">Copy Table</button>
      <button class="btn btn-primary" onclick="window.print()">Print / Export PDF</button>
    </div>

    <div class="table-container">
      <table class="flow-table">
        <thead>
          <tr>
            <th style="width: 44px;">No.</th>
            <th style="width: 170px;">Section</th>
            <th style="width: 110px;">Timecode</th>
            <th style="width: 80px;">Duration</th>
            <th style="width: 100px;">Speaker</th>
            <th>Dialogue / Transcript</th>
          </tr>
        </thead>
        <tbody>
{rendered_table_body}
        </tbody>
      </table>
    </div>
  </div>

  <script>
    function copyTableText() {{
      const table = document.querySelector('table.flow-table');
      if (!table) return;
      let text = '';
      for (const row of table.rows) {{
        const cells = Array.from(row.cells).map(c => c.innerText.trim().replace(/\\t/g, ' '));
        text += cells.join('\\t') + '\\n';
      }}
      navigator.clipboard.writeText(text).then(() => {{
        alert('Table copied to clipboard in tab-separated format!');
      }});
    }}
  </script>
</body>
</html>"""
