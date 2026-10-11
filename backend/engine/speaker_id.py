"""
Intelligent Speaker & Role Identification Engine for Universal Video Transcription.
Domain-agnostic identification of Narrator + Dialogue Participants across all video genres
(educational, tutorials, podcasts, interviews, lectures, tech talks, documentaries, meetings).
Extracts real participant names and honorifics dynamically from dialogue without hardcoded mocks.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
import sqlite3
from pathlib import Path

# Vibrant, accessible color palette for identified roles and speakers
ROLE_PALETTES = {
    "narrator": "#d97706",    # Warm Amber
    "instructor": "#059669",  # Emerald Green
    "primary": "#2563eb",     # Royal Blue
    "secondary": "#0284c7",   # Sky Blue
    "tertiary": "#0d9488",    # Teal
    "quaternary": "#06b6d4",  # Cyan
}

# Universal English stop-words: capitalized tokens that must never be treated as names
GENERAL_EXCLUSIONS = {
    # Discourse sequence, transitions, and time
    "first", "second", "third", "finally", "next", "then", "now", "here", "there",
    "today", "yesterday", "tomorrow", "tonight", "welcome", "hello", "good",
    "however", "therefore", "moreover", "furthermore", "meanwhile", "nevertheless",
    "nonetheless", "otherwise", "likewise", "consequently", "further", "hence", "thus",
    # Common sentence-initial verbs
    "look", "listen", "see", "watch", "remember", "notice", "understand", "explain",
    "check", "guess", "know", "think", "start", "stop", "try", "make", "take",
    "show", "find", "come", "learn", "follow", "visit", "connect", "build", "create",
    "use", "using", "work", "working", "read", "write", "call", "called", "gives", "let",
    # Adverbs & qualifiers
    "carefully", "properly", "quickly", "slowly", "gently", "together", "perfectly",
    "clearly", "obviously", "honestly", "simply", "directly", "already", "certainly",
    "definitely", "absolutely", "specifically", "generally", "actually", "naturally",
    "exactly", "right", "sure", "well", "great", "excellent", "amazing", "awesome",
    # Conversational interjections & confirmations
    "yay", "wow", "yes", "yeah", "yep", "no", "nope", "okay", "ok", "please", "sorry",
    "pardon", "excuse", "thanks", "thank",
    # Conjunctions, prepositions & pronouns
    "and", "but", "or", "so", "because", "although", "since", "while", "with", "from",
    "into", "onto", "upon", "for", "about", "above", "below", "between",
    "what", "why", "how", "where", "when", "which", "who", "whom", "whose",
    "that", "this", "these", "those", "they", "them", "their", "theirs", "it", "its",
    "every", "each", "all", "some", "any", "many", "much", "more", "most",
    # Generic discourse nouns
    "video", "lesson", "session", "episode", "podcast", "chapter", "slide", "step",
    "topic", "project", "example", "question", "answer", "problem", "solution",
    "students", "everyone", "people", "guys", "folks", "team", "class", "don",
    # Common states & emotions after "I am" / "I'm"
    "excited", "happy", "glad", "ready", "curious", "thrilled", "interested", "afraid", "able"
}

# Recognized professional honorifics and titles
HONORIFIC_ROLES = [
    "teacher", "sir", "ma'am", "madam", "doctor", "dr", "professor", "prof",
    "instructor", "coach", "judge", "officer", "captain", "host"
]

# Universal narrative intro & channel greeting patterns (applies to any genre)
NARRATIVE_INTRO_GREETING_PATTERNS = [
    r"\bwelcome to\b",
    r"\bwelcome back\b",
    r"\bhello students\b",
    r"\bhello everyone\b",
    r"\bin this (?:video|session|presentation|meeting|talk|episode|podcast|lecture|discussion|tutorial)\b",
    r"\btoday we (?:are going to|will|shall) (?:learn|discuss|cover|explore|examine|see|look at)\b",
    r"\bin today'?s (?:lesson|session|episode|meeting|presentation|video)\b",
    r"\blet us (?:begin|get started|start)\b",
    r"\blet'?s (?:begin|get started|start)\b",
    r"\bgood (?:morning|afternoon|evening) (?:students|everyone|all|viewers)\b",
]

# Universal narrative third-person framing and scene-setting
NARRATIVE_SCENE_SETTING_PATTERNS = [
    r"\bnow let us (?:go ahead and )?(?:meet|see|follow|visit|look at)\b",
    r"\blet us (?:go ahead and )?(?:meet|see|follow|visit|look at)\b",
    r"\bmeet\s+[A-Z][a-z]+\b",
    r"^(?:now\s+)?(?:he|she|they)\s+(?:finds?|sees?|wonders?|looks?|asks?|wants?|discovers?|notices?|walks?|comes?|goes?|has?|tries?)\b",
    r"^(?:and so|and then|so|and)\s+(?:he|she|they)\s+(?:asks?|finds?|wonders?|looks?|wants?|needs?)\b",
]

# Universal video outro and viewer signoff patterns
NARRATIVE_OUTRO_PATTERNS = [
    r"\bthanks? for watching\b",
    r"\bthank you for watching\b",
    r"\bthanks? for (?:listening|tuning in|joining|attending)\b",
    r"\bthank you for (?:listening|joining|attending)\b",
    r"\bkeep (?:innovating|creating|learning|practicing|coding)\b",
    r"\bsee you (?:next time|in the next|all soon)\b",
    r"\bdon'?t forget to (?:like|subscribe|share)\b",
    r"\bthat brings us to the end\b",
    r"\bthat wraps up\b",
]

# Universal narrative synthesis / voiceover reflection patterns
NARRATIVE_SYNTHESIS_PATTERNS = [
    r"\b(?:now,? )?let us see how (?:[a-zA-Z]+ and [a-zA-Z]+|concepts?|these ideas|all of these|everything)\b",
    r"\bthis is how (?:[a-zA-Z]+ and [a-zA-Z]+|all of these|everything|these concepts|these disciplines)\b",
    r"\b(?:brings? (?:it|all|them) together|work together|putting it all together)\b",
    r"\b(?:connecting concepts|cross-disciplinary|multidisciplinary synthesis)\b",
]

# Universal conversational inquiry & questioner patterns (domain-agnostic)
INQUIRY_CUES = [
    # Respectful vocatives to an instructor, expert, or guide
    r"\b(?:ma'?am|sir|teacher|miss|madam|doctor|prof|professor)\b",
    # Syntactic interrogatives ending with questions
    r"\b(?:what is|what are|what does|why is|why are|why does|how does|how do|how can|can you|could you)\b.*?\?",
    r"\b(?:is it|is this|do you know|help me out|help me)\b.*?\?",
    r"\b(?:what is this called|what does it do|what is this|why are there so many)\b",
    # Expressions of curiosity, uncertainty, or requesting help
    r"\b(?:i don'?t know|i don'?t understand|i do not understand|i'?m not sure|i wonder|can you please help|could you please help)\b",
    r"\b(?:which (?:ones?|items?|parts?|tools?|steps?)|what (?:do we need|is needed|should i do))\b",
    r"\b(?:i want to|need (?:some|your|any) guidance|need help)\b",
]

# Universal realizations, acknowledgements, and conversational confirmations
CONFIRMATION_CUES = [
    r"^(?:yes ma'?am|yes sir|thank you ma'?am|thank you sir|thank you teacher)\b",
    r"^(?:yes|yeah|yep|understood|got it|i see|that makes sense|right|okay|ok|sure)\b",
    r"^(?:yay!?|wow!?|awesome!?|great!?|it worked!?|it works!?)\b",
    r"\b(?:now i have understood|now i understand|that makes sense|clear now)\b",
    r"\b(?:let us try|let'?s try|actually working|it works|it worked)\b",
]

# Universal explanation, instructor, and guidance patterns (domain-agnostic)
EXPLANATION_CUES = [
    # Definitions and term explanations
    r"\b(?:this is called an?|this is an?|this means|the definition of|means|stands for|is defined as|refers to)\b",
    # Pedagogical walkthrough guidance
    r"\b(?:first let us understand|let us understand|now let us understand)\b",
    r"\b(?:for example|for instance|in other words|the reason is|because)\b",
    r"\b(?:now let us see|now let'?s see|let us see and understand|let'?s look at|let us look at)\b",
    r"\b(?:connects? (?:to|concepts|from)|how this (?:topic|project|concept) connects)\b",
    r"\b(?:don'?t worry|i'?ll explain|what happened)\b",
    r"\b(?:it helps (?:us|to)|it is used (?:for|to)|consists of)\b",
    # Universal procedural & demonstration guidance
    r"\b(?:in step\s+\d+|step\s+\d+|step\s+(?:one|two|three|four|five|six|seven|eight|nine|ten))\b",
    r"\b(?:first,? let us|next,? we|then we|now we can|now in step)\b",
    r"\b(?:come on,? let me show you|let me show you|let me walk you through|let us build it together)\b",
    r"\b(?:we have (?:finished|completed|prepared)|now (?:our|the) [a-zA-Z]+ is ready)\b",
    r"\b(?:the next step is to|now let us test)\b",
    r"\b(?:sure\s+[A-Z][a-z]+|i completely understand\s+[A-Z][a-z]+)\b",
]


# Pre-compiled regex patterns for maximum execution speed
_NORM_APOSTROPHES = re.compile(r"[’‘`]")
_NORM_QUOTES = re.compile(r'[“”]')
_NORM_CONTRACTIONS = re.compile(r"\b([a-zA-Z]+)\s*'\s*([a-zA-Z]+)\b")
_NORM_HYPHEN_CODES = re.compile(r"\b([A-Za-z]{2,6})\s*[-–]\s*(\d{2,5})\b")
_NORM_SPACED_CODES = re.compile(r"\b([A-Za-z]{2,6})\s+(\d{3,5})\b")
_NORM_SPACES = re.compile(r"\s+")

_COMPILED_NARRATIVE_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in (
        NARRATIVE_INTRO_GREETING_PATTERNS + NARRATIVE_SCENE_SETTING_PATTERNS +
        NARRATIVE_OUTRO_PATTERNS + NARRATIVE_SYNTHESIS_PATTERNS
    )
]
_COMPILED_INTRO_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NARRATIVE_INTRO_GREETING_PATTERNS]
_COMPILED_SCENE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NARRATIVE_SCENE_SETTING_PATTERNS]
_COMPILED_OUTRO_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NARRATIVE_OUTRO_PATTERNS]
_COMPILED_SYNTHESIS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in NARRATIVE_SYNTHESIS_PATTERNS]
_COMPILED_INQUIRY_CUES = [re.compile(p, re.IGNORECASE) for p in INQUIRY_CUES]
_COMPILED_CONFIRMATION_CUES = [re.compile(p, re.IGNORECASE) for p in CONFIRMATION_CUES]
_COMPILED_EXPLANATION_CUES = [re.compile(p, re.IGNORECASE) for p in EXPLANATION_CUES]

# High-performance compiled union regexes for O(1) single-pass DFA matching
_RE_NARRATIVE = re.compile("|".join(f"(?:{p})" for p in (
    NARRATIVE_INTRO_GREETING_PATTERNS + NARRATIVE_SCENE_SETTING_PATTERNS +
    NARRATIVE_OUTRO_PATTERNS + NARRATIVE_SYNTHESIS_PATTERNS
)), re.IGNORECASE)
_RE_INTRO = re.compile("|".join(f"(?:{p})" for p in NARRATIVE_INTRO_GREETING_PATTERNS), re.IGNORECASE)
_RE_SCENE = re.compile("|".join(f"(?:{p})" for p in NARRATIVE_SCENE_SETTING_PATTERNS), re.IGNORECASE)
_RE_OUTRO = re.compile("|".join(f"(?:{p})" for p in NARRATIVE_OUTRO_PATTERNS), re.IGNORECASE)
_RE_SYNTHESIS = re.compile("|".join(f"(?:{p})" for p in NARRATIVE_SYNTHESIS_PATTERNS), re.IGNORECASE)
_RE_INQUIRY = re.compile("|".join(f"(?:{p})" for p in INQUIRY_CUES), re.IGNORECASE)
_RE_CONFIRMATION = re.compile("|".join(f"(?:{p})" for p in CONFIRMATION_CUES), re.IGNORECASE)
_RE_EXPLANATION = re.compile("|".join(f"(?:{p})" for p in EXPLANATION_CUES), re.IGNORECASE)
_RE_HONORIFIC_ROLES = re.compile(rf"\b(?:{'|'.join(re.escape(h) for h in HONORIFIC_ROLES)})\b", re.IGNORECASE)
_RE_ROLE_MODIFIER = re.compile(r"\b([A-Za-z]{3,15})\s+(teacher|instructor|professor|prof|coach|doctor|dr|guide|trainer|host)\b", re.IGNORECASE)
_RE_TITLE_NAME = re.compile(r"\b(?i:dr|doctor|prof|professor|mr|mrs|ms)\.?\s+([A-Z][a-z]+)\b")
_RE_INTRO_NAME = re.compile(r"\b(?i:meet|welcome|joined by|this is)\s+([A-Z][a-z]+)\b")
_RE_SELF_INTRO = re.compile(r"\b(?i:i am|i'm|my name is)\s+([A-Z][a-z]+)\b")
_RE_START_VOCATIVE = re.compile(r"^([A-Z][a-z]+),\s+(?i:we|you|i|let|look|listen|what|how|why|can|could|please|now)\b")
_RE_END_VOCATIVE = re.compile(r",\s*([A-Z][a-z]+)[?.!]")
_RE_PHRASAL_VOCATIVE = re.compile(r"\b(?i:sure|understand|completely understand|worry|listen|hello|hi|hey|come on|tell me|thanks|thank you)\b\s*,?\s*([A-Z][a-z]+)\b")
_RE_IN_SCENE_DIALOGUE = re.compile(r"^(?:i\b|my\b|we\b|excuse me|hello\b|hi\b|hey\b|oh\b|wait\b|look\b|yay\b|wow\b)", re.IGNORECASE)
_RE_TEACHER_MAAM = re.compile(r"\b(?:ma'?am|sir|teacher)\b", re.IGNORECASE)
_RE_TEACHER_ROLE_ALL = re.compile(r"\b(?:ma'?am|sir|teacher|miss|madam|doctor|prof)\b", re.IGNORECASE)
_RE_TAG_QUESTION = re.compile(r"(?:right|okay|correct)\?$", re.IGNORECASE)



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
    """Checks if a segment text contains narrative opening, framing, outro, or synthesis markers."""
    t_lower = normalize_speech_text(text).lower()
    return bool(_RE_NARRATIVE.search(t_lower))



import functools


@functools.lru_cache(maxsize=128)
def _get_compiled_vocative_rules(name: str):
    """Pre-compiles regex patterns for a character name to eliminate re-compilation overhead."""
    n_esc = re.escape(name)
    n_low = re.escape(name.lower())
    exclude_framing = re.compile(rf"\b(?:meet|about|with|introducing|and so|now let us meet|call)\s+{n_low}\b", re.IGNORECASE)
    exclude_decl = re.compile(rf"\b{n_low}\s+(?:is|was|has|had|does|did|finds|goes|went|said|says|wants|wished|asked)\b", re.IGNORECASE)
    pos_start = re.compile(rf"^{n_esc},\s+(?:we|you|i|let|look|listen|what|how|why|can|could|please|now)\b", re.IGNORECASE)
    pos_end = re.compile(rf",\s*{n_esc}[?.!]$|\b{n_esc}\?$|\b(?:sure|understand)\s+{n_esc}[?.!,]", re.IGNORECASE)
    pos_imperative = re.compile(rf"\b(?:sure|understand|completely understand|worry|listen|hello|hi|hey|tell me|thanks|thank you|welcome|come on|see)\s*,?\s*{n_esc}\b", re.IGNORECASE)
    pos_parenthetical = re.compile(rf",\s*{n_esc},\s*", re.IGNORECASE)
    return exclude_framing, exclude_decl, pos_start, pos_end, pos_imperative, pos_parenthetical


def is_direct_vocative_to(name: str, text: str) -> bool:
    """
    Determines whether a character name is being directly addressed (vocative case)
    versus merely mentioned in third-person (e.g. 'meet David' or 'David went').
    Uses pre-compiled, cached rules for high-throughput evaluation.
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
    Extracts real participant names and honorifics dynamically from transcript segments.
    Uses generic linguistic patterns (introductions, vocative addresses, self-introductions).
    """
    mentions: Dict[str, List[int]] = {}
    honorifics: List[str] = []

    def _add(raw_name: str, idx: int):
        clean = raw_name.strip().capitalize()
        if clean.lower() not in GENERAL_EXCLUSIONS and len(clean) >= 3:
            mentions.setdefault(clean, []).append(idx)

    for seg in segments:
        text = normalize_speech_text(seg.get("text", ""))
        idx = seg.get("segment_index", seg.get("index", 0))

        # Dynamic role modifier + title extraction: e.g. "robotics teacher", "science instructor", "fitness coach"
        m_role = _RE_ROLE_MODIFIER.search(text)
        if m_role:
            modifier = m_role.group(1).capitalize()
            base_title = m_role.group(2).capitalize()
            if modifier.lower() not in GENERAL_EXCLUSIONS:
                honorifics.append(f"{modifier} {base_title}")

        for m_h in _RE_HONORIFIC_ROLES.finditer(text):
            honorifics.append(m_h.group(0).capitalize())

        # 1. Title + Name: "Dr. Smith", "Professor Charles", "Mr. Anderson"
        for m in _RE_TITLE_NAME.finditer(text):
            _add(m.group(1), idx)

        # 2. Third-person introduction: "meet David", "welcome Sarah", "joined by Alex"
        for m in _RE_INTRO_NAME.finditer(text):
            _add(m.group(1), idx)

        # 3. Direct self-introduction: "I am Alex", "My name is Priya"
        for m in _RE_SELF_INTRO.finditer(text):
            _add(m.group(1), idx)

        # 4. Direct vocative at sentence start: "Sarah, this is...", "David, what is..."
        for m in _RE_START_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

        # 5. Direct vocative after comma or ending punctuation: "What happened, Amit?", "Tell us, Sarah."
        for m in _RE_END_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

        # 6. Conversational phrasal addresses: "Sure David", "understand Sarah", "Listen Alex", "Thanks Priya"
        for m in _RE_PHRASAL_VOCATIVE.finditer(text):
            _add(m.group(1), idx)

    # Sort extracted names by frequency of appearance
    honorific_set = {h.lower() for h in honorifics}
    sorted_names = [
        name for name, _ in sorted(mentions.items(), key=lambda kv: len(kv[1]), reverse=True)
        if name.lower() not in honorific_set
    ]

    return {
        "names": sorted_names,
        "honorifics": list(set(honorifics)),
    }


def identify_speakers_for_segments(
    segments: List[Dict[str, Any]],
    num_speakers: Optional[int] = 3,
    tier: str = "auto",
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Universal, domain-agnostic speaker & role identification algorithm.
    Accurately identifies Narrator, primary participants, and instructors across any video type,
    assigning real names extracted dynamically from dialogue.
    Supports Multi-Tier architecture:
    - Tier 2: AI Semantic Reasoner (Gemini with automatic fallback to OpenRouter).
    - Tier 1: Local Pragmatic State Graph (offline, instant, zero-cost).
    """
    target_speakers = int(num_speakers) if num_speakers is not None else 3

    if not segments:
        return {
            "tier": "tier1_local_graph",
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
    # OPTIONAL TIER 2: MULTI-PROVIDER AI SEMANTIC REASONER
    # (Gemini API with seamless fallback to OpenRouter)
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
                ai_res["student_name"] = s0
                ai_res["teacher_name"] = s1
                ai_res["primary_name"] = s0
                ai_res["secondary_name"] = s1
                ai_res["total_segments"] = len(segments)
                ai_res["narrator_count"] = sum(
                    1 for v in ai_res.get("addressee_assignments", {}).values() if v == "Audience"
                )
                return ai_res
        except Exception:
            pass  # Seamless fallback to Tier 1

    n_total = len(segments)

    # -------------------------------------------------------------
    # 1. EXTRACT PARTICIPANT NAMES & ROLES FROM DIALOGUE
    # -------------------------------------------------------------
    extracted_data = extract_vocatives_and_mentions(segments)
    extracted_names = extracted_data["names"]
    honorifics = extracted_data["honorifics"]

    # -------------------------------------------------------------
    # 2. IDENTIFY NARRATOR SEGMENTS (INTRO & OUTRO BLOCKS)
    # -------------------------------------------------------------
    narrator_indices = set()

    # Check intro greeting in the first 4 segments
    intro_found = False
    for i in range(min(4, n_total)):
        t_low = normalize_speech_text(segments[i]["text"]).lower()
        if _RE_INTRO.search(t_low):
            intro_found = True
            break

    if intro_found:
        # Narrative block runs contiguously until first in-scene first-person or conversational address
        for i in range(min(10, n_total)):
            t_low = normalize_speech_text(segments[i]["text"]).lower()
            is_intro = bool(_RE_INTRO.search(t_low))
            is_scene = bool(_RE_SCENE.search(t_low))

            # Universal in-scene dialogue marker: direct first-person utterance or conversational greeting
            is_in_scene = (
                _RE_IN_SCENE_DIALOGUE.search(t_low)
                or _RE_TEACHER_MAAM.search(t_low)
                or t_low.endswith("?")
            ) and not (is_intro or is_scene)

            if is_in_scene and i > 0:
                break
            if is_intro or is_scene:
                narrator_indices.add(i)
            elif narrator_indices and not is_in_scene and i <= 3:
                narrator_indices.add(i)
            else:
                break

    # Check outro narrator in the trailing segments
    outro_start = max(min(4, n_total), n_total - 6)
    for i in range(outro_start, n_total):
        t_low = normalize_speech_text(segments[i]["text"]).lower()
        if _RE_OUTRO.search(t_low):
            for k in range(i, n_total):
                narrator_indices.add(k)
            break

    # Check middle narrative voiceover / synthesis blocks
    for i in range(n_total):
        t_low = normalize_speech_text(segments[i]["text"]).lower()
        if _RE_SYNTHESIS.search(t_low):
            narrator_indices.add(i)

    # Fill continuous narrative synthesis blocks if detected
    synth_indices = [i for i in narrator_indices if i >= 4 and i < n_total - 2]
    if synth_indices:
        s_min, s_max = min(synth_indices), max(synth_indices)
        for i in range(s_min, s_max + 1):
            t_low = normalize_speech_text(segments[i]["text"]).lower()
            if not _RE_TEACHER_MAAM.search(t_low):
                narrator_indices.add(i)

    has_narrator = len(narrator_indices) > 0
    actual_speaker_count = max(1, target_speakers)

    # -------------------------------------------------------------
    # 3. CONSTRUCT SPEAKERS DYNAMICALLY BASED ON VIDEO DISCOURSE
    # -------------------------------------------------------------
    primary_name = extracted_names[0] if extracted_names else None
    second_name = extracted_names[1] if len(extracted_names) > 1 else None

    # Check whether the video exhibits educational/instructor dynamics
    has_teacher_role = any(
        "teacher" in h.lower() or h.lower() in ["ma'am", "sir", "instructor", "professor", "prof"]
        for h in honorifics
    )

    if has_teacher_role:
        speaker_0_name = primary_name or "Student"
        speaker_0_role = "Student"
        specific_teacher = next((h for h in honorifics if "Teacher" in h and h != "Teacher"), None)
        speaker_1_name = specific_teacher or "Teacher"
        speaker_1_role = specific_teacher or "Teacher"
    elif len(extracted_names) >= 2:
        speaker_0_name = extracted_names[0]
        speaker_0_role = extracted_names[0]
        speaker_1_name = extracted_names[1]
        speaker_1_role = extracted_names[1]
    elif len(extracted_names) == 1:
        speaker_0_name = extracted_names[0]
        speaker_0_role = extracted_names[0]
        speaker_1_name = "Speaker 2"
        speaker_1_role = "Speaker 2"
    else:
        speaker_0_name = "Speaker 1"
        speaker_0_role = "Speaker 1"
        speaker_1_name = "Speaker 2"
        speaker_1_role = "Speaker 2"

    speakers = []
    palette_list = [
        ROLE_PALETTES.get("primary", "#2563eb"),
        ROLE_PALETTES.get("instructor" if has_teacher_role else "secondary", "#059669"),
        ROLE_PALETTES.get("narrator", "#d97706"),
        ROLE_PALETTES.get("secondary", "#0284c7"),
        ROLE_PALETTES.get("tertiary", "#0d9488"),
        ROLE_PALETTES.get("quaternary", "#06b6d4"),
    ]

    # Primary dialogue participant
    speakers.append({
        "speaker_label": "SPEAKER_00",
        "display_name": speaker_0_name,
        "role": speaker_0_role,
        "color_hex": palette_list[0],
    })

    # Secondary dialogue participant (if multi-speaker)
    if actual_speaker_count >= 2:
        speakers.append({
            "speaker_label": "SPEAKER_01",
            "display_name": speaker_1_name,
            "role": speaker_1_role,
            "color_hex": palette_list[1],
        })

    # Narrator (always registered if detected, avoiding missing speaker labels)
    narrator_label = "SPEAKER_02" if actual_speaker_count >= 2 else "SPEAKER_00"
    if has_narrator:
        if not any(s["speaker_label"] == narrator_label for s in speakers):
            speakers.append({
                "speaker_label": narrator_label,
                "display_name": "Narrator",
                "role": "Narrator",
                "color_hex": ROLE_PALETTES.get("narrator", "#d97706"),
            })

    # Additional speaker slots
    start_extra = 3 if has_narrator else 2
    for s_idx in range(start_extra, actual_speaker_count):
        lbl = f"SPEAKER_{s_idx:02d}"
        if not any(s["speaker_label"] == lbl for s in speakers):
            name = f"Speaker {s_idx + 1}"
            speakers.append({
                "speaker_label": lbl,
                "display_name": name,
                "role": name,
                "color_hex": palette_list[s_idx % len(palette_list)],
            })

    speaker_0_label = "SPEAKER_00"
    speaker_1_label = "SPEAKER_01" if actual_speaker_count >= 2 else "SPEAKER_00"

    # Acoustic diarization cluster correlation (if segments contain pre-existing acoustic labels)
    acoustic_labels = [seg.get("speaker_label") for seg in segments if seg.get("speaker_label")]
    unique_acoustic = list(dict.fromkeys(acoustic_labels))
    acoustic_map = {}
    if len(unique_acoustic) >= 2:
        cluster_scores = {lbl: {"inquiry": 0, "explanation": 0} for lbl in unique_acoustic}
        for seg in segments:
            lbl = seg.get("speaker_label")
            if not lbl or lbl not in cluster_scores:
                continue
            txt = normalize_speech_text(seg.get("text", "")).lower()
            if _RE_CONFIRMATION.search(txt) or _RE_INQUIRY.search(txt):
                cluster_scores[lbl]["inquiry"] += 1
            if _RE_EXPLANATION.search(txt):
                cluster_scores[lbl]["explanation"] += 1
            if primary_name and is_direct_vocative_to(primary_name, seg.get("text", "")):
                cluster_scores[lbl]["explanation"] += 2
        sorted_clusters = sorted(
            unique_acoustic,
            key=lambda l: cluster_scores[l]["inquiry"] - cluster_scores[l]["explanation"],
            reverse=True
        )
        if len(sorted_clusters) >= 2:
            acoustic_map[sorted_clusters[0]] = speaker_0_label
            acoustic_map[sorted_clusters[1]] = speaker_1_label

    # -------------------------------------------------------------
    # 4. ATTRIBUTE SEGMENTS CONVERSATIONALLY
    # -------------------------------------------------------------
    assignments: Dict[int, str] = {}
    addressees: Dict[int, str] = {}
    intents: Dict[int, str] = {}
    current_dialogue_speaker = speaker_0_label

    # Locate index where direct dialogue interaction begins
    first_teacher_interaction = n_total
    for idx_seg, s_item in enumerate(segments):
        t_chk = normalize_speech_text(s_item.get("text", "")).lower()
        if _RE_TEACHER_MAAM.search(t_chk) or (primary_name and is_direct_vocative_to(primary_name, s_item.get("text", ""))):
            first_teacher_interaction = idx_seg
            break

    for i, seg in enumerate(segments):
        # A. Narrator intro, outro, & synthesis voiceover
        if i in narrator_indices and has_narrator:
            assignments[i] = narrator_label
            addressees[i] = "Audience"
            intents[i] = "narration"
            continue

        text = normalize_speech_text(seg.get("text", ""))
        t_lower = text.lower()

        # B. Direct vocative address by name: Person addressing primary participant
        if primary_name and is_direct_vocative_to(primary_name, text):
            assignments[i] = speaker_1_label
            addressees[i] = primary_name
            intents[i] = "inquiry" if t_lower.endswith("?") else "explanation"
            current_dialogue_speaker = speaker_1_label
            continue

        if second_name and is_direct_vocative_to(second_name, text):
            assignments[i] = speaker_0_label
            addressees[i] = second_name
            intents[i] = "inquiry" if t_lower.endswith("?") else "statement"
            current_dialogue_speaker = speaker_0_label
            continue

        # C. Direct address to instructor / teacher / host
        if has_teacher_role and _RE_TEACHER_ROLE_ALL.search(t_lower):
            assignments[i] = speaker_0_label
            addressees[i] = speaker_1_name
            if _RE_CONFIRMATION.search(t_lower):
                intents[i] = "confirmation"
            elif t_lower.endswith("?") or _RE_INQUIRY.search(t_lower):
                intents[i] = "inquiry"
            else:
                intents[i] = "statement"
            current_dialogue_speaker = speaker_0_label
            continue

        # D. Universal confirmation / realization cues
        is_confirmation = bool(_RE_CONFIRMATION.search(t_lower))
        if is_confirmation:
            assignments[i] = speaker_0_label
            addressees[i] = speaker_1_name
            intents[i] = "confirmation"
            current_dialogue_speaker = speaker_0_label
            continue

        # E. Match universal inquiry vs explanation cues
        is_tag_question = bool(_RE_TAG_QUESTION.search(t_lower))
        is_inquiry = bool(_RE_INQUIRY.search(t_lower)) or (t_lower.endswith("?") and not is_tag_question)
        is_explanation = bool(_RE_EXPLANATION.search(t_lower))

        if is_inquiry and not is_explanation:
            assignments[i] = speaker_0_label
            addressees[i] = speaker_1_name if i >= first_teacher_interaction else "Audience"
            intents[i] = "inquiry"
            current_dialogue_speaker = speaker_0_label
        elif is_explanation and not is_inquiry:
            assignments[i] = speaker_1_label
            addressees[i] = speaker_0_name
            intents[i] = "explanation"
            current_dialogue_speaker = speaker_1_label
        elif is_inquiry and is_explanation:
            if t_lower.endswith("?"):
                assignments[i] = speaker_0_label
                addressees[i] = speaker_1_name if i >= first_teacher_interaction else "Audience"
                intents[i] = "inquiry"
                current_dialogue_speaker = speaker_0_label
            else:
                assignments[i] = speaker_1_label
                addressees[i] = speaker_0_name
                intents[i] = "explanation"
                current_dialogue_speaker = speaker_1_label
        else:
            # Fall back to acoustic mapping if available, else current dialogue speaker
            a_lbl = seg.get("speaker_label")
            mapped_spk = acoustic_map.get(a_lbl) if a_lbl else None
            chosen_spk = mapped_spk or current_dialogue_speaker
            assignments[i] = chosen_spk
            if chosen_spk == speaker_0_label:
                addressees[i] = speaker_1_name if i >= first_teacher_interaction else "Audience"
            elif chosen_spk == speaker_1_label:
                addressees[i] = speaker_0_name
            else:
                addressees[i] = "Audience"
            intents[i] = "statement"
            current_dialogue_speaker = chosen_spk

    # -------------------------------------------------------------
    # 5. PRUNE UNUSED SPEAKERS
    # -------------------------------------------------------------
    used_labels = set(assignments.values())
    if used_labels:
        speakers = [s for s in speakers if s["speaker_label"] in used_labels]

    return {
        "success": True,
        "tier": "tier1_state_graph",
        "speakers": speakers,
        "segment_assignments": assignments,
        "addressee_assignments": addressees,
        "intent_assignments": intents,
        "student_name": speaker_0_name,
        "teacher_name": speaker_1_name,
        "primary_name": speaker_0_name,
        "secondary_name": speaker_1_name,
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

        # 2. Run universal identification
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

        # 3. Persist updated speakers in batch
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

        # 4. Batch update segment assignments, addressees, intents, and word records
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

        # 5. Update parent transcript timestamp
        cursor.execute(
            "UPDATE transcripts SET updated_at = CURRENT_TIMESTAMP WHERE job_id = ?",
            (job_id,)
        )

    return {
        "success": True,
        "job_id": job_id,
        "tier": res.get("tier", "tier1_state_graph"),
        "speakers": speakers,
        "student_name": res.get("student_name"),
        "teacher_name": res.get("teacher_name"),
        "primary_name": res.get("primary_name"),
        "secondary_name": res.get("secondary_name"),
        "narrator_segments": res.get("narrator_count", 0),
        "total_segments": len(segments),
        "addressee_assignments": addressees,
        "intent_assignments": intents,
    }
