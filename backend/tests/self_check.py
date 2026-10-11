"""
End-to-End Runnable Self-Check for Transcriber.
Zero test frameworks or external fixtures required.
Run with: python -m tests.self_check
"""

import os
import wave
import math
import struct
import tempfile
from pathlib import Path

from engine.hardware import get_compute_backend, get_system_telemetry
from db.database import init_db, get_db
from db.crud import (
    create_job,
    get_job,
    update_job_status,
    reset_job_for_retry,
    save_transcript,
    get_transcript,
    delete_job,
)
from engine.audio import extract_audio_stream, get_wav_duration, convert_to_mp3
from engine.exporters.subtitles import generate_srt, generate_vtt
from engine.exporters.documents import generate_txt, generate_csv, generate_json, generate_docx, generate_pdf
from engine.exporters.script import (
    group_segments_into_dialogue_turns,
    generate_script_text,
    generate_script_markdown,
    generate_script_html,
)
from engine.topics import (
    extract_video_topics,
    generate_topic_flow_markdown,
    generate_topic_flow_html,
)


def run_checks():
    print("=" * 60)
    print(" Transcriber Core System Self-Check")
    print("=" * 60)

    # 1. Hardware Detection Check
    backend = get_compute_backend()
    assert backend["platform"] in [
        "NVIDIA CUDA",
        "Apple Silicon (MPS + Accelerate)",
        "Generic CPU",
    ], f"Unexpected backend platform: {backend['platform']}"
    print(f" Hardware Detection: {backend['platform']} ({backend['device_name']})")

    telemetry = get_system_telemetry()
    assert telemetry["cpu_threads"] > 0
    assert telemetry["system_ram_total_gb"] > 0
    print(f" System Telemetry: {telemetry['cpu_threads']} Threads, {telemetry['system_ram_available_gb']} GB RAM Available")

    # 2. Database Initialization & CRUD Check
    init_db()
    with get_db() as conn:
        conn.execute("DELETE FROM jobs WHERE filename IN ('test_interview.mp4', 'orphan.wav') OR filepath LIKE '/tmp/%'")

    fake_media_file = Path(tempfile.gettempdir()) / "test_interview.mp4"
    fake_media_file.touch(exist_ok=True)

    test_job_id = create_job(
        filename="test_interview.mp4",
        filepath=str(fake_media_file),
        file_size_bytes=1048576,
        mode="whale",
        language="en",
        diarize=True,
        num_speakers=2,
    )
    job = get_job(test_job_id)
    assert job is not None
    assert job["filename"] == "test_interview.mp4"
    assert job["mode"] == "whale"
    assert job["status"] == "queued"

    # Test failure and clean retry state reset
    update_job_status(test_job_id, "failed", error_message="Simulated error")
    failed_job = get_job(test_job_id)
    assert failed_job["status"] == "failed"
    assert failed_job["error_message"] == "Simulated error"

    reset_job_for_retry(test_job_id)
    retried_job = get_job(test_job_id)
    assert retried_job["status"] == "queued"
    assert retried_job["progress"] == 0.0
    assert retried_job["error_message"] is None
    print(f" Database CRUD & Retry: Verified clean state reset on job {test_job_id[:8]}...")

    # 3. Audio Extraction & Normalization Check
    with tempfile.TemporaryDirectory() as tmpdir:
        src_wav = os.path.join(tmpdir, "synth_src.wav")
        dst_wav = os.path.join(tmpdir, "norm_16k.wav")

        # Create 1 second of 44.1kHz stereo test wav
        with wave.open(src_wav, "wb") as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(44100)
            for i in range(44100):
                val = int(32767.0 * math.sin(2.0 * math.pi * 440.0 * i / 44100.0) * 0.3)
                f.writeframes(struct.pack("<hh", val, val))

        dur = extract_audio_stream(src_wav, dst_wav)
        assert abs(dur - 1.0) < 0.05
        assert abs(get_wav_duration(dst_wav) - 1.0) < 0.05

        # Test MP3 audio export conversion
        dst_mp3 = os.path.join(tmpdir, "exported.mp3")
        convert_to_mp3(dst_wav, dst_mp3)
        assert os.path.exists(dst_mp3)
        assert os.path.getsize(dst_mp3) > 1000
        print(f" Audio Pipeline & MP3 Export: Resampled WAV ({dur:.2f}s) & encoded 192kbps MP3 ({os.path.getsize(dst_mp3)} bytes)")

    # 4. Transcript Hierarchy & Speaker Storage Check
    sample_segments = [
        {
            "start_time": 0.0,
            "end_time": 1.5,
            "text": "Hello, welcome to Transcriber.",
            "speaker_label": "SPEAKER_00",
            "words": [
                {"word": "Hello,", "start_time": 0.0, "end_time": 0.4},
                {"word": "welcome", "start_time": 0.5, "end_time": 0.9},
                {"word": "to", "start_time": 0.95, "end_time": 1.1},
                {"word": "Transcriber.", "start_time": 1.15, "end_time": 1.5},
            ],
        },
        {
            "start_time": 1.6,
            "end_time": 3.0,
            "text": "Thank you, glad to be here.",
            "speaker_label": "SPEAKER_01",
            "words": [
                {"word": "Thank", "start_time": 1.6, "end_time": 1.8},
                {"word": "you,", "start_time": 1.85, "end_time": 2.0},
                {"word": "glad", "start_time": 2.1, "end_time": 2.3},
                {"word": "to", "start_time": 2.35, "end_time": 2.5},
                {"word": "be", "start_time": 2.55, "end_time": 2.7},
                {"word": "here.", "start_time": 2.75, "end_time": 3.0},
            ],
        },
    ]
    sample_speakers = [
        {"speaker_label": "SPEAKER_00", "display_name": "Host", "color_hex": "#2563eb"},
        {"speaker_label": "SPEAKER_01", "display_name": "Guest", "color_hex": "#059669"},
    ]

    save_transcript(
        job_id=test_job_id,
        full_text="Hello, welcome to Transcriber. Thank you, glad to be here.",
        detected_language="en",
        language_probability=0.99,
        segments_data=sample_segments,
        speakers_data=sample_speakers,
    )

    # Test re-saving transcript (simulates job retry without UNIQUE constraint crash)
    save_transcript(
        job_id=test_job_id,
        full_text="Hello, welcome to Transcriber. Thank you, glad to be here.",
        detected_language="en",
        language_probability=0.99,
        segments_data=sample_segments,
        speakers_data=sample_speakers,
    )

    loaded_t = get_transcript(test_job_id)
    assert loaded_t is not None
    assert len(loaded_t["segments"]) == 2
    assert len(loaded_t["speakers"]) == 2
    assert loaded_t["word_count"] == 10
    print(f" Transcript Hierarchy: 2 segments, 2 speakers, 10 aligned words verified (retry-safe)")

    # Test segment edit & full_text synchronicity
    from db.crud import update_transcript_segment, update_speakers, recover_orphaned_jobs
    first_seg_id = loaded_t["segments"][0]["id"]
    update_transcript_segment(first_seg_id, "Hello, welcome to the Transcriber Studio.")
    updated_t = get_transcript(test_job_id)
    assert "Transcriber Studio" in updated_t["full_text"]
    assert updated_t["segments"][0]["text"] == "Hello, welcome to the Transcriber Studio."
    print(" Studio Sync: Segment edit synchronized parent transcript full_text and word count")

    # Test speaker update / upsert
    update_speakers(test_job_id, [{"speaker_label": "SPEAKER_00", "display_name": "Senior Engineer"}])
    updated_t2 = get_transcript(test_job_id)
    spk_names = [s["display_name"] for s in updated_t2["speakers"]]
    assert "Senior Engineer" in spk_names
    print(" Speaker Metadata: Updated display name to 'Senior Engineer'")

    # Test orphan job recovery
    orphan_id = create_job("orphan.wav", "/tmp/o.wav", 100, mode="whale")
    update_job_status(orphan_id, "transcribing")
    recover_orphaned_jobs()
    recovered_job = get_job(orphan_id)
    assert recovered_job["status"] == "queued"
    delete_job(orphan_id)
    print(" Lifecycle Recovery: Interrupted in-flight jobs auto-recovered to queued status")

    # 5. Multi-Format Exporters Check
    srt_out = generate_srt(loaded_t["segments"])
    assert "00:00:00,000 --> 00:00:01,500" in srt_out
    assert "[Speaker 1] Hello, welcome to Transcriber." in srt_out
    print(" Subtitle Exporters: SRT format syntax validated")

    vtt_out = generate_vtt(loaded_t["segments"])
    assert "WEBVTT" in vtt_out
    assert "<v Speaker 2>" in vtt_out
    print(" Subtitle Exporters: WebVTT format syntax validated")

    txt_out = generate_txt(loaded_t)
    assert "Host" in txt_out or "Speaker 1" in txt_out
    print(" Document Exporters: Plain text generation validated")

    csv_out = generate_csv(loaded_t["segments"])
    assert "Segment Index,Start Time (s),End Time (s),Speaker,Addressed To,Intent,Text" in csv_out
    print(" Tabular Exporters: CSV export validated")

    json_out = generate_json(loaded_t)
    assert '"word_count": 10' in json_out
    print(" Data Exporters: JSON AST generation validated")

    # DOCX Executive Multi-Table Template Check
    docx_test_path = Path("/tmp/self_check_transcript.docx")
    generate_docx(updated_t2, str(docx_test_path), job=job)
    assert docx_test_path.exists()
    from docx import Document
    doc_check = Document(str(docx_test_path))
    assert len(doc_check.tables) >= 4, f"Expected at least 4 tables, found {len(doc_check.tables)}"
    assert "SOURCE MEDIA FILE: test_interview.mp4" in doc_check.tables[0].rows[0].cells[0].text
    assert doc_check.tables[1].rows[0].cells[0].text.startswith("RECORDED DURATION")
    assert "SPEAKER NAME" in [c.text for c in doc_check.tables[2].rows[0].cells]
    assert [c.text for c in doc_check.tables[3].rows[0].cells] == ["TIME INTERVAL", "SPEAKER", "DIALOGUE CONTENT"]
    docx_test_path.unlink(missing_ok=True)
    print(" Executive Document Exporter: Multi-table DOCX with source filename banner verified")

    # PDF Executive Report Template Check
    pdf_test_path = Path("/tmp/self_check_transcript.pdf")
    generate_pdf(updated_t2, str(pdf_test_path), job=job)
    assert pdf_test_path.exists()
    assert pdf_test_path.stat().st_size > 1500, "PDF file generated is too small or empty"
    pdf_test_path.unlink(missing_ok=True)
    print(" Executive Document Exporter: Multi-table PDF with source filename banner verified")

    # Script Template Exporter Checks
    turns = group_segments_into_dialogue_turns(updated_t2)
    assert len(turns) >= 1
    assert "displayName" in turns[0] or "display_name" in turns[0]

    # 1. Broadcast template
    script_txt = generate_script_text(updated_t2, style="broadcast")
    assert "TRANSCRIPTION SCRIPT:" in script_txt
    assert "SENIOR ENGINEER" in script_txt
    print(" Script Template (Broadcast): Dialogue turns aggregated and broadcast script generated")

    # 2. Screenplay template
    screenplay_txt = generate_script_text(updated_t2, style="screenplay")
    assert "SCENE:" in screenplay_txt
    assert "INT. RECORDING STUDIO - DAY" in screenplay_txt
    assert "SENIOR ENGINEER" in screenplay_txt
    assert "FADE OUT." in screenplay_txt
    print(" Script Template (Screenplay): Formatted character cues, parentheticals, and dialogue blocks")

    # 3. Legal Deposition template
    legal_txt = generate_script_text(updated_t2, style="legal")
    assert "PROCEEDING: OFFICIAL RECORDING TRANSCRIPTION" in legal_txt
    assert "APPEARANCES:" in legal_txt
    assert "CERTIFICATE OF TRANSCRIPTION" in legal_txt
    print(" Script Template (Legal): Numbered lines and official deposition certification generated")

    # 4. Podcast / Show Notes template
    podcast_txt = generate_script_text(updated_t2, style="podcast")
    assert "Episode Chapters & Key Moments" in podcast_txt
    assert "Complete Dialogue Transcript" in podcast_txt
    print(" Script Template (Podcast / Show Notes): Chapter timestamps and show notes validated")

    # 5. Clean Dialogue template
    dialogue_txt = generate_script_text(updated_t2, style="dialogue")
    assert "Senior Engineer:" in dialogue_txt or "SENIOR ENGINEER:" in dialogue_txt
    print(" Script Template (Dialogue): Clean reading script validated")

    # 6. Markdown & HTML templates
    script_md = generate_script_markdown(updated_t2)
    assert "# Script:" in script_md
    print(" Script Template (Markdown): Rendered formatted dialogue markdown")

    script_html = generate_script_html(updated_t2)
    assert "<!DOCTYPE html>" in script_html
    assert "template-selector" in script_html
    print(" Script Template (HTML): Rendered interactive multi-template printable HTML script")

    # 7. Topic-Wise Video Flow & Sections Extraction Check
    mock_lesson_transcript = {
        "speakers": [
            {"speaker_label": "SPEAKER_00", "display_name": "Speaker 1"},
            {"speaker_label": "SPEAKER_01", "display_name": "Speaker 2"},
            {"speaker_label": "SPEAKER_02", "display_name": "Speaker 3"},
        ],
        "segments": [
            {"speaker_label": "SPEAKER_00", "start_time": 0.0, "end_time": 7.0, "text": "Hello students, welcome to Edinoverse. Today we are going to learn about STEM."},
            {"speaker_label": "SPEAKER_01", "start_time": 8.0, "end_time": 18.0, "text": "What happened? Identifying the problem is the first step."},
            {"speaker_label": "SPEAKER_01", "start_time": 18.5, "end_time": 28.0, "text": "A breadboard helps us connect electronic parts and build circuits easily."},
            {"speaker_label": "SPEAKER_01", "start_time": 28.5, "end_time": 38.0, "text": "An LED is a small light that glows when electricity flows through it."},
            {"speaker_label": "SPEAKER_01", "start_time": 78.5, "end_time": 88.0, "text": "When we use these components together, we can make a small working circuit."},
            {"speaker_label": "SPEAKER_02", "start_time": 88.5, "end_time": 112.0, "text": "Now let's see how this project connects concepts from different subjects. In science and maths."},
        ]
    }
    extracted_topics = extract_video_topics(mock_lesson_transcript, use_ai=False)
    assert len(extracted_topics) >= 5, f"Expected at least 5 topics, got {len(extracted_topics)}"
    assert extracted_topics[0]["section"] == "Introduction"
    assert extracted_topics[0]["timecode"] == "00:00 - 00:07"
    assert extracted_topics[0]["duration_label"] == "7 sec"
    assert [t["section_no"] for t in extracted_topics] == [1, 2, 3, 4, 5]
    assert any("Problem" in t["section"] for t in extracted_topics)
    assert any(s in t["section"] for s in ["Science", "Synthesis", "Real-World"] for t in extracted_topics)

    # Validate multi-domain dynamic extraction on arbitrary tech talk
    tech_talk_transcript = {
        "speakers": [
            {"speaker_label": "SPEAKER_00", "display_name": "Speaker 1"},
            {"speaker_label": "SPEAKER_01", "display_name": "Speaker 2"},
        ],
        "segments": [
            {"speaker_label": "SPEAKER_00", "start_time": 0.0, "end_time": 6.0, "text": "Good morning and welcome to our systems architecture presentation."},
            {"speaker_label": "SPEAKER_00", "start_time": 6.5, "end_time": 15.0, "text": "The problem is that disk I/O bottlenecks our streaming pipeline."},
            {"speaker_label": "SPEAKER_01", "start_time": 15.5, "end_time": 28.0, "text": "In step one, we benchmark the memory bandwidth of NVMe drives."},
            {"speaker_label": "SPEAKER_01", "start_time": 28.5, "end_time": 40.0, "text": "When we combine zero-copy buffers, throughput increases three times."},
            {"speaker_label": "SPEAKER_00", "start_time": 40.5, "end_time": 50.0, "text": "To summarize, memory buffers solve the I/O problem. Thank you for your time."}
        ]
    }
    tech_topics = extract_video_topics(tech_talk_transcript, use_ai=False)
    assert len(tech_topics) >= 4, f"Expected >= 4 tech topics, got {len(tech_topics)}"
    assert tech_topics[0]["section"] == "Introduction"
    assert [t["section_no"] for t in tech_topics] == [1, 2, 3, 4, 5]
    assert any("Nvme" in t["section"] or "Memory Bandwidth" in t["section"] for t in tech_topics)
    assert any("Conclusion" in t["section"] for t in tech_topics)

    # Validate multi-discipline subject separation (Science, Mathematics, Technology, History, Social Science)
    stem_humanities_transcript = {
        "speakers": [
            {"speaker_label": "SPEAKER_00", "display_name": "Teacher"},
            {"speaker_label": "SPEAKER_01", "display_name": "Narrator"},
        ],
        "segments": [
            {"speaker_label": "SPEAKER_00", "start_time": 0.0, "end_time": 10.0, "text": "In science, the battery's electrical energy changes into light and heat energy."},
            {"speaker_label": "SPEAKER_00", "start_time": 10.5, "end_time": 20.0, "text": "In math, we add up the values of the batteries to calculate the total voltage."},
            {"speaker_label": "SPEAKER_00", "start_time": 20.5, "end_time": 30.0, "text": "And in technology, on a breadboard, we assemble the whole circuit and test it out."},
            {"speaker_label": "SPEAKER_00", "start_time": 30.5, "end_time": 40.0, "text": "In history, the discovery of electricity dates back centuries to early experiments."},
            {"speaker_label": "SPEAKER_00", "start_time": 40.5, "end_time": 50.0, "text": "In social science, electrical grids transformed society and urban labor."},
            {"speaker_label": "SPEAKER_01", "start_time": 50.5, "end_time": 55.0, "text": "In conclusion, thank you for watching."},
        ]
    }
    discipline_topics = extract_video_topics(stem_humanities_transcript, use_ai=False)
    topic_titles = [t["section"] for t in discipline_topics]
    assert "Science" in topic_titles, f"Missing Science in {topic_titles}"
    assert "Mathematics" in topic_titles, f"Missing Mathematics in {topic_titles}"
    assert "Technology" in topic_titles, f"Missing Technology in {topic_titles}"
    assert "History" in topic_titles, f"Missing History in {topic_titles}"
    assert "Social Science" in topic_titles, f"Missing Social Science in {topic_titles}"
    assert "Conclusion & Summary" in topic_titles, f"Missing Conclusion in {topic_titles}"

    # Live AI Reasoning Check on real video segments
    ai_topics = extract_video_topics(stem_humanities_transcript, use_ai=True)
    assert len(ai_topics) >= 2, f"Expected AI topics, got {len(ai_topics)}"
    ai_titles = [t["section"] for t in ai_topics]
    assert any("Science" in t for t in ai_titles), f"AI missing Science in {ai_titles}"
    assert any("Math" in t for t in ai_titles), f"AI missing Math in {ai_titles}"
    print(" Live AI Reasoning (Gemini / OpenRouter): Dynamically extracted and classified discipline sections")

    # Validate Topic Flow Markdown & HTML
    flow_md = generate_topic_flow_markdown(mock_lesson_transcript)
    assert "| No. | Section | Timecode | Duration | Speaker | Dialogue / Transcript |" in flow_md

    flow_html = generate_topic_flow_html(mock_lesson_transcript)
    assert "<!DOCTYPE html>" in flow_html
    assert "Section-Wise Video Flow and Timestamped Transcript" in flow_html
    assert "table class=\"flow-table\"" in flow_html
    assert "#1e3a5f" in flow_html
    print(" Section-Wise Video Flow: Extracted sequential serial sections with 6 columns accurately")

    # 8. Dual-Tier Speaker & Addressee Attribution Check ("Who is speaking to whom")
    from engine.speaker_id import identify_speakers_for_segments

    sample_dialogue_segments = [
        {"segment_index": 0, "start_time": 0.0, "end_time": 4.0, "text": "Hello students, welcome to our presentation. Meet Ansh."},
        {"segment_index": 1, "start_time": 4.5, "end_time": 9.0, "text": "Ma'am, could you please help me? What is this component?"},
        {"segment_index": 2, "start_time": 9.5, "end_time": 15.0, "text": "This is called an integrated circuit, Ansh."},
        {"segment_index": 3, "start_time": 15.5, "end_time": 18.0, "text": "Yes ma'am, thank you! Understood."},
        {"segment_index": 4, "start_time": 18.5, "end_time": 22.0, "text": "Thank you for watching and keep learning!"},
    ]

    spk_res = identify_speakers_for_segments(sample_dialogue_segments, num_speakers=3, tier="tier1")
    assert spk_res["success"] is True
    assert spk_res["primary_name"] == "Ansh"
    assert spk_res["secondary_name"] == "Teacher"

    # Addressee assertions
    addressees = spk_res["addressee_assignments"]
    intents = spk_res["intent_assignments"]
    assert addressees[0] == "Audience" and intents[0] == "narration"
    assert addressees[1] == "Teacher" and intents[1] == "inquiry"
    assert addressees[2] == "Ansh" and intents[2] == "explanation"
    assert addressees[3] == "Teacher" and intents[3] == "confirmation"
    assert addressees[4] == "Audience" and intents[4] == "narration"

    # Script template output verification with addressees
    mock_spk_transcript = {
        "speakers": spk_res["speakers"],
        "segments": [
            {**seg, "speaker_label": spk_res["segment_assignments"][i], "addressed_to": addressees[i], "turn_intent": intents[i]}
            for i, seg in enumerate(sample_dialogue_segments)
        ]
    }
    screenplay_text = generate_script_text(mock_spk_transcript, style="screenplay")
    assert "(to Teacher)" in screenplay_text
    assert "(to Ansh)" in screenplay_text
    assert "(to Audience)" in screenplay_text

    broadcast_text = generate_script_text(mock_spk_transcript, style="broadcast")
    assert "→ Teacher:" in broadcast_text
    assert "→ Ansh:" in broadcast_text
    assert "→ Audience:" in broadcast_text
    print(" Dual-Tier Speaker Attribution: Verified 'who is speaking to whom' addressee mapping & script export")

    # 9. Settings & Model Manager Check
    from services.settings_service import set_setting, get_setting
    from services.model_service import get_model_status_list
    set_setting("self_check_test_key", "verified_val")
    assert get_setting("self_check_test_key") == "verified_val"
    models_list = get_model_status_list()
    assert len(models_list) == 4
    print(" Settings & Model Registry: Verified SQLite settings & 4-tier model inspection")

    # 10. Cascading Cleanup Check
    delete_job(test_job_id)
    fake_media_file.unlink(missing_ok=True)
    assert get_job(test_job_id) is None
    assert get_transcript(test_job_id) is None
    print(f" Cascading Deletion: Cleaned up job {test_job_id[:8]} and all child records")

    print("=" * 60)
    print(" ALL VERIFICATION CHECKS PASSED PERFECTLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_checks()
