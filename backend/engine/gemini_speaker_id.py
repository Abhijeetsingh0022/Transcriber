"""
AI Semantic Reasoner for Character and Addressee Attribution.
Multi-provider AI reasoning engine supporting Gemini API with automatic fallback
to OpenRouter (and Tier 1 offline fallback).
Built on unified ai_client with zero external dependencies.
"""

import os
from typing import List, Dict, Any, Optional

from engine.ai_client import (
    get_gemini_api_key,
    get_openrouter_api_key,
    resolve_openrouter_inference_key,
    call_ai_json,
    get_ai_status,
)

# Backwards compatibility alias
_resolve_openrouter_inference_key = resolve_openrouter_inference_key

ROLE_PALETTE = ["#2563eb", "#059669", "#d97706", "#0284c7", "#0d9488", "#06b6d4", "#ea580c"]

ROLE_COLORS = {
    "narrator": "#d97706",
    "host": "#d97706",
    "instructor": "#059669",
    "teacher": "#059669",
    "primary": "#2563eb",
    "student": "#2563eb",
    "learner": "#2563eb",
    "guest": "#0284c7",
    "secondary": "#0d9488",
    "audience": "#06b6d4",
}

DISCOURSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "characters": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "role": {"type": "STRING"}
                },
                "required": ["name", "role"]
            }
        },
        "turns": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "segment_index": {"type": "INTEGER"},
                    "speaker": {"type": "STRING"},
                    "addressed_to": {"type": "STRING"},
                    "intent": {"type": "STRING"}
                },
                "required": ["segment_index", "speaker", "addressed_to", "intent"]
            }
        }
    },
    "required": ["characters", "turns"]
}


def _build_discourse_prompt(segments: List[Dict[str, Any]]) -> str:
    """Builds a compact, structured transcript prompt for AI discourse analysis across any language."""
    transcript_lines = []
    # Analyze up to 500 segments concisely formatted
    for idx, seg in enumerate(segments[:500]):
        text = seg.get("text", "").strip()
        start = seg.get("start_time", 0.0)
        end = seg.get("end_time", 0.0)
        transcript_lines.append(f"[{idx}] ({start:.1f}s - {end:.1f}s): {text}")

    return (
        "You are an expert dialogue and discourse analyst for video recordings across all languages.\n"
        "Analyze the transcript lines below and determine:\n"
        "1. All speaking characters/participants in the recording, extracting their real names and conversational roles from dialogue vocatives, honorifics, and cues.\n"
        "   - Include 'Narrator' if there is opening channel intro, presentation, or closing voiceover directed at the audience.\n"
        "   - Identify real names, vocatives, and honorific roles dynamically from dialogue cues across any language (e.g. Teacher, Student, Host, Doctor, Sir, Ma'am).\n"
        "   - Use clean, standard display names for 'characters.name' so UI badges render cleanly.\n"
        "   - Do NOT include 'Audience' or 'Viewers' as a character in 'characters' (use 'Audience' only for 'turns.addressed_to').\n"
        "2. For every segment index, determine exactly who is speaking ('speaker'), who they are addressing ('addressed_to'), and their conversational intent ('intent').\n"
        "Universal Rules:\n"
        "- CRITICAL SENTENCE CONTINUATION RULE: Speech transcribers split sentences across segment boundaries (e.g. mid-clause, after a comma, or conjunction). If segment [i] continues an unfinished sentence or clause from segment [i-1], it MUST have the EXACT SAME speaker and addressed_to as segment [i-1]. A single sentence NEVER changes speakers midway through.\n"
        "- CRITICAL NARRATOR INTRO RULE: The opening channel intro and topic announcement (e.g. 'Hello students, welcome to [Channel]. Today we will learn about [Topic] and how [Concepts] work.') belongs 100% to 'Narrator' addressed to 'Audience' with intent 'narration'. Do NOT attribute introductory explanations to 'Teacher' or in-scene characters before the interactive scene dialogue begins.\n"
        "- In-scene characters (e.g. Teacher, Student) only speak once the interactive dialogue begins in the scene (e.g. when a student asks 'Teacher, ...' or characters converse).\n"
        "- When Person A addresses Person B by name or honorific, speaker is Person A and addressed_to is Person B.\n"
        "- When someone asks a question or expresses confusion, intent is 'inquiry'.\n"
        "- When someone teaches, explains a concept, or provides guidance, intent is 'explanation'.\n"
        "- When someone acknowledges or confirms understanding ('Yes', 'Understood', 'Right'), intent is 'confirmation'.\n"
        "- Intent must be one of: 'narration', 'inquiry', 'explanation', 'confirmation', 'statement'.\n"
        "- Never hallucinate names; extract real names spoken in the dialogue or use clear descriptive roles ('Teacher', 'Student', 'Host', 'Guest', 'Speaker 1').\n"
        "- In 'turns.speaker' and 'turns.addressed_to', use the exact 'name' string defined in the 'characters' list.\n"
        "Respond ONLY with valid JSON with this exact schema:\n"
        "{\n"
        '  "characters": [{"name": "...", "role": "..."}],\n'
        '  "turns": [{"segment_index": 0, "speaker": "...", "addressed_to": "...", "intent": "..."}]\n'
        "}\n\n"
        "Transcript:\n" + "\n".join(transcript_lines)
    )


def _parse_ai_character_response(
    result: Dict[str, Any],
    segments: List[Dict[str, Any]],
    tier_label: str
) -> Dict[str, Any]:
    """Parses standardized JSON response from AI provider into engine speaker roster with syntactic bonding."""
    from engine.speaker_id import is_sentence_continuation, normalize_speech_text

    raw_char_list = result.get("characters", [])
    # Filter out listener-only entities like 'Audience' from speaking roster
    char_list = [c for c in raw_char_list if c.get("name", "").strip().lower() not in ["audience", "viewers", "listener"]]
    speakers = []
    name_to_label = {}
    for s_idx, c in enumerate(char_list):
        lbl = f"SPEAKER_{s_idx:02d}"
        c_name = c.get("name", f"Speaker {s_idx + 1}").strip()
        c_role = c.get("role", c_name).strip()
        name_to_label[c_name.lower()] = lbl
        name_to_label[c_role.lower()] = lbl

        # Role-based color matching with palette fallback
        c_color = ROLE_COLORS.get(c_role.lower(), ROLE_COLORS.get(c_name.lower()))
        if not c_color:
            for k, col in ROLE_COLORS.items():
                if k in c_role.lower() or k in c_name.lower():
                    c_color = col
                    break
        if not c_color:
            c_color = ROLE_PALETTE[s_idx % len(ROLE_PALETTE)]

        speakers.append({
            "speaker_label": lbl,
            "display_name": c_name,
            "role": c_role,
            "color_hex": c_color,
        })

    assignments: Dict[int, str] = {}
    addressees: Dict[int, str] = {}
    intents: Dict[int, str] = {}
    for turn in result.get("turns", []):
        idx = turn.get("segment_index")
        if idx is None:
            continue
        spk = turn.get("speaker", "").strip()
        addr = turn.get("addressed_to", "").strip()
        intn = turn.get("intent", "statement").strip()

        matched_lbl = name_to_label.get(spk.lower())
        if not matched_lbl:
            for k, v in name_to_label.items():
                if k in spk.lower() or spk.lower() in k:
                    matched_lbl = v
                    break
        if not matched_lbl:
            matched_lbl = "SPEAKER_00" if speakers else "SPEAKER_00"

        assignments[idx] = matched_lbl
        addressees[idx] = addr
        intents[idx] = intn

    for i in range(len(segments)):
        if i not in assignments:
            assignments[i] = assignments.get(i - 1, "SPEAKER_00")
            addressees[i] = addressees.get(i - 1, "Audience")
            intents[i] = "statement"

    # Real-time physical signal: Syntactic sentence continuation bonding
    # Speech chunk boundaries (e.g. pauses, commas) mid-sentence MUST retain identical speaker & addressee
    for i in range(1, len(segments)):
        if is_sentence_continuation(segments[i - 1], segments[i]):
            assignments[i] = assignments[i - 1]
            addressees[i] = addressees[i - 1]
            if intents.get(i - 1) == "narration":
                intents[i] = "narration"

    # Prune unused speakers from the roster
    used_labels = set(assignments.values())
    speakers = [s for s in speakers if s["speaker_label"] in used_labels]

    return {
        "success": True,
        "tier": tier_label,
        "speakers": speakers,
        "segment_assignments": assignments,
        "addressee_assignments": addressees,
        "intent_assignments": intents,
    }


def identify_speakers_with_ai(
    segments: List[Dict[str, Any]],
    num_speakers: Optional[int] = 3,
    gemini_api_key: Optional[str] = None,
    openrouter_api_key: Optional[str] = None,
    cache_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Executes AI character recognition and addressee reasoning using unified AI gateway:
    1. Primary: Gemini 3.6 Flash (Free Tier)
    2. Secondary: OpenRouter Free Models (Liquid LFM, Nemotron)
    3. Returns None if both unavailable, enabling instant Tier 1 offline fallback.
    """
    if not segments:
        return None

    timeout = max(25.0, min(60.0, 10.0 + len(segments) * 0.25))
    prompt_text = _build_discourse_prompt(segments)
    res, provider = call_ai_json(
        prompt=prompt_text,
        task_tag="speakers",
        cache_key=cache_key,
        schema=DISCOURSE_SCHEMA,
        timeout=timeout,
        override_gemini_key=gemini_api_key,
        override_openrouter_key=openrouter_api_key,
    )
    if res and isinstance(res, dict):
        parsed = _parse_ai_character_response(res, segments, f"ai_{provider}")
        if parsed and parsed.get("success"):
            return parsed

    return None


def identify_speakers_with_gemini(
    segments: List[Dict[str, Any]],
    num_speakers: Optional[int] = 3,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Backwards-compatible wrapper delegating to unified AI gateway."""
    return identify_speakers_with_ai(segments, num_speakers, gemini_api_key=api_key)


def identify_speakers_with_openrouter(
    segments: List[Dict[str, Any]],
    num_speakers: Optional[int] = 3,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Backwards-compatible wrapper delegating to unified AI gateway."""
    return identify_speakers_with_ai(segments, num_speakers, openrouter_api_key=api_key)
