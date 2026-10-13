"""
Real-Time Speaker & Role Identification Engine for Video Transcription.
Driven by real-time audio data and generative AI reasoning (Gemini / OpenRouter / TokenHarbor),
with an acoustic- and discourse-driven offline fallback.
Eliminates hardcoded keyword dictionaries and mock personas.
"""

import re
import functools
from typing import List, Dict, Any, Tuple, Optional

# Accessible color palette for identified roles and speakers
ROLE_PALETTES = {
    "narrator": "#d97706",    # Warm Amber
    "instructor": "#059669",  # Emerald Green
    "primary": "#2563eb",     # Royal Blue
    "secondary": "#0284c7",   # Sky Blue
    "tertiary": "#0d9488",    # Teal
    "quaternary": "#06b6d4",  # Cyan
}

# Minimal set of capitalized English tokens that are grammatical function words (pronouns, conjunctions, adverbs)
# rather than personal names when appearing capitalized in Whisper transcripts
NON_NAME_TOKENS = {
    "the", "this", "that", "these", "those", "there", "here",
    "what", "when", "where", "why", "how", "who", "whom", "whose", "which",
    "today", "yesterday", "tomorrow", "tonight", "now", "then", "first", "next",
    "please", "thank", "thanks", "hello", "welcome", "everyone", "students",
    "yes", "yeah", "yep", "no", "nope", "okay", "ok", "sure", "well",
    "and", "but", "or", "so", "because", "although", "since", "while",
    "video", "lesson", "session", "episode", "chapter", "slide", "step",
}

# Normalization patterns for speech transcripts
_NORM_APOSTROPHES = re.compile(r"[’‘`]")
_NORM_QUOTES = re.compile(r'[“”]')
_NORM_CONTRACTIONS = re.compile(r"\b([a-zA-Z]+)\s*'\s*([a-zA-Z]+)\b")
_NORM_HYPHEN_CODES = re.compile(r"\b([A-Za-z]{2,6})\s*[-–]\s*(\d{2,5})\b")
_NORM_SPACED_CODES = re.compile(r"\b([A-Za-z]{2,6})\s+(\d{3,5})\b")
_NORM_SPACES = re.compile(r"\s+")

# Real-time syntactic sentence & clause continuity
_TERMINAL_PUNCTUATION = {".", "!", "?", "।", "॥", "؟", "。", "！", "？"}
_CONTINUATION_PUNCTUATION = {",", ";", ":", "-", "—", "–", "...", "…", "/"}
_RE_COORDINATING_CONJUNCTION = re.compile(
    r"^(?:and|or|but|nor|yet|so|which|who|whom|whose|where|when|that|because|as|aur|ya|tatha|evam|par|lekin|jo|jisse|jisme|ki)\b",
    re.IGNORECASE,
)
_RE_DIRECT_DIALOGUE_STARTER = re.compile(
    r"^(?:hello|hi|hey|excuse me|listen|look|wait|teacher|sir|ma'?am|madam|dr|doctor|prof|professor)\b",
    re.IGNORECASE,
)

# Minimal grammatical pattern recognizers for natural dialogue
_RE_SELF_INTRO = re.compile(r"\b(?:my name is|i am|i'm)\s+([A-Z][a-z]+)\b", re.IGNORECASE)
_RE_INTRO_NAME = re.compile(r"\b(?:meet|welcome|joined by|this is)\s+([A-Z][a-z]+)\b", re.IGNORECASE)
_RE_TITLE_NAME = re.compile(r"\b(?:dr|doctor|prof|professor|mr|mrs|ms)\.?\s+([A-Z][a-z]+)\b", re.IGNORECASE)
_RE_START_VOCATIVE = re.compile(r"^([A-Z][a-z]+),\s+[a-z]", re.IGNORECASE)
_RE_END_VOCATIVE = re.compile(r",\s*([A-Z][a-z]+)[?.!]")
_RE_PRAISE_VOCATIVE = re.compile(
    r"\b(?:good question|great question|sure|thanks|thank you|well done|correct)\s*,?\s*([A-Z][a-z]+)\b",
    re.IGNORECASE,
)
_RE_HONORIFIC_VOCATIVE = re.compile(r"\b(teacher|ma'am|sir|doctor|professor)\b", re.IGNORECASE)
_RE_CONFIRMATION_START = re.compile(r"^(?:yes|yeah|yep|understood|got it|right|okay|ok|sure|thank you)\b", re.IGNORECASE)
_RE_NARRATOR_MINIMAL = re.compile(
    r"\b(?:welcome to\b|welcome back\b|today we (?:will|are going to|shall)|thanks? for watching|thank you for watching)\b",
    re.IGNORECASE,
)


def normalize_speech_text(text: str) -> str:
    """
    Universal speech transcript normalizer.
    Cleans up contractions, punctuation spacing, quotation marks, and
    spaced alphanumeric model/part codes (e.g. 'XYZ - 100' -> 'XYZ100').
    """
    if not text:
        return ""
    t = text.strip()
    t = _NORM_APOSTROPHES.sub("'", t)
    t = _NORM_QUOTES.sub('"', t)
    t = _NORM_CONTRACTIONS.sub(r"\1'\2", t)
    t = _NORM_HYPHEN_CODES.sub(r"\1\2", t)
    t = _NORM_SPACED_CODES.sub(r"\1\2", t)
    return _NORM_SPACES.sub(" ", t)


def is_narrator_text(text: str) -> bool:
    """Checks if a segment text contains standard narrative opening, framing, or outro markers."""
    t_lower = normalize_speech_text(text).lower()
    return bool(_RE_NARRATOR_MINIMAL.search(t_lower))


def is_sentence_continuation(
    prev_seg: Optional[Dict[str, Any]],
    curr_seg: Optional[Dict[str, Any]],
    max_gap: float = 2.5,
) -> bool:
    """
    Determines whether curr_seg is a direct syntactic/sentence continuation of prev_seg.
    Speech transcribers (like Whisper) frequently split a single sentence across audio chunk
    boundaries (e.g. at pauses or commas). A segment continuing an ongoing clause or sentence
    MUST retain the same speaker and addressee as the preceding segment.
    """
    if not prev_seg or not curr_seg:
        return False
    prev_text = (prev_seg.get("text") or "").strip()
    curr_text = (curr_seg.get("text") or "").strip()
    if not prev_text or not curr_text:
        return False

    prev_end = float(prev_seg.get("end_time") or 0.0)
    curr_start = float(curr_seg.get("start_time") or 0.0)
    time_gap = max(0.0, curr_start - prev_end)
    if time_gap > max_gap:
        return False

    # Explicit conversational addresses/dialogue starters signal a turn boundary
    if _RE_DIRECT_DIALOGUE_STARTER.search(curr_text):
        return False

    prev_last_char = prev_text[-1]
    ends_terminal = prev_last_char in _TERMINAL_PUNCTUATION
    ends_continuation = prev_last_char in _CONTINUATION_PUNCTUATION or prev_text.endswith("...")
    starts_lower = curr_text[0].islower()
    starts_symbol = not curr_text[0].isalnum()
    starts_conj = bool(_RE_COORDINATING_CONJUNCTION.search(curr_text))

    # 1. Trailing continuation punctuation (comma, dash, ellipsis, semicolon, colon)
    if ends_continuation:
        return True

    # 2. Previous ended without terminal punctuation (raw chunk break mid-clause)
    if not ends_terminal:
        if starts_lower or starts_conj or starts_symbol or time_gap <= 1.5:
            return True

    # 3. Current starts with lowercase or coordinating conjunction within close time window
    if (starts_lower or starts_conj) and time_gap <= 1.2:
        return True

    return False


@functools.lru_cache(maxsize=128)
def _get_compiled_vocative_rules(name: str):
    """Pre-compiles regex patterns for a character name for fast evaluation."""
    n_esc = re.escape(name)
    n_low = re.escape(name.lower())
    exclude_framing = re.compile(rf"\b(?:meet|about|with|introducing|and so|now let us meet|call)\s+{n_low}\b", re.IGNORECASE)
    exclude_decl = re.compile(rf"\b{n_low}\s+(?:is|was|has|had|does|did|finds|goes|went|said|says|wants|wished|asked)\b", re.IGNORECASE)
    pos_start = re.compile(rf"^{n_esc},\s+", re.IGNORECASE)
    pos_end = re.compile(rf",\s*{n_esc}[?.!]$|\b{n_esc}\?$", re.IGNORECASE)
    pos_imperative = re.compile(rf"\b(?:sure|understand|listen|hello|hi|hey|tell me|thanks|thank you|good question|great question|yes|well said|well done)\s*,?\s*{n_esc}\b", re.IGNORECASE)
    pos_parenthetical = re.compile(rf",\s*{n_esc},\s*", re.IGNORECASE)
    return exclude_framing, exclude_decl, pos_start, pos_end, pos_imperative, pos_parenthetical


def is_direct_vocative_to(name: str, text: str) -> bool:
    """
    Determines whether a character name is being directly addressed (vocative case)
    versus merely mentioned in third-person (e.g. 'meet David' or 'David went').
    """
    if not name:
        return False
    norm = normalize_speech_text(text)
    ex_frame, ex_decl, p_start, p_end, p_imp, p_paren = _get_compiled_vocative_rules(name)

    if ex_frame.search(norm) or ex_decl.search(norm):
        return False

    return bool(p_start.search(norm) or p_end.search(norm) or p_imp.search(norm) or p_paren.search(norm))


def extract_vocatives_and_mentions(segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extracts real participant names and honorifics dynamically from transcript segments
    using natural linguistic grammar (introductions, vocatives, self-introductions).
    """
    mentions: Dict[str, List[int]] = {}
    honorifics: List[str] = []

    def _add(raw_name: str, idx: int):
        clean = raw_name.strip().capitalize()
        if clean.lower() not in NON_NAME_TOKENS and len(clean) >= 3:
            mentions.setdefault(clean, []).append(idx)

    for seg in segments:
        text = normalize_speech_text(seg.get("text", ""))
        idx = seg.get("segment_index", seg.get("index", 0))

        # Honorific vocatives spoken in dialogue (e.g. "Teacher", "Ma'am", "Sir", "Doctor")
        for m_h in _RE_HONORIFIC_VOCATIVE.finditer(text):
            h_word = m_h.group(1).lower()
            if h_word in ["ma'am", "sir", "teacher"]:
                honorifics.append("Teacher")
            else:
                honorifics.append(h_word.capitalize())

        # Title + Name: "Dr. Smith", "Professor Charles", "Mr. Anderson"
        for m in _RE_TITLE_NAME.finditer(text):
            _add(m.group(1), idx)

        # Introductions: "meet David", "welcome Sarah", "joined by Alex"
        for m in _RE_INTRO_NAME.finditer(text):
            _add(m.group(1), idx)

        # Direct self-introduction: "I am Alex", "My name is Priya"
        for m in _RE_SELF_INTRO.finditer(text):
            _add(m.group(1), idx)

        # Sentence-initial vocative: "Sarah, this is..."
        for m in _RE_START_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

        # Sentence-final vocative: "What is this, Kunal?"
        for m in _RE_END_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

        # Conversational praise or phrasal address: "Good question Kunal", "Thanks Sarah"
        for m in _RE_PRAISE_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

    honorific_set = {h.lower() for h in honorifics}
    sorted_names = [
        name for name, _ in sorted(mentions.items(), key=lambda kv: len(kv[1]), reverse=True)
        if name.lower() not in honorific_set
    ]

    return {
        "names": sorted_names,
        "honorifics": list(dict.fromkeys(honorifics)),
    }


def identify_speakers_for_segments(
    segments: List[Dict[str, Any]],
    num_speakers: Optional[int] = 3,
    tier: str = "auto",
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Real-time speaker & role identification algorithm.
    - Tier 2 (Primary / Default): Multi-Provider Generative AI Semantic Reasoner (Gemini / OpenRouter / TokenHarbor).
      Operates on pure real-time transcript data, dynamically generating characters, roles, and turns.
    - Tier 1 (Offline Fallback): Data-driven attribution based on acoustic clusters, spoken dialogue vocatives,
      and syntactic sentence continuity.
    """
    target_speakers = int(num_speakers) if num_speakers is not None else 3

    if not segments:
        return {
            "tier": "tier1_local",
            "speakers": [],
            "segment_assignments": {},
            "addressee_assignments": {},
            "intent_assignments": {},
            "student_name": "Speaker 1",
            "teacher_name": "Speaker 2",
            "primary_name": "Speaker 1",
            "secondary_name": "Speaker 2",
            "narrator_count": 0,
            "total_segments": 0,
        }

    # -------------------------------------------------------------
    # TIER 2: PURE REAL-TIME GENERATIVE AI REASONING
    # -------------------------------------------------------------
    if tier in ["auto", "tier2"]:
        try:
            from engine.gemini_speaker_id import identify_speakers_with_ai
            ai_res = identify_speakers_with_ai(
                segments,
                target_speakers,
                gemini_api_key=gemini_api_key,
                openrouter_api_key=openrouter_api_key,
            )
            if ai_res and ai_res.get("success"):
                spks = ai_res.get("speakers", [])
                s0 = spks[0]["display_name"] if len(spks) > 0 else "Speaker 1"
                s1 = spks[1]["display_name"] if len(spks) > 1 else "Speaker 2"

                # Dynamic role resolution (avoid hardcoding Narrator as student!)
                teacher_spk = next((s for s in spks if "teacher" in s.get("role", "").lower() or "teacher" in s.get("display_name", "").lower()), None)
                student_spk = next((s for s in spks if "student" in s.get("role", "").lower() or ("narrator" not in s.get("display_name", "").lower() and s != teacher_spk)), None)

                ai_res["student_name"] = student_spk["display_name"] if student_spk else s0
                ai_res["teacher_name"] = teacher_spk["display_name"] if teacher_spk else s1
                ai_res["primary_name"] = student_spk["display_name"] if student_spk else s0
                ai_res["secondary_name"] = teacher_spk["display_name"] if teacher_spk else s1
                ai_res["summary"] = " • ".join(
                    f"{s['display_name']} ({s['role']})" if s.get('role') and s['role'].lower() != s['display_name'].lower() else s['display_name']
                    for s in spks
                )
                ai_res["total_segments"] = len(segments)
                ai_res["narrator_count"] = sum(
                    1 for v in ai_res.get("addressee_assignments", {}).values() if v == "Audience"
                )
                return ai_res
        except Exception:
            pass  # Fall back to data-driven offline processing

    n_total = len(segments)

    # -------------------------------------------------------------
    # TIER 1: DATA-DRIVEN OFFLINE FALLBACK
    # -------------------------------------------------------------
    extracted_data = extract_vocatives_and_mentions(segments)
    extracted_names = extracted_data["names"]
    honorifics = extracted_data["honorifics"]

    # Detect opening / closing narrative blocks from transcript structure
    narrator_indices = set()
    first_interactive_turn = n_total

    # Find the first direct conversational interaction (e.g. vocative or question)
    for idx_seg, s_item in enumerate(segments):
        t_raw = s_item.get("text", "")
        t_chk = normalize_speech_text(t_raw)
        has_vocative = any(is_direct_vocative_to(n, t_chk) for n in extracted_names) or bool(_RE_HONORIFIC_VOCATIVE.search(t_chk))
        if has_vocative or (t_chk.strip().endswith("?") and idx_seg > 0):
            first_interactive_turn = idx_seg
            break

    # Segments before first interactive turn with presentation/intro text belong to Narrator
    for i in range(min(first_interactive_turn, n_total)):
        t_low = normalize_speech_text(segments[i].get("text", "")).lower()
        if is_narrator_text(t_low) or (i > 0 and (i - 1 in narrator_indices) and is_sentence_continuation(segments[i - 1], segments[i])):
            narrator_indices.add(i)

    # Trailing outro check
    if n_total > 2:
        last_seg_txt = normalize_speech_text(segments[-1].get("text", "")).lower()
        if "thank" in last_seg_txt and ("watching" in last_seg_txt or "listening" in last_seg_txt or "learning" in last_seg_txt):
            narrator_indices.add(n_total - 1)

    has_narrator = len(narrator_indices) > 0

    # Dynamic naming: use real names and honorifics discovered in dialogue
    primary_name = extracted_names[0] if extracted_names else None
    second_name = extracted_names[1] if len(extracted_names) > 1 else None
    has_teacher_honorific = "Teacher" in honorifics

    if primary_name and has_teacher_honorific:
        s0_name = primary_name
        s1_name = "Teacher"
    elif primary_name and second_name:
        s0_name = primary_name
        s1_name = second_name
    elif primary_name:
        s0_name = primary_name
        s1_name = "Speaker 2"
    elif has_teacher_honorific:
        s0_name = "Speaker 1"
        s1_name = "Teacher"
    else:
        s0_name = "Speaker 1"
        s1_name = "Speaker 2"

    speakers = []
    speaker_0_label = "SPEAKER_00"
    speaker_1_label = "SPEAKER_01" if target_speakers >= 2 else "SPEAKER_00"
    narrator_label = "SPEAKER_02" if target_speakers >= 2 else "SPEAKER_00"

    speakers.append({
        "speaker_label": speaker_0_label,
        "display_name": s0_name,
        "role": s0_name,
        "color_hex": ROLE_PALETTES["primary"],
    })

    if target_speakers >= 2:
        speakers.append({
            "speaker_label": speaker_1_label,
            "display_name": s1_name,
            "role": s1_name,
            "color_hex": ROLE_PALETTES["instructor"] if s1_name == "Teacher" else ROLE_PALETTES["secondary"],
        })

    if has_narrator:
        speakers.append({
            "speaker_label": narrator_label,
            "display_name": "Narrator",
            "role": "Narrator",
            "color_hex": ROLE_PALETTES["narrator"],
        })

    # Segment attribution
    assignments: Dict[int, str] = {}
    addressees: Dict[int, str] = {}
    intents: Dict[int, str] = {}
    current_speaker = speaker_0_label

    for i, seg in enumerate(segments):
        # A. Real-time physical signal: Sentence continuation bonding
        if i > 0 and is_sentence_continuation(segments[i - 1], seg):
            assignments[i] = assignments[i - 1]
            addressees[i] = addressees[i - 1]
            intents[i] = intents[i - 1]
            if assignments[i] in [speaker_0_label, speaker_1_label]:
                current_speaker = assignments[i]
            continue

        # B. Narrative intro/outro
        if i in narrator_indices and has_narrator:
            assignments[i] = narrator_label
            addressees[i] = "Audience"
            intents[i] = "narration"
            continue

        text = normalize_speech_text(seg.get("text", ""))
        t_lower = text.lower()

        # C. Direct vocative address by name or honorific
        if s0_name != "Speaker 1" and is_direct_vocative_to(s0_name, text):
            assignments[i] = speaker_1_label
            addressees[i] = s0_name
            intents[i] = "inquiry" if t_lower.endswith("?") else "explanation"
            current_speaker = speaker_1_label
            continue

        if s1_name != "Speaker 2" and (is_direct_vocative_to(s1_name, text) or _RE_HONORIFIC_VOCATIVE.search(t_lower)):
            assignments[i] = speaker_0_label
            addressees[i] = s1_name
            if _RE_CONFIRMATION_START.search(t_lower):
                intents[i] = "confirmation"
            elif t_lower.endswith("?"):
                intents[i] = "inquiry"
            else:
                intents[i] = "statement"
            current_speaker = speaker_0_label
            continue

        # D. Confirmation response
        if _RE_CONFIRMATION_START.search(t_lower) and i > 0:
            assignments[i] = speaker_0_label
            addressees[i] = s1_name
            intents[i] = "confirmation"
            current_speaker = speaker_0_label
            continue

        # E. Questions vs Answers based on punctuation and discourse
        if t_lower.endswith("?"):
            assignments[i] = speaker_0_label
            addressees[i] = s1_name if i >= first_interactive_turn else "Audience"
            intents[i] = "inquiry"
            current_speaker = speaker_0_label
        elif i > 0 and intents.get(i - 1) == "inquiry":
            assignments[i] = speaker_1_label
            addressees[i] = s0_name
            intents[i] = "explanation"
            current_speaker = speaker_1_label
        else:
            a_lbl = seg.get("speaker_label")
            chosen = speaker_0_label if a_lbl == "SPEAKER_00" else (speaker_1_label if a_lbl == "SPEAKER_01" else current_speaker)
            assignments[i] = chosen
            addressees[i] = s1_name if chosen == speaker_0_label else s0_name
            intents[i] = "statement"
            current_speaker = chosen

    # Prune unused speaker labels
    used_labels = set(assignments.values())
    speakers = [s for s in speakers if s["speaker_label"] in used_labels]

    summary_str = " • ".join(
        f"{s['display_name']} ({s['role']})" if s.get('role') and s['role'].lower() != s['display_name'].lower() else s['display_name']
        for s in speakers
    )

    return {
        "success": True,
        "tier": "tier1_local",
        "speakers": speakers,
        "summary": summary_str,
        "segment_assignments": assignments,
        "addressee_assignments": addressees,
        "intent_assignments": intents,
        "student_name": s0_name,
        "teacher_name": s1_name,
        "primary_name": s0_name,
        "secondary_name": s1_name,
        "narrator_count": len(narrator_indices),
        "total_segments": n_total,
    }


def smart_identify_and_save_job(
    db_path: Optional[str] = None,
    job_id: str = "",
    tier: str = "auto",
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes universal smart speaker identification on a job, persists
    the updated speaker names, addressed_to, and turn_intent directly to the database,
    and returns results. Reuses centralized get_db() session manager.
    """
    from db.database import get_db

    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Fetch transcript segments
        cursor.execute(
            """
            SELECT id, segment_index, speaker_label, start_time, end_time, text 
            FROM segments 
            WHERE job_id = ? 
            ORDER BY segment_index ASC
            """,
            (job_id,)
        )
        rows = cursor.fetchall()
        if not rows:
            return {"error": "No segments found for job"}

        segments = [dict(r) for r in rows]

        # 2. Resolve active API keys if not explicitly passed
        if not gemini_api_key:
            try:
                from services.settings_service import get_raw_gemini_key
                gemini_api_key = get_raw_gemini_key()
            except Exception:
                pass
        if not openrouter_api_key:
            try:
                from services.settings_service import get_raw_openrouter_key
                openrouter_api_key = get_raw_openrouter_key()
            except Exception:
                pass

        # 3. Acoustic Voice Clustering (if media audio file is accessible)
        try:
            from engine.diarizer import tag_segments_with_acoustic_clusters
            from db.database import DATA_DIR
            job_audio_path = DATA_DIR / "media" / job_id / "audio_16k.wav"
            if not job_audio_path.exists():
                cursor.execute("SELECT filepath FROM jobs WHERE id = ?", (job_id,))
                row_job = cursor.fetchone()
                if row_job and row_job["filepath"] and Path(row_job["filepath"]).exists():
                    job_audio_path = Path(row_job["filepath"])
            if job_audio_path.exists():
                tag_segments_with_acoustic_clusters(str(job_audio_path), segments, num_speakers=3)
        except Exception:
            pass

        # 4. Run universal identification
        res = identify_speakers_for_segments(
            segments,
            num_speakers=3,
            tier=tier,
            gemini_api_key=gemini_api_key,
            openrouter_api_key=openrouter_api_key,
        )
        speakers = res["speakers"]
        assignments = res["segment_assignments"]
        addressees = res.get("addressee_assignments", {})
        intents = res.get("intent_assignments", {})

        # 5. Persist updated speakers in batch
        cursor.execute("DELETE FROM speakers WHERE job_id = ?", (job_id,))
        spk_data = [
            (
                f"spk_{job_id}_{spk['speaker_label']}",
                job_id,
                spk["speaker_label"],
                spk["display_name"],
                spk["color_hex"]
            )
            for spk in speakers
        ]
        if spk_data:
            cursor.executemany(
                """
                INSERT INTO speakers (id, job_id, speaker_label, display_name, color_hex)
                VALUES (?, ?, ?, ?, ?)
                """,
                spk_data
            )

        # 6. Batch update segment assignments, addressees, intents, and word records
        seg_updates = []
        word_updates = []
        for idx, seg in enumerate(segments):
            assigned_label = assignments.get(idx, "SPEAKER_00")
            addr = addressees.get(idx)
            intent = intents.get(idx)
            seg_updates.append((assigned_label, addr, intent, seg["id"]))
            word_updates.append((assigned_label, seg["id"]))

        cursor.executemany(
            """
            UPDATE segments 
            SET speaker_label = ?, addressed_to = ?, turn_intent = ? 
            WHERE id = ?
            """,
            seg_updates
        )
        cursor.executemany(
            """
            UPDATE words 
            SET speaker_label = ? 
            WHERE segment_id = ?
            """,
            word_updates
        )

        # 7. Update parent transcript timestamp
        cursor.execute(
            "UPDATE transcripts SET updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (job_id,)
        )

    return {
        "success": True,
        "job_id": job_id,
        "tier": res.get("tier", "tier1_local"),
        "speakers": speakers,
        "summary": res.get("summary"),
        "student_name": res.get("student_name"),
        "teacher_name": res.get("teacher_name"),
        "primary_name": res.get("primary_name"),
        "secondary_name": res.get("secondary_name"),
        "narrator_segments": res.get("narrator_count", 0),
        "total_segments": len(segments),
        "addressee_assignments": addressees,
        "intent_assignments": intents,
    }
