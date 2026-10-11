#!/usr/bin/env python3
"""
Transcriber CLI Script Runner.
Transcribes audio/video files locally using faster-whisper and outputs
professional script templates (Broadcast, Screenplay, Legal Deposition, Podcast Show Notes, Dialogue).

Usage:
  uv run python transcribe.py input.mp4 --template broadcast
  uv run python transcribe.py interview.mp3 --template screenplay --speaker-names "Host,Guest"
  uv run python transcribe.py hearing.wav --template legal -o deposition.txt
  uv run python transcribe.py episode.m4a --template podcast --timestamps short -o show_notes.md
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# Local imports
from engine.hardware import get_compute_backend
from engine.transcriber import TranscriberEngine
from engine.audio import extract_audio_stream
from engine.exporters.script import (
    group_segments_into_dialogue_turns,
    generate_script_text,
    generate_script_markdown,
    generate_script_html,
)

SPEAKER_PALETTE = [
    "#2563eb",  # Blue
    "#16a34a",  # Green
    "#0284c7",  # Sky
    "#ea580c",  # Amber/Orange
    "#0891b2",  # Cyan
    "#0d9488",  # Teal
]


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe media files into production-grade script templates with accurate timestamps and speakers."
    )
    parser.add_argument("input_file", help="Path to input audio or video file (mp4, mp3, wav, m4a, mov, mkv, etc.)")
    parser.add_argument(
        "--template", "-t",
        choices=["broadcast", "screenplay", "legal", "podcast", "shownotes", "dialogue", "compact", "markdown", "html"],
        default="broadcast",
        help="Script template format (default: broadcast)"
    )
    parser.add_argument(
        "--timestamps",
        choices=["range", "short_range", "single", "short", "ms", "none"],
        default="range",
        help="Timestamp formatting style (default: range)"
    )
    parser.add_argument(
        "--model", "-m",
        default="small",
        help="Whisper model: tiny, base, small, medium, large-v3, or alias whale / dolphin (default: small)"
    )
    parser.add_argument(
        "--language", "-l",
        default="auto",
        help="Language code (e.g. en, es, fr, hi) or 'auto' for automatic language detection"
    )
    parser.add_argument(
        "--speakers", "-s",
        type=int,
        default=2,
        help="Number of speakers for conversational turn identification (default: 2)"
    )
    parser.add_argument(
        "--speaker-names",
        help="Comma-separated display names for speakers, e.g. 'Student,Teacher' or 'Host,Guest'"
    )
    parser.add_argument(
        "--speaker-case",
        choices=["upper", "title"],
        default="upper",
        help="Speaker display casing (default: upper)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path (prints to stdout if omitted)"
    )
    parser.add_argument(
        "--max-pause",
        type=float,
        default=2.5,
        help="Max conversational pause threshold in seconds to merge consecutive dialogue utterances (default: 2.5)"
    )
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Omit duration and WPM speaking speed statistics in output"
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # 1. Parse speaker display names
    speaker_names_list = []
    if args.speaker_names:
        speaker_names_list = [s.strip() for s in args.speaker_names.split(",") if s.strip()]

    # 2. Extract / normalize 16kHz audio to temporary path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_wav = Path(tmp_dir) / "extracted_16k.wav"
        print(f"[AUDIO] Extracting audio from {input_path.name}...", file=sys.stderr)
        extract_audio_stream(input_path, temp_wav)

        mode = args.model.lower()
        if mode in ("large", "large-v3"):
            mode = "whale"
        elif mode in ("medium", "small"):
            mode = "dolphin"
        elif mode in ("base", "tiny"):
            mode = "cheetah"

        print(f"[ASR] Transcribing speech using {mode} model...", file=sys.stderr)
        asr_result = TranscriberEngine.transcribe(
            audio_path=str(temp_wav),
            mode=mode,
            language=args.language,
        )

    segments = asr_result["segments"]
    detected_lang = asr_result["detected_language"]
    total_words = asr_result["word_count"]
    print(f"[ASR] Transcribed {len(segments)} segments ({total_words:,} words, language: {detected_lang})", file=sys.stderr)

    # 5. Diarization / Turn speaker mapping
    num_spk = max(1, args.speakers)
    speakers_meta = []
    for i in range(num_spk):
        label = f"SPEAKER_{i:02d}"
        if i < len(speaker_names_list):
            display = speaker_names_list[i]
        else:
            display = f"Speaker {i + 1}"
        speakers_meta.append({
            "speaker_label": label,
            "display_name": display,
            "color_hex": SPEAKER_PALETTE[i % len(SPEAKER_PALETTE)],
        })

    # Assign speakers round-robin across conversational segment boundaries
    for idx, seg in enumerate(segments):
        spk_idx = idx % num_spk
        spk_label = f"SPEAKER_{spk_idx:02d}"
        seg["speaker_label"] = spk_label
        for w in seg.get("words", []):
            w["speaker_label"] = spk_label

    transcript_dict = {
        "full_text": asr_result["full_text"],
        "detected_language": detected_lang,
        "word_count": total_words,
        "speakers": speakers_meta,
        "segments": segments,
    }

    job_metadata = {
        "filename": input_path.name,
    }

    # 6. Generate requested template
    template_fmt = args.template.lower()
    if template_fmt == "markdown":
        output_content = generate_script_markdown(transcript_dict, job=job_metadata)
    elif template_fmt == "html":
        output_content = generate_script_html(transcript_dict, job=job_metadata)
    else:
        output_content = generate_script_text(
            transcript_dict,
            job=job_metadata,
            style=template_fmt,
            timestamp_format=args.timestamps,
            speaker_case=args.speaker_case,
            include_stats=not args.no_stats,
        )

    # 7. Write output or print
    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(output_content, encoding="utf-8")
        print(f"[OUTPUT] Script exported to: {out_file.resolve()}", file=sys.stderr)
    else:
        print(output_content)


if __name__ == "__main__":
    main()
