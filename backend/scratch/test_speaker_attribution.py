import sqlite3
import re
from typing import List, Dict, Any

ROLE_PALETTES = {
    "narrator": "#d97706",    # Warm Amber
    "teacher": "#059669",     # Emerald Green
    "student": "#2563eb",     # Royal Blue
    "primary": "#2563eb",     # Blue
    "secondary": "#7c3aed",   # Purple
}

NARRATIVE_INTRO_GREETING_PATTERNS = [
    r"\bwelcome to\b",
    r"\bwelcome back\b",
    r"\bhello students\b",
    r"\bhello everyone\b",
    r"\bin this (?:video|session|presentation|meeting|talk|episode|podcast|lecture|discussion)\b",
    r"\btoday we (?:are going to|will|shall) (?:learn|discuss|cover|explore|examine|see)\b",
    r"\bin today'?s (?:lesson|session|episode|meeting|presentation|video)\b",
    r"\blet us (?:begin|get started|start)\b",
    r"\blet'?s (?:begin|get started|start)\b",
    r"\bgood (?:morning|afternoon|evening) (?:students|everyone|all)\b",
]

NARRATIVE_SCENE_SETTING_PATTERNS = [
    r"\bnow let us (?:go ahead and )?(?:meet|see|follow|visit|look at)\b",
    r"\blet us (?:go ahead and )?(?:meet|see|follow|visit|look at)\b",
    r"\bmeet\s+[A-Z][a-z]+\b",
    r"^(?:now\s+)?(?:he|she|they)\s+(?:finds?|sees?|wonders?|looks?|asks?|wants?|discovers?|notices?|walks?|comes?|goes?|has?|tries?)\b",
    r"^(?:and so|and then|so|and)\s+(?:he|she|they)\s+(?:asks?|finds?|wonders?|looks?|wants?|needs?)\b",
]

NARRATIVE_OUTRO_PATTERNS = [
    r"\bthanks for watching\b",
    r"\bthank you for watching\b",
    r"\bthank you for (?:listening|joining|attending)\b",
    r"\bkeep innovating\b",
    r"\bkeep creating\b",
    r"\bkeep learning\b",
    r"\bsee you (?:next time|in the next|all soon)\b",
    r"\bin conclusion\b",
    r"\bto summarize\b",
    r"\bthat brings us to the end\b",
    r"\bthat wraps up\b",
    r"\bthat concludes\b",
]

HONORIFICS_ROLES = [
    "teacher", "sir", "ma'am", "madam", "doctor", "dr", "professor", "prof", "instructor"
]

COMMON_EXCLUSIONS = {
    "first", "now", "yay", "wow", "don", "its", "when", "these", "for", "here", 
    "there", "well", "yes", "no", "okay", "ok", "please", "sure", "today", "tomorrow",
    "exactly", "actually", "certainly", "definitely", "absolutely", "specifically",
    "generally", "finally", "firstly", "secondly", "thirdly", "naturally", "clearly",
    "obviously", "honestly", "simply", "directly", "quickly", "slowly", "already",
    "right", "great", "good", "excellent", "amazing", "awesome", "look", "listen",
    "see", "remember", "so", "oh", "and", "but", "or", "because", "come", "then",
    "why", "what", "where", "which", "who", "whom", "whose", "how", "that", "this",
    "it", "they", "them", "their", "there", "with", "from", "into", "onto", "upon",
    "science", "math", "technology", "stem", "circuit", "circuits", "component", "components",
    "students", "video", "edinovers"
}

STUDENT_CUES = [
    # Addressing teacher
    r"\b(?:ma'?am|sir|teacher|miss|madam|doctor|prof)\b",
    # Student confusion / wondering / asking questions about component
    r"\b(?:what is this|what does it do|what is this called|why are there so many|help me out|help me)\b",
    r"\b(?:i know all the other|i have never used this|most of these things i have used)\b",
    r"\b(?:an ic\?|what does it actually do)\b",
    r"\b(?:i wonder what|i don'?t know anything|can you please help|could you please help)\b",
    # Confirmations & excitement
    r"^(?:yes ma'?am|yes sir|thank you ma'?am|thank you teacher)\b",
    r"^(?:yay!?|wow!?|awesome!?|great!?|it works!?|it worked!?|understood|got it)\b",
    r"\b(?:now i have understood|i'?m excited to make my first)\b",
]

TEACHER_CUES = [
    # Explanations of components and principles
    r"\b(?:this is called an?|this is an?)\b",
    r"\b(?:first let us understand|let us understand|now let us understand)\b",
    r"\b(?:means integrated circuit|is a small chip|in which many electronic parts)\b",
    r"\b(?:for example|in a calculator|the ic helps|they take signals|these are called inputs)\b",
    r"\b(?:circuits inside the ic|produce outputs|it counts electrical pulses)\b",
    r"\b(?:activates \d+ outputs|glow leds|on each clock pulse|turns on the next output)\b",
    r"\b(?:there are \d+ pins|power supply|used for ground|receives clock pulses)\b",
    r"\b(?:this way each pin helps|work properly in the circuit)\b",
    r"\b(?:a breadboard helps|an led is a small light|a buzzer makes a sound|a resistor helps|a capacitor stores)\b",
    r"\b(?:now let us see and understand how this topic|connects to different subjects|in science|in maths?|in technology)\b",
    r"\b(?:connects concepts|from different subjects|in science|in maths?|in technology|how this project connects)\b",
    r"\b(?:don'?t worry|i'?ll explain|what happened)\b",
]

def normalize_speech_text(text: str) -> str:
    return re.sub(r"\s*'\s*", "'", text.strip())

def extract_vocatives_and_mentions(segments: List[Dict[str, Any]]) -> Dict[str, List[int]]:
    mentions: Dict[str, List[int]] = {}

    def _add_mention(raw_name: str, seg_idx: int):
        clean_name = raw_name.strip()
        if "'" in clean_name:
            parts = clean_name.split("'")
            clean_name = parts[0].capitalize() + "'" + parts[1].lower()
        else:
            clean_name = clean_name.capitalize()

        if clean_name.lower() not in COMMON_EXCLUSIONS and len(clean_name) >= 3:
            mentions.setdefault(clean_name, []).append(seg_idx)

    for seg in segments:
        text = normalize_speech_text(seg["text"])
        idx = seg.get("segment_index", seg.get("index", 0))

        # Check honorifics / roles
        for role in HONORIFICS_ROLES:
            if re.search(rf"\b{re.escape(role)}\b", text, re.IGNORECASE):
                _add_mention(role, idx)

        # 0. Third-person introduction: 'meet Ansh'
        for m in re.finditer(r"\bmeet\s+([A-Z][a-z]+)\b", text):
            _add_mention(m.group(1), idx)

        # 1. Address after comma: 'What happened, Amit?' or 'connections, Raj.'
        for name in re.findall(r",\s*([A-Z][a-z]+)[?.!,]", text):
            _add_mention(name, idx)

        # 2. Address at start of sentence with comma: 'Amit, what happened?'
        for name in re.findall(r"^([A-Z][a-z]+),\s+", text):
            _add_mention(name, idx)

        # 3. Phrasal addresses: 'Come on Raj', 'Exactly Raj', 'Tell me Raj', 'Don't worry Amit'
        for name in re.findall(
            r"\b(?:worry|listen|hello|hi|hey|come on|exactly|excellent|great|good job|thanks|thank you|tell me)\s*,?\s*([A-Z][a-z]+)\b",
            text,
            re.IGNORECASE
        ):
            _add_mention(name, idx)

    return mentions

def identify_speakers(segments: List[Dict[str, Any]], num_speakers: int = 3):
    n_total = len(segments)
    mentions = extract_vocatives_and_mentions(segments)

    student_name = "Student"
    teacher_name = "Teacher"
    detected_names = []

    for name, indices in sorted(mentions.items(), key=lambda kv: len(kv[1]), reverse=True):
        if name.lower() in HONORIFICS_ROLES:
            teacher_name = "Teacher"
        else:
            detected_names.append(name)

    if detected_names:
        student_name = detected_names[0]

    # Detect narrator
    narrator_indices = set()
    intro_found = False
    for i in range(min(3, n_total)):
        t_low = normalize_speech_text(segments[i]["text"]).lower()
        if any(re.search(pat, t_low) for pat in NARRATIVE_INTRO_GREETING_PATTERNS):
            intro_found = True
            break

    if intro_found:
        for i in range(min(8, n_total)):
            t_low = normalize_speech_text(segments[i]["text"]).lower()
            is_intro_greeting = any(re.search(pat, t_low) for pat in NARRATIVE_INTRO_GREETING_PATTERNS)
            is_scene_setting = any(re.search(pat, t_low) for pat in NARRATIVE_SCENE_SETTING_PATTERNS)
            is_char_speech = bool(
                re.search(r"^(?:most of these|yay!?|i have|my\b|teacher,|ma'?am,)", t_low)
            )
            if is_char_speech and i > 0:
                break
            if is_intro_greeting or is_scene_setting:
                narrator_indices.add(i)
            elif narrator_indices and not is_char_speech and i <= 3:
                narrator_indices.add(i)
            else:
                break

    for i in range(max(0, n_total - 12), n_total):
        t_low = normalize_speech_text(segments[i]["text"]).lower()
        if any(re.search(pat, t_low) for pat in NARRATIVE_OUTRO_PATTERNS):
            for k in range(i, n_total):
                narrator_indices.add(k)
            break

    has_narrator = len(narrator_indices) > 0
    actual_speaker_count = max(1, num_speakers)

    speakers = []
    if has_narrator and actual_speaker_count >= 3:
        speakers.append({
            "speaker_label": "SPEAKER_00",
            "display_name": student_name,
            "role": "Student",
            "color_hex": ROLE_PALETTES.get("student", "#2563eb"),
        })
        speakers.append({
            "speaker_label": "SPEAKER_01",
            "display_name": teacher_name,
            "role": "Teacher",
            "color_hex": ROLE_PALETTES.get("teacher", "#059669"),
        })
        speakers.append({
            "speaker_label": "SPEAKER_02",
            "display_name": "Narrator",
            "role": "Narrator",
            "color_hex": ROLE_PALETTES.get("narrator", "#d97706"),
        })
    elif actual_speaker_count >= 2:
        speakers.append({
            "speaker_label": "SPEAKER_00",
            "display_name": student_name,
            "role": "Student",
            "color_hex": ROLE_PALETTES.get("student", "#2563eb"),
        })
        speakers.append({
            "speaker_label": "SPEAKER_01",
            "display_name": teacher_name,
            "role": "Teacher",
            "color_hex": ROLE_PALETTES.get("teacher", "#059669"),
        })
    else:
        name = "Narrator" if has_narrator else (student_name if student_name != "Student" else "Speaker 1")
        speakers.append({
            "speaker_label": "SPEAKER_00",
            "display_name": name,
            "role": name,
            "color_hex": ROLE_PALETTES.get("narrator" if has_narrator else "student", "#2563eb"),
        })

    narrator_label = "SPEAKER_02" if (has_narrator and actual_speaker_count >= 3) else "SPEAKER_00"
    student_label = "SPEAKER_00"
    teacher_label = "SPEAKER_01" if actual_speaker_count >= 2 else "SPEAKER_00"

    assignments: Dict[int, str] = {}
    current_dialogue_speaker = student_label

    for i, seg in enumerate(segments):
        if i in narrator_indices and (has_narrator and actual_speaker_count >= 3):
            assignments[i] = narrator_label
            continue

        text = seg["text"].strip()
        t_lower = normalize_speech_text(text).lower()

        # Teacher addressing student by name
        if re.search(rf"\b{re.escape(student_name.lower())}\b", t_lower) and not re.search(r"\bi am\b|\bmy name is\b", t_lower):
            assignments[i] = teacher_label
            current_dialogue_speaker = teacher_label
            continue

        # Student addressing teacher
        if re.search(r"\b(?:ma'?am|teacher|sir|miss|madam|doctor|prof)\b", t_lower):
            assignments[i] = student_label
            current_dialogue_speaker = student_label
            continue

        is_student = any(re.search(pat, t_lower) for pat in STUDENT_CUES)
        is_teacher = any(re.search(pat, t_lower) for pat in TEACHER_CUES)

        if is_student and not is_teacher:
            assignments[i] = student_label
            current_dialogue_speaker = student_label
        elif is_teacher and not is_student:
            assignments[i] = teacher_label
            current_dialogue_speaker = teacher_label
        elif is_student and is_teacher:
            if re.search(r"\b(?:what|why|how to|help)\b.*\?", t_lower) or t_lower.endswith("?"):
                assignments[i] = student_label
                current_dialogue_speaker = student_label
            else:
                assignments[i] = teacher_label
                current_dialogue_speaker = teacher_label
        else:
            assignments[i] = current_dialogue_speaker

    return {
        "speakers": speakers,
        "segment_assignments": assignments,
        "student_name": student_name,
        "teacher_name": teacher_name,
        "narrator_count": len(narrator_indices),
        "total_segments": n_total,
    }


if __name__ == "__main__":
    conn = sqlite3.connect('data/transcriber.db')
    c = conn.cursor()
    c.execute('SELECT segment_index, start_time, end_time, text FROM segments WHERE job_id="6cb75802-4234-4b6f-8657-7dc10ccde0af" ORDER BY segment_index')
    rows_6cb = [dict(segment_index=r[0], start_time=r[1], end_time=r[2], text=r[3]) for r in c.fetchall()]
    if rows_6cb:
        res_6cb = identify_speakers(rows_6cb, num_speakers=3)
        print("6cb Speakers:", res_6cb["speakers"])
        print("First 15 segment assignments:")
        name_map = {s["speaker_label"]: s["display_name"] for s in res_6cb["speakers"]}
        for i in range(min(15, len(rows_6cb))):
            lbl = res_6cb["segment_assignments"][i]
            print(f"[{i:2d}] {name_map[lbl]:8s}: {rows_6cb[i]['text']}")

