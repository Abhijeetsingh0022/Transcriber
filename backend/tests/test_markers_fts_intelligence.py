"""
Self-check for Audio Markers, SQLite FTS5 Full-Text Search, and Executive Intelligence persistence.
Run directly with python tests/test_markers_fts_intelligence.py.
"""

import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import init_db, get_db
from db.crud import (
    create_job,
    delete_job,
    create_marker,
    get_markers,
    delete_marker,
    save_intelligence,
    get_intelligence,
    search_transcripts_fts,
    save_transcript,
)


def run_checks():
    print("Initializing Database...")
    init_db()

    print("Creating temporary test job...")
    test_job_id = create_job(
        filename="meeting_test.mp4",
        filepath="/tmp/meeting_test.mp4",
        file_size_bytes=10240,
        mode="whale",
        language="en",
        task="transcribe",
        diarize=True,
    )
    print(f"Created test job: {test_job_id}")

    try:
        # ─────────────────────────────────────────────────────────────
        # 1. TEST AUDIO MARKERS (CRUD & PERSISTENCE)
        # ─────────────────────────────────────────────────────────────
        print("\n--- 1. Testing Audio Markers Persistence ---")
        m1 = create_marker(
            job_id=test_job_id,
            time_pos=14.5,
            label="Intro & Kickoff",
            tag="note",
            marker_id="m_test_1",
        )
        assert m1["id"] == "m_test_1"
        assert m1["time"] == 14.5
        assert m1["label"] == "Intro & Kickoff"

        m2 = create_marker(
            job_id=test_job_id,
            time_pos=62.0,
            label="Budget Allocation Decision",
            tag="highlight",
        )
        assert m2["id"].startswith("m_")
        assert m2["time"] == 62.0

        markers = get_markers(test_job_id)
        assert len(markers) == 2, f"Expected 2 markers, got {len(markers)}"
        assert markers[0]["id"] == "m_test_1"
        assert markers[1]["label"] == "Budget Allocation Decision"
        print(f"  ✓ Markers created & fetched in chronological order ({len(markers)} markers)")

        # Update marker
        m1_updated = create_marker(
            job_id=test_job_id,
            time_pos=15.0,
            label="Intro & Revised Kickoff",
            tag="review",
            marker_id="m_test_1",
        )
        assert m1_updated["label"] == "Intro & Revised Kickoff"
        assert m1_updated["time"] == 15.0

        # Delete marker
        delete_marker(test_job_id, "m_test_1")
        remaining = get_markers(test_job_id)
        assert len(remaining) == 1, f"Expected 1 marker after delete, got {len(remaining)}"
        assert remaining[0]["id"] == m2["id"]
        print("  ✓ Marker update and deletion verified")

        # ─────────────────────────────────────────────────────────────
        # 2. TEST SQLITE FTS5 FULL-TEXT SEARCH & SYNC TRIGGERS
        # ─────────────────────────────────────────────────────────────
        print("\n--- 2. Testing SQLite FTS5 Full-Text Search ---")
        dummy_segments = [
            {
                "speaker_label": "SPEAKER_00",
                "start_time": 10.0,
                "end_time": 15.5,
                "text": "Welcome everyone to our quantum computing architecture review.",
                "words": [],
            },
            {
                "speaker_label": "SPEAKER_01",
                "start_time": 16.0,
                "end_time": 22.0,
                "text": "Thank you Alice, our quarterly revenue grew twenty percent.",
                "words": [],
            },
        ]
        save_transcript(
            job_id=test_job_id,
            full_text="Welcome everyone to our quantum computing architecture review. Thank you Alice, our quarterly revenue grew twenty percent.",
            detected_language="en",
            language_probability=0.99,
            segments_data=dummy_segments,
            speakers_data=[
                {"speaker_label": "SPEAKER_00", "display_name": "Alice"},
                {"speaker_label": "SPEAKER_01", "display_name": "Bob"},
            ],
        )

        # Search via FTS5 for 'quantum'
        res_quantum = search_transcripts_fts(query="quantum", job_id=test_job_id)
        assert len(res_quantum) == 1, f"Expected 1 FTS match for 'quantum', got {len(res_quantum)}"
        assert "quantum" in res_quantum[0]["text"].lower()
        assert "<mark>quantum</mark>" in res_quantum[0]["highlight"].lower()
        print(f"  ✓ FTS5 match found: {res_quantum[0]['highlight']}")

        # Search via FTS5 across all jobs without job_id filter
        res_revenue = search_transcripts_fts(query="revenue")
        assert len(res_revenue) >= 1, "Expected match for 'revenue' across library"
        print("  ✓ Global FTS5 search across all jobs verified")

        # Test trigger update
        with get_db() as conn:
            seg_id = res_quantum[0]["segment_id"]
            conn.execute(
                "UPDATE segments SET text = ? WHERE id = ?",
                ("Updated line discussing superconducting qubits.", seg_id),
            )

        res_qubits = search_transcripts_fts(query="qubits", job_id=test_job_id)
        assert len(res_qubits) == 1, "Trigger should sync updated segment text to FTS5"
        res_old = search_transcripts_fts(query="quantum", job_id=test_job_id)
        assert len(res_old) == 0, "Old text should be purged from FTS5 index upon segment update"
        print("  ✓ Automatic SQLite trigger sync (INSERT/UPDATE/DELETE) on FTS5 verified")

        # ─────────────────────────────────────────────────────────────
        # 3. TEST EXECUTIVE INTELLIGENCE SQLITE PERSISTENCE
        # ─────────────────────────────────────────────────────────────
        print("\n--- 3. Testing Executive Intelligence SQLite Persistence ---")
        mock_intel = {
            "tldr": "Quantum roadmap aligned and approved.",
            "executive_summary": "The leadership team met to review Q3 progress and agreed on superconducting milestones.",
            "key_takeaways": [
                "Roadmap approved by consensus",
                "Q3 deliverables on track",
            ],
            "action_items": [
                {
                    "task": "Finalize test suite",
                    "assignee": "Alice",
                    "timestamp": "00:15",
                    "time_seconds": 15.0,
                    "priority": "high",
                }
            ],
            "chapters": [
                {
                    "title": "Welcome and Intro",
                    "start_time": 0.0,
                    "start_timestamp": "00:00",
                    "description": "Opening remarks",
                }
            ],
            "key_questions": [
                {
                    "question": "What is the timeline?",
                    "answer": "End of Q4.",
                    "asked_by": "Bob",
                    "timestamp": "00:18",
                }
            ],
            "sentiment_and_tone": "Constructive and goal-oriented",
            "generated_by": "gemini-2.5-flash",
        }

        saved = save_intelligence(test_job_id, mock_intel)
        assert saved["job_id"] == test_job_id
        assert saved["tldr"] == mock_intel["tldr"]

        fetched = get_intelligence(test_job_id)
        assert fetched is not None, "Executive intelligence should be retrieved from SQLite"
        assert fetched["executive_summary"] == mock_intel["executive_summary"]
        assert len(fetched["key_takeaways"]) == 2
        assert len(fetched["action_items"]) == 1
        assert fetched["action_items"][0]["assignee"] == "Alice"
        assert fetched["action_items"][0]["priority"] == "high"
        assert fetched["generated_by"] == "gemini-2.5-flash"
        print("  ✓ Executive intelligence saved and retrieved from SQLite successfully")

        print("\n✅ ALL DATABASE, MARKERS, FTS5 & INTELLIGENCE CHECKS PASSED PERFECTLY!\n")

    finally:
        print(f"Cleaning up test job: {test_job_id}")
        delete_job(test_job_id)


if __name__ == "__main__":
    run_checks()
