"""
Security and Engine Flaw Regression Tests.
Verifies all security fixes and edge-case defenses in backend/engine.
"""

import re
from engine.exporters.documents import generate_csv, _sanitize_csv_cell, _safe_hex_color
from engine.exporters.subtitles import generate_vtt, format_timestamp_srt, format_timestamp_vtt
from engine.exporters.script import generate_script_html
from engine.topics import format_tc, format_duration_label
from engine.transcriber import TranscriberEngine


def test_csv_formula_injection():
    # CWE-1236: CSV cells starting with formula characters must be prefixed with single quote
    malicious_inputs = ["=SUM(A1:A10)", "+cmd|' /C calc'!A0", "-5+2", "@mention", "\tmalicious", "\rmalicious"]
    for inp in malicious_inputs:
        sanitized = _sanitize_csv_cell(inp)
        assert sanitized.startswith("'"), f"Failed to sanitize CSV formula trigger: {inp}"

    benign = "Normal spoken text"
    assert _sanitize_csv_cell(benign) == benign

    segments = [
        {"start_time": 0.0, "end_time": 2.0, "speaker_label": "SPEAKER_00", "text": "=cmd|' /C calc'!A0"}
    ]
    csv_out = generate_csv(segments)
    assert "'=cmd|" in csv_out, "CSV generation output did not neutralize formula injection"
    print(" CSV Formula Injection Defense verified.")


def test_pdf_safe_hex_color():
    assert _safe_hex_color("#2563EB") == "#2563EB"
    assert _safe_hex_color("#ff00aa") == "#ff00aa"
    # Invalid colors must fall back to default
    assert _safe_hex_color("invalid") == "#2563EB"
    assert _safe_hex_color('<font color="red">') == "#2563EB"
    assert _safe_hex_color("#12345") == "#2563EB"
    assert _safe_hex_color(None) == "#2563EB"
    print(" PDF ReportLab Safe Hex Color validation verified.")


def test_script_html_security_and_js_property():
    transcript = {
        "segments": [
            {"start_time": 0.0, "end_time": 2.5, "speaker_label": "SPEAKER_00", "text": "</script><script>alert(1)</script>"}
        ],
        "speakers": [
            {"speaker_label": "SPEAKER_00", "display_name": 'Dr. O\'Connor <img src=x onerror=alert(1)>'}
        ]
    }
    html_out = generate_script_html(transcript, job={"filename": "Test <script> ' Recording.mp4"})
    assert "</script><script>" not in html_out, "XSS script breakout detected in HTML exporter"
    assert "\\u003c/script>" in html_out, "JSON < was not properly escaped into \\u003c"
    assert "(t.display_name || '').toLowerCase()" in html_out, "display_name property bug found in JS filter"
    print(" Script HTML XSS sanitization and JS search property verified.")


def test_vtt_speaker_tag_sanitization():
    segments = [
        {"start_time": 0.0, "end_time": 1.5, "speaker_label": "SPEAKER_00", "text": "Hello world"}
    ]
    speakers = [
        {"speaker_label": "SPEAKER_00", "display_name": "Speaker <One>\r\nExtra"}
    ]
    vtt = generate_vtt(segments, speakers)
    # Must not contain unescaped angle brackets or newlines inside the <v ...> voice cue
    assert "<v Speaker One Extra>Hello world</v>" in vtt or "<v Speaker OneExtra>Hello world</v>" in vtt
    assert "<v Speaker <" not in vtt
    print(" WebVTT voice cue tag sanitization verified.")


def test_null_timestamp_handling():
    assert format_tc(None) == "00:00"
    assert format_duration_label(None) == "1 sec"
    assert format_timestamp_srt(None) == "00:00:00,000"
    assert format_timestamp_vtt(None) == "00:00:00.000"
    print(" Null timestamp and duration guards verified.")


def test_upload_extension_security():
    from api.routes.jobs import ALLOWED_MEDIA_EXTENSIONS
    dangerous_extensions = [".exe", ".sh", ".py", ".bat", ".php", ".js"]
    for ext in dangerous_extensions:
        assert ext not in ALLOWED_MEDIA_EXTENSIONS
    assert ".mp3" in ALLOWED_MEDIA_EXTENSIONS
    assert ".wav" in ALLOWED_MEDIA_EXTENSIONS
    assert ".mp4" in ALLOWED_MEDIA_EXTENSIONS
    print(" Upload allowed media extensions security verified.")


def test_url_scheme_security():
    import pytest
    import asyncio
    from services.job_service import service_download_and_queue_url

    with pytest.raises(ValueError, match="Invalid URL"):
        asyncio.run(service_download_and_queue_url(
            url="file:///etc/passwd",
            mode="whale",
            language="auto",
            task="transcribe",
            diarize=False,
            num_speakers=None,
            restore_audio=False,
            initial_prompt=None,
        ))
    print(" SSRF URL scheme validation verified.")


def test_ssrf_private_network_blocking():
    import pytest
    import asyncio
    from services.job_service import service_download_and_queue_url

    blocked_urls = [
        "http://localhost:8000/secret",
        "http://127.0.0.1:8000/test",
        "http://169.254.169.254/latest/meta-data/",
        "http://service.local/dump",
    ]
    for b_url in blocked_urls:
        with pytest.raises(ValueError, match="forbidden"):
            asyncio.run(service_download_and_queue_url(
                url=b_url,
                mode="whale",
                language="auto",
                task="transcribe",
                diarize=False,
                num_speakers=None,
                restore_audio=False,
                initial_prompt=None,
            ))
    print(" SSRF private network and metadata IP blocking verified.")


def test_safe_id_validation():
    from db.crud import is_safe_id, get_job, delete_job
    assert is_safe_id("c42e40dc") is True
    assert is_safe_id("6a929fe7-786c-4f42-b067-84880cdf554d") is True
    assert is_safe_id("../../etc/passwd") is False
    assert is_safe_id("job/../bad") is False
    assert is_safe_id("") is False
    assert is_safe_id(None) is False

    assert get_job("../../etc/passwd") is None
    assert delete_job("../../etc/passwd") is False
    print(" Entity ID path traversal protection verified.")


def test_speaker_color_hex_validation():
    from api.schemas import SpeakerUpdateItem
    valid = SpeakerUpdateItem(speaker_label="SPEAKER_00", display_name="Host", color_hex="#10b981")
    assert valid.color_hex == "#10b981"

    malicious = SpeakerUpdateItem(speaker_label="SPEAKER_00", display_name="Host", color_hex='"><script>')
    assert malicious.color_hex == "#2563eb"

    bad_len = SpeakerUpdateItem(speaker_label="SPEAKER_00", display_name="Host", color_hex="#12345")
    assert bad_len.color_hex == "#2563eb"
    print(" SpeakerUpdateItem color hex sanitization verified.")


def test_vocative_caching_and_subtitles():
    from engine.speaker_id import is_direct_vocative_to
    from engine.exporters.subtitles import format_timestamp_srt, format_timestamp_vtt

    assert is_direct_vocative_to("David", "David, what is this component?") is True
    assert is_direct_vocative_to("David", "Now let us meet David") is False
    assert is_direct_vocative_to("David", "Thank you, David.") is True

    assert format_timestamp_srt(125.456) == "00:02:05,456"
    assert format_timestamp_vtt(125.456) == "00:02:05.456"
    print(" Vocative pattern matcher and subtitle divmod formatters verified.")


def test_word_synchronization_accuracy():
    from db.database import get_db
    from db.crud import sync_segment_words, create_job, save_transcript, delete_job

    job_id = create_job("test.wav", "/tmp/test.wav", 1000)
    save_transcript(
        job_id=job_id,
        full_text="one two three four",
        detected_language="en",
        language_probability=0.99,
        segments_data=[{
            "start_time": 0.0,
            "end_time": 4.0,
            "text": "one two three four",
            "speaker_label": "SPEAKER_00",
            "words": [
                {"word": "one", "start_time": 0.0, "end_time": 1.0, "confidence_score": 1.0},
                {"word": "two", "start_time": 1.0, "end_time": 2.0, "confidence_score": 1.0},
                {"word": "three", "start_time": 2.0, "end_time": 3.0, "confidence_score": 1.0},
                {"word": "four", "start_time": 3.0, "end_time": 4.0, "confidence_score": 1.0},
            ]
        }],
        speakers_data=[{"speaker_label": "SPEAKER_00", "display_name": "Speaker 1"}]
    )

    with get_db() as conn:
        seg_row = conn.execute("SELECT id FROM segments WHERE job_id = ?", (job_id,)).fetchone()
        test_seg_id = seg_row["id"]

        # 1. Word count matches: 1-to-1 text replacement keeping timestamps
        sync_segment_words(conn, test_seg_id, "first second third fourth")
        w_rows = conn.execute("SELECT word, start_time, end_time FROM words WHERE segment_id = ? ORDER BY word_index ASC", (test_seg_id,)).fetchall()
        assert len(w_rows) == 4
        assert [r["word"] for r in w_rows] == ["first", "second", "third", "fourth"]
        assert w_rows[0]["start_time"] == 0.0
        assert w_rows[0]["end_time"] == 1.0

        # 2. Word count differs: proportional redistribution
        sync_segment_words(conn, test_seg_id, "alpha beta")
        w_rows2 = conn.execute("SELECT word, start_time, end_time FROM words WHERE segment_id = ? ORDER BY word_index ASC", (test_seg_id,)).fetchall()
        assert len(w_rows2) == 2
        assert [r["word"] for r in w_rows2] == ["alpha", "beta"]
        assert w_rows2[0]["start_time"] == 0.0
        assert w_rows2[0]["end_time"] == 2.0
        assert w_rows2[1]["start_time"] == 2.0
        assert w_rows2[1]["end_time"] == 4.0

    delete_job(job_id)
    print(" Word synchronization accuracy and proportional redistribution verified.")


def test_waveform_peak_generation():
    import wave
    import struct
    import math
    import tempfile
    from engine.audio import generate_waveform_peaks

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        wav_path = tf.name

    try:
        # Generate 1-second 440Hz sine wave at 16kHz
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            frames = bytearray()
            for i in range(16000):
                val = int(16000 * math.sin(2 * math.pi * 440 * i / 16000))
                frames.extend(struct.pack("<h", val))
            wf.writeframes(frames)

        peaks = generate_waveform_peaks(wav_path, num_peaks=32)
        assert len(peaks) == 32
        assert all(0.0 <= p <= 1.0 for p in peaks)
        assert max(peaks) == 1.0  # Scaled to peak amplitude
    finally:
        import os
        if os.path.exists(wav_path):
            os.remove(wav_path)

    print(" Acoustic waveform peak generation verified.")


def test_memory_release_and_endpoints():
    from fastapi.testclient import TestClient
    from main import app
    from engine.transcriber import TranscriberEngine

    # Directly verify engine release method
    assert isinstance(TranscriberEngine.release_model(), bool)

    client = TestClient(app)
    # Test POST /api/system/release_memory
    res_mem = client.post("/api/system/release_memory")
    assert res_mem.status_code == 200
    assert res_mem.json()["success"] is True

    # Test GET /api/jobs/{job_id}/waveform validation
    res_bad = client.get("/api/jobs/job..bad/waveform")
    assert res_bad.status_code == 400

    res_missing = client.get("/api/jobs/nonexistent_job_123/waveform?points=16")
    assert res_missing.status_code == 200
    assert len(res_missing.json()["peaks"]) == 16

    # Test dialogues and topics ID validation
    assert client.get("/api/jobs/bad..id/dialogues").status_code == 400
    assert client.get("/api/jobs/bad..id/topics").status_code == 400
    assert client.get("/api/jobs/bad..id/script/preview").status_code == 400
    assert client.get("/api/jobs/bad..id/transcript").status_code == 400
    assert client.put("/api/jobs/bad..id/segments/safe_seg", json={"text": "hello"}).status_code == 400
    assert client.put("/api/jobs/safe_id/segments/bad..seg", json={"text": "hello"}).status_code == 400
    print(" Memory release endpoint and waveform/dialogue/speaker API security verified.")


def test_pagination_and_num_speakers_guards():
    from services.job_service import service_list_jobs
    from fastapi.testclient import TestClient
    from main import app

    # Pagination bounds clamping
    p_zero = service_list_jobs(None, page=0, limit=-10)
    assert p_zero["page"] == 1
    assert p_zero["limit"] == 1

    p_excess = service_list_jobs(None, page=2, limit=9999)
    assert p_excess["page"] == 2
    assert p_excess["limit"] == 200

    # Num speakers validation via API
    client = TestClient(app)
    res_high = client.post("/api/jobs/url", json={"url": "https://example.com/audio.mp3", "num_speakers": 64})
    assert res_high.status_code == 400

    res_neg = client.post("/api/jobs/url", json={"url": "https://example.com/audio.mp3", "num_speakers": -5})
    assert res_neg.status_code == 400

    # No-extension upload rejection
    res_no_ext = client.post(
        "/api/jobs/upload",
        files=[("files", ("audio_without_extension", b"fake audio content", "application/octet-stream"))]
    )
    assert res_no_ext.status_code == 400
    print(" Pagination clamping, num_speakers bounds, and extension security verified.")


def test_executive_intelligence_suite():
    from engine.intelligence import (
        _heuristic_executive_intelligence,
        export_intelligence_markdown,
    )
    from fastapi.testclient import TestClient
    from main import app

    sample_transcript = {
        "job_id": "test_intel_job",
        "full_text": "Welcome to our engineering standup. We will deploy the release at noon.",
        "segments": [
            {
                "speaker_label": "SPEAKER_00",
                "start_time": 0.0,
                "end_time": 10.0,
                "text": "Welcome to our engineering standup.",
            },
            {
                "speaker_label": "SPEAKER_01",
                "start_time": 10.0,
                "end_time": 25.0,
                "text": "We will deploy the release at noon and verify telemetry.",
            },
        ],
    }

    # Test offline heuristic generator
    intel = _heuristic_executive_intelligence(sample_transcript, job={"filename": "standup.mp3", "duration_seconds": 25.0})
    assert "tldr" in intel and len(intel["tldr"]) > 0
    assert "executive_summary" in intel
    assert isinstance(intel["key_takeaways"], list)
    assert isinstance(intel["chapters"], list)
    assert any("deploy the release" in act["task"] for act in intel["action_items"])

    # Test markdown export
    md = export_intelligence_markdown(intel)
    assert "# Executive Briefing" in md
    assert "## TL;DR" in md
    assert "Action Items & Next Steps" in md

    # Test API endpoints
    client = TestClient(app)
    # Bad job id rejection
    assert client.get("/api/jobs/bad..id/intelligence").status_code == 400
    assert client.post("/api/jobs/bad..id/intelligence/generate").status_code == 400
    assert client.get("/api/jobs/bad..id/intelligence/export").status_code == 400
    print(" Executive AI Intelligence suite and API security verified.")


if __name__ == "__main__":
    print("============================================================")
    print("  Engine Security & Defect Regression Test Suite")
    print("============================================================")
    test_csv_formula_injection()
    test_pdf_safe_hex_color()
    test_script_html_security_and_js_property()
    test_vtt_speaker_tag_sanitization()
    test_null_timestamp_handling()
    test_upload_extension_security()
    test_url_scheme_security()
    test_ssrf_private_network_blocking()
    test_safe_id_validation()
    test_speaker_color_hex_validation()
    test_vocative_caching_and_subtitles()
    test_word_synchronization_accuracy()
    test_waveform_peak_generation()
    test_memory_release_and_endpoints()
    test_pagination_and_num_speakers_guards()
    test_executive_intelligence_suite()
    print("============================================================")
    print(" ALL ENGINE SECURITY AND DEFECT TESTS PASSED!")
    print("============================================================")


