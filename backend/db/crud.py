"""
CRUD (Create, Read, Update, Delete) database operations for Transcriber.
"""

import hashlib
import json
import re
import threading
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from db.database import get_db
from db.models import JobItem, JobStatus, TranscriptResponse, SpeakerItem, SegmentItem, WordItem

_SAFE_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")

# Thread-safe in-memory LRU cache for full transcript trees to eliminate repeated multi-table SELECT queries
_TRANSCRIPT_CACHE: OrderedDict = OrderedDict()
_TRANSCRIPT_CACHE_LOCK = threading.Lock()
_MAX_TRANSCRIPT_CACHE = 50

# 1-second TTL cache for count_jobs to eliminate high-frequency SQLite load from status polling
_COUNT_JOBS_CACHE: Dict[Optional[str], Any] = {}
_COUNT_JOBS_LOCK = threading.Lock()


def invalidate_transcript_cache(job_id: Optional[str] = None) -> None:
    """Invalidates in-memory transcript cache for a specific job_id, or completely if None."""
    with _TRANSCRIPT_CACHE_LOCK:
        if job_id:
            _TRANSCRIPT_CACHE.pop(job_id, None)
        else:
            _TRANSCRIPT_CACHE.clear()


def invalidate_count_jobs_cache() -> None:
    """Invalidates in-memory job count cache."""
    with _COUNT_JOBS_LOCK:
        _COUNT_JOBS_CACHE.clear()


def is_safe_id(val: Optional[str]) -> bool:
    """Validates that entity UUID / ID contains only safe alphanumeric characters."""
    return bool(val and _SAFE_ID_PATTERN.match(val))


def create_job(
    filename: str,
    filepath: str,
    file_size_bytes: int,
    mode: str = "whale",
    language: str = "auto",
    task: str = "transcribe",
    diarize: bool = False,
    num_speakers: Optional[int] = None,
    restore_audio: bool = False,
    initial_prompt: Optional[str] = None,
) -> str:
    """Inserts a new job into SQLite and returns its UUID."""
    job_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (
                id, filename, filepath, file_size_bytes, mode, language,
                task, diarize, num_speakers, restore_audio, initial_prompt,
                status, progress, current_stage, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0.0, 'Queued in line', CURRENT_TIMESTAMP)
            """,
            (
                job_id, filename, filepath, file_size_bytes, mode, language,
                task, 1 if diarize else 0, num_speakers, 1 if restore_audio else 0, initial_prompt
            ),
        )
    invalidate_count_jobs_cache()
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single job by UUID with strict path traversal / ID validation."""
    if not is_safe_id(job_id):
        return None
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_jobs(status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Lists jobs ordered by created_at DESC with optional status filter and transcript summary."""
    with get_db() as conn:
        query = """
            SELECT 
                jobs.*,
                transcripts.detected_language,
                transcripts.word_count,
                transcripts.segment_count,
                SUBSTR(transcripts.full_text, 1, 300) AS snippet_text
            FROM jobs
            LEFT JOIN transcripts ON jobs.id = transcripts.job_id
        """
        if status:
            cursor = conn.execute(
                query + " WHERE jobs.status = ? ORDER BY jobs.created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            )
        else:
            cursor = conn.execute(
                query + " ORDER BY jobs.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        return [dict(row) for row in cursor.fetchall()]


def get_jobs_state_hash(status: Optional[str] = None) -> str:
    """Computes a sub-millisecond hash of the current jobs table state for conditional HTTP caching."""
    with get_db() as conn:
        if status:
            cursor = conn.execute(
                "SELECT COUNT(*), MAX(created_at), MAX(COALESCE(completed_at, '')), TOTAL(progress), MAX(status) FROM jobs WHERE status = ?",
                (status,),
            )
        else:
            cursor = conn.execute(
                "SELECT COUNT(*), MAX(created_at), MAX(COALESCE(completed_at, '')), TOTAL(progress), MAX(status) FROM jobs"
            )
        row = cursor.fetchone()
        raw = f"{row[0]}:{row[1]}:{row[2]}:{row[3]}:{row[4]}:{status or 'all'}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def count_jobs(status: Optional[str] = None) -> int:
    """Counts total jobs matching filter with 1.0s TTL caching to avoid high-frequency polling load."""
    now = time.time()
    with _COUNT_JOBS_LOCK:
        if status in _COUNT_JOBS_CACHE:
            ts, val = _COUNT_JOBS_CACHE[status]
            if now - ts < 1.0:
                return val

    with get_db() as conn:
        if status:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs WHERE status = ?", (status,))
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM jobs")
        count_val = cursor.fetchone()[0]

    with _COUNT_JOBS_LOCK:
        _COUNT_JOBS_CACHE[status] = (now, count_val)

    return count_val


def update_job_progress(job_id: str, progress: float, stage: str):
    """Updates job progress percentage and human-readable stage message."""
    with get_db() as conn:
        conn.execute(
            "UPDATE jobs SET progress = ?, current_stage = ? WHERE id = ?",
            (progress, stage, job_id),
        )


def update_job_status(
    job_id: str,
    status: str,
    error_message: Optional[str] = None,
    duration_seconds: Optional[float] = None,
):
    """Updates job status and lifecycle timestamps."""
    if not is_safe_id(job_id):
        return
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        if status == "preprocessing":
            conn.execute(
                "UPDATE jobs SET status = ?, started_at = ? WHERE id = ?",
                (status, now, job_id),
            )
        elif status in ("completed", "failed", "cancelled"):
            if duration_seconds is not None:
                conn.execute(
                    "UPDATE jobs SET status = ?, error_message = ?, completed_at = ?, duration_seconds = ? WHERE id = ?",
                    (status, error_message, now, duration_seconds, job_id),
                )
            else:
                conn.execute(
                    "UPDATE jobs SET status = ?, error_message = ?, completed_at = ? WHERE id = ?",
                    (status, error_message, now, job_id),
                )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, job_id),
            )
    invalidate_count_jobs_cache()


def reset_job_for_retry(job_id: str):
    """Resets a failed/cancelled job for reprocessing: clears errors and sets status to queued."""
    with get_db() as conn:
        conn.execute(
            """
            UPDATE jobs
            SET status = 'queued',
                progress = 0.0,
                current_stage = 'Queued in line',
                error_message = NULL,
                started_at = NULL,
                completed_at = NULL
            WHERE id = ?
            """,
            (job_id,),
        )


def delete_job(job_id: str) -> bool:
    """Deletes job and cascades to transcripts, segments, words, and speakers."""
    if not is_safe_id(job_id):
        return False
    invalidate_transcript_cache(job_id)
    invalidate_count_jobs_cache()
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        return cursor.rowcount > 0


def delete_jobs(job_ids: List[str]) -> int:
    """Batch deletes multiple jobs and their cascaded records in a single atomic transaction."""
    safe_ids = [jid for jid in job_ids if is_safe_id(jid)]
    if not safe_ids:
        return 0
    invalidate_count_jobs_cache()
    for jid in safe_ids:
        invalidate_transcript_cache(jid)
    with get_db() as conn:
        placeholders = ",".join("?" for _ in safe_ids)
        cursor = conn.execute(f"DELETE FROM jobs WHERE id IN ({placeholders})", safe_ids)
        return cursor.rowcount


def save_transcript(
    job_id: str,
    full_text: str,
    detected_language: Optional[str],
    language_probability: Optional[float],
    segments_data: List[Dict[str, Any]],
    speakers_data: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Saves complete transcript hierarchy: transcript record, speakers, segments, and words.
    Cleans up any previous partial or retry transcripts to prevent UNIQUE constraint violations.
    """
    transcript_id = str(uuid.uuid4())
    word_count = sum(len(seg.get("words", [])) for seg in segments_data)
    segment_count = len(segments_data)

    with get_db() as conn:
        # Clean up any existing transcript or speakers for this job (e.g. from a retried run)
        conn.execute("DELETE FROM transcripts WHERE job_id = ?", (job_id,))
        conn.execute("DELETE FROM speakers WHERE job_id = ?", (job_id,))

        # 1. Insert transcript
        conn.execute(
            """
            INSERT INTO transcripts (
                id, job_id, full_text, detected_language,
                language_probability, word_count, segment_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcript_id, job_id, full_text, detected_language,
                language_probability, word_count, segment_count
            ),
        )

        # 2. Batch insert speakers
        if speakers_data:
            speaker_rows = [
                (
                    str(uuid.uuid4()),
                    job_id,
                    spk["speaker_label"],
                    spk.get("display_name", spk["speaker_label"]),
                    spk.get("color_hex", "#2563eb"),
                )
                for spk in speakers_data
            ]
            conn.executemany(
                """
                INSERT INTO speakers (id, job_id, speaker_label, display_name, color_hex)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(job_id, speaker_label) DO UPDATE SET
                    display_name = excluded.display_name,
                    color_hex = excluded.color_hex
                """,
                speaker_rows,
            )

        # 3. Batch insert segments & words in compiled batches (10-20x faster than single inserts)
        segment_rows = []
        word_rows = []
        for idx, seg in enumerate(segments_data):
            seg_id = str(uuid.uuid4())
            seg["id"] = seg_id
            segment_rows.append((
                seg_id, transcript_id, job_id, idx,
                seg.get("speaker_label"), seg.get("addressed_to"), seg.get("turn_intent"),
                seg["start_time"], seg["end_time"], seg["text"]
            ))

            for w_idx, w in enumerate(seg.get("words", [])):
                word_rows.append((
                    str(uuid.uuid4()), seg_id, job_id, w_idx,
                    w["word"], w["start_time"], w["end_time"],
                    w.get("confidence_score", 1.0), seg.get("speaker_label")
                ))

        if segment_rows:
            conn.executemany(
                """
                INSERT INTO segments (
                    id, transcript_id, job_id, segment_index,
                    speaker_label, addressed_to, turn_intent,
                    start_time, end_time, text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                segment_rows,
            )

        if word_rows:
            conn.executemany(
                """
                INSERT INTO words (
                    id, segment_id, job_id, word_index,
                    word, start_time, end_time, confidence_score, speaker_label
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                word_rows,
            )

        invalidate_transcript_cache(job_id)
        return transcript_id


def get_transcript(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full transcript tree with segments, words, and speakers with thread-safe in-memory LRU caching."""
    if not is_safe_id(job_id):
        return None

    with _TRANSCRIPT_CACHE_LOCK:
        if job_id in _TRANSCRIPT_CACHE:
            _TRANSCRIPT_CACHE.move_to_end(job_id)
            cached = _TRANSCRIPT_CACHE[job_id]
            return {
                **cached,
                "speakers": list(cached.get("speakers", [])),
                "segments": list(cached.get("segments", [])),
            }

    with get_db() as conn:
        t_cur = conn.execute("SELECT * FROM transcripts WHERE job_id = ?", (job_id,))
        t_row = t_cur.fetchone()
        if not t_row:
            return None

        transcript = dict(t_row)

        # Speakers
        spk_cur = conn.execute("SELECT * FROM speakers WHERE job_id = ?", (job_id,))
        transcript["speakers"] = [dict(s) for s in spk_cur.fetchall()]

        # Segments
        seg_cur = conn.execute(
            "SELECT * FROM segments WHERE job_id = ? ORDER BY segment_index ASC", (job_id,)
        )
        segments = [dict(s) for s in seg_cur.fetchall()]

        # Words fetched in a single query and mapped in-memory (O(N) vs O(N*segments))
        w_cur = conn.execute(
            "SELECT * FROM words WHERE job_id = ? ORDER BY word_index ASC", (job_id,)
        )
        words_by_segment: Dict[str, List[Dict[str, Any]]] = {}
        for w in w_cur:
            w_dict = dict(w)
            seg_id = w_dict["segment_id"]
            if seg_id not in words_by_segment:
                words_by_segment[seg_id] = []
            words_by_segment[seg_id].append(w_dict)

        for seg in segments:
            seg["words"] = words_by_segment.get(seg["id"], [])

        transcript["segments"] = segments

        with _TRANSCRIPT_CACHE_LOCK:
            if len(_TRANSCRIPT_CACHE) >= _MAX_TRANSCRIPT_CACHE:
                _TRANSCRIPT_CACHE.popitem(last=False)
            _TRANSCRIPT_CACHE[job_id] = transcript

        return {
            **transcript,
            "speakers": list(transcript.get("speakers", [])),
            "segments": list(transcript.get("segments", [])),
        }


def update_speakers(job_id: str, updates: List[Dict[str, str]]):
    """Updates or upserts display names and colors of speaker labels."""
    invalidate_transcript_cache(job_id)
    with get_db() as conn:
        for u in updates:
            spk_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO speakers (id, job_id, speaker_label, display_name, color_hex)
                VALUES (?, ?, ?, ?, COALESCE(?, '#2563eb'))
                ON CONFLICT(job_id, speaker_label) DO UPDATE SET
                    display_name = excluded.display_name,
                    color_hex = COALESCE(excluded.color_hex, speakers.color_hex)
                """,
                (spk_id, job_id, u["speaker_label"], u.get("display_name", u["speaker_label"]), u.get("color_hex")),
            )


def sync_segment_words(
    conn,
    segment_id: str,
    text: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    job_id: Optional[str] = None,
    speaker_label: Optional[str] = None,
) -> None:
    """
    Synchronizes word records for a segment to ensure 100% word timing & text alignment.
    - If word counts match: updates words 1-to-1, preserving exact acoustic timestamps.
    - If word counts differ: proportionally distributes timestamps across start/end interval.
    """
    existing_words = conn.execute(
        "SELECT id, start_time, end_time FROM words WHERE segment_id = ? ORDER BY word_index ASC",
        (segment_id,),
    ).fetchall()
    new_words = text.strip().split()

    if not new_words:
        conn.execute("DELETE FROM words WHERE segment_id = ?", (segment_id,))
        return

    if existing_words and len(existing_words) == len(new_words):
        # 1-to-1 word text alignment: preserve exact acoustic timestamps
        conn.executemany(
            "UPDATE words SET word = ? WHERE id = ?",
            [(w_text, ew["id"]) for w_text, ew in zip(new_words, existing_words)]
        )
    else:
        # Re-distribute words proportionally across the segment's start and end times
        if start_time is None or end_time is None or job_id is None:
            seg_time = conn.execute(
                "SELECT job_id, speaker_label, start_time, end_time FROM segments WHERE id = ?",
                (segment_id,)
            ).fetchone()
            if not seg_time:
                return
            s_start = seg_time["start_time"]
            s_end = seg_time["end_time"]
            j_id = seg_time["job_id"]
            spk = seg_time["speaker_label"]
        else:
            s_start = start_time
            s_end = end_time
            j_id = job_id
            spk = speaker_label

        s_dur = max(0.05, s_end - s_start)
        step = s_dur / len(new_words)
        conn.execute("DELETE FROM words WHERE segment_id = ?", (segment_id,))
        new_word_rows = [
            (
                str(uuid.uuid4()),
                segment_id,
                j_id,
                w_idx,
                w,
                round(s_start + (w_idx * step), 3),
                round(s_start + ((w_idx + 1) * step), 3),
                1.0,
                spk,
            )
            for w_idx, w in enumerate(new_words)
        ]
        conn.executemany(
            """
            INSERT INTO words (
                id, segment_id, job_id, word_index,
                word, start_time, end_time, confidence_score, speaker_label
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            new_word_rows,
        )


def update_transcript_segment(segment_id: str, text: str):
    """Updates text content of a specific segment, synchronizes word records, and keeps parent transcript full_text synchronized."""
    with get_db() as conn:
        conn.execute("UPDATE segments SET text = ? WHERE id = ?", (text, segment_id))
        sync_segment_words(conn, segment_id, text)

        row = conn.execute("SELECT job_id, transcript_id FROM segments WHERE id = ?", (segment_id,)).fetchone()
        if row:
            invalidate_transcript_cache(row["job_id"])
            transcript_id = row["transcript_id"]
            segs = conn.execute(
                "SELECT text FROM segments WHERE transcript_id = ? ORDER BY segment_index ASC",
                (transcript_id,),
            ).fetchall()
            new_full_text = " ".join(s["text"].strip() for s in segs if s["text"].strip())
            word_count = sum(len(s["text"].split()) for s in segs)
            conn.execute(
                """
                UPDATE transcripts
                SET full_text = ?, word_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (new_full_text, word_count, transcript_id),
            )


def update_segments_speaker(segment_ids: List[str], speaker_label: str):
    """Batch updates the speaker label of one or more segments."""
    if not segment_ids:
        return
    with get_db() as conn:
        row = conn.execute("SELECT job_id FROM segments WHERE id = ?", (segment_ids[0],)).fetchone()
        if row:
            invalidate_transcript_cache(row["job_id"])
        placeholders = ",".join("?" for _ in segment_ids)
        conn.execute(
            f"UPDATE segments SET speaker_label = ? WHERE id IN ({placeholders})",
            [speaker_label] + segment_ids,
        )
        conn.execute(
            f"UPDATE words SET speaker_label = ? WHERE segment_id IN ({placeholders})",
            [speaker_label] + segment_ids,
        )


def update_segments_addressee(segment_ids: List[str], addressed_to: str):
    """Batch updates the addressee (who is spoken to) of one or more segments."""
    if not segment_ids:
        return
    with get_db() as conn:
        row = conn.execute("SELECT job_id FROM segments WHERE id = ?", (segment_ids[0],)).fetchone()
        if row:
            invalidate_transcript_cache(row["job_id"])
        placeholders = ",".join("?" for _ in segment_ids)
        conn.execute(
            f"UPDATE segments SET addressed_to = ? WHERE id IN ({placeholders})",
            [addressed_to] + segment_ids,
        )


def recover_orphaned_jobs():
    """Resets any jobs interrupted by a server shutdown or restart back to queued."""
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE jobs
            SET status = 'queued',
                progress = 0.0,
                current_stage = 'Re-queued after server restart'
            WHERE status IN ('preprocessing', 'transcribing', 'aligning', 'diarizing')
            """
        )
        if cursor.rowcount > 0:
            print(f"Recovered {cursor.rowcount} orphaned in-flight jobs back to queued status.")

        mux_cursor = conn.execute(
            """
            UPDATE mux_jobs
            SET status = 'failed',
                error_message = 'Mux operation interrupted by server restart. Click Start Multi-Track Mux to restart.'
            WHERE status = 'processing'
            """
        )
        if mux_cursor.rowcount > 0:
            print(f"Recovered {mux_cursor.rowcount} orphaned in-flight mux jobs.")


# ---------------------------------------------------------------------------
# Mux Tracks CRUD
# ---------------------------------------------------------------------------

def insert_mux_track(
    job_id: str,
    label: str,
    filepath: str,
    language: str = "und",
    codec: str = "copy",
    bitrate: int = 192_000,
    channels: int = 2,
    sample_rate: int = 44100,
    disposition: str = "none",
    is_default: bool = False,
    gain: float = 1.0,
    is_muted: bool = False,
) -> Dict[str, Any]:
    """Appends a new audio track config row, auto-assigning the next track_index."""
    track_id = str(uuid.uuid4())
    with get_db() as conn:
        # Compute next available index atomically
        row = conn.execute(
            "SELECT COALESCE(MAX(track_index) + 1, 0) FROM mux_tracks WHERE job_id = ?", (job_id,)
        ).fetchone()
        track_index = row[0]

        if is_default:
            # Ensure only one default track per job
            conn.execute(
                "UPDATE mux_tracks SET is_default = 0 WHERE job_id = ?", (job_id,)
            )

        conn.execute(
            """
            INSERT INTO mux_tracks (
                id, job_id, track_index, label, language, filepath,
                codec, bitrate, channels, sample_rate, disposition, is_default, gain, is_muted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                track_id, job_id, track_index, label, language, filepath,
                codec, bitrate, channels, sample_rate, disposition, 1 if is_default else 0,
                float(gain), 1 if is_muted else 0,
            ),
        )
    return get_mux_track(track_id)


def get_mux_track(track_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single mux_tracks row by id."""
    if not is_safe_id(track_id):
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM mux_tracks WHERE id = ?", (track_id,)).fetchone()
        return dict(row) if row else None


def get_mux_tracks(job_id: str) -> List[Dict[str, Any]]:
    """Returns all tracks for a job, ordered by track_index."""
    if not is_safe_id(job_id):
        return []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM mux_tracks WHERE job_id = ? ORDER BY track_index ASC", (job_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_mux_track(track_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Partially updates a mux_tracks row from a dict of column=value pairs.
    If is_default=True is set, clears the flag on all sibling tracks first.
    """
    if not is_safe_id(track_id):
        return None
    if not updates:
        return get_mux_track(track_id)

    allowed = {
        "label", "language", "codec", "bitrate", "channels",
        "sample_rate", "disposition", "is_default", "gain", "is_muted"
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    if not safe:
        return get_mux_track(track_id)

    with get_db() as conn:
        if safe.get("is_default"):
            # Fetch job_id for the sibling-clear query
            row = conn.execute("SELECT job_id FROM mux_tracks WHERE id = ?", (track_id,)).fetchone()
            if row:
                conn.execute(
                    "UPDATE mux_tracks SET is_default = 0 WHERE job_id = ?", (row["job_id"],)
                )

        set_clause = ", ".join(f"{k} = ?" for k in safe)
        values = list(safe.values()) + [track_id]
        conn.execute(f"UPDATE mux_tracks SET {set_clause} WHERE id = ?", values)

    return get_mux_track(track_id)


def delete_mux_track(track_id: str) -> bool:
    """Removes a mux_tracks row. Caller is responsible for deleting the file from disk."""
    if not is_safe_id(track_id):
        return False
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM mux_tracks WHERE id = ?", (track_id,))
        return cursor.rowcount > 0


def reorder_mux_tracks(job_id: str) -> None:
    """Re-normalises track_index to be 0-based after a deletion to close gaps."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id FROM mux_tracks WHERE job_id = ? ORDER BY track_index ASC", (job_id,)
        ).fetchall()
        for new_idx, row in enumerate(rows):
            conn.execute(
                "UPDATE mux_tracks SET track_index = ? WHERE id = ?", (new_idx, row["id"])
            )


def swap_mux_track_indices(job_id: str, track_id_1: str, track_id_2: str) -> None:
    """Safely swaps the track_index of two tracks in a single transaction, avoiding UNIQUE collision."""
    with get_db() as conn:
        t1 = conn.execute("SELECT track_index FROM mux_tracks WHERE id = ? AND job_id = ?", (track_id_1, job_id)).fetchone()
        t2 = conn.execute("SELECT track_index FROM mux_tracks WHERE id = ? AND job_id = ?", (track_id_2, job_id)).fetchone()
        if not t1 or not t2:
            return
        idx1, idx2 = t1["track_index"], t2["track_index"]
        conn.execute("UPDATE mux_tracks SET track_index = -999 WHERE id = ?", (track_id_1,))
        conn.execute("UPDATE mux_tracks SET track_index = ? WHERE id = ?", (idx1, track_id_2))
        conn.execute("UPDATE mux_tracks SET track_index = ? WHERE id = ?", (idx2, track_id_1))


def reorder_mux_tracks_list(job_id: str, track_ids: List[str]) -> None:
    """Sets track_index in the exact order of track_ids, avoiding UNIQUE(job_id, track_index) collisions."""
    with get_db() as conn:
        for idx, tid in enumerate(track_ids):
            conn.execute(
                "UPDATE mux_tracks SET track_index = ? WHERE id = ? AND job_id = ?",
                (-(idx + 1000), tid, job_id)
            )
        for idx, tid in enumerate(track_ids):
            conn.execute(
                "UPDATE mux_tracks SET track_index = ? WHERE id = ? AND job_id = ?",
                (idx, tid, job_id)
            )


# ---------------------------------------------------------------------------
# Mux Jobs CRUD
# ---------------------------------------------------------------------------

def upsert_mux_job(
    job_id: str,
    status: str = "pending",
    output_path: Optional[str] = None,
    output_format: str = "mp4",
    error_message: Optional[str] = None,
    custom_video_path: Optional[str] = None,
    mux_mode: str = "tracks",
    mute_all_audio: bool = False,
) -> Dict[str, Any]:
    """Inserts or replaces the mux operation record for a job."""
    if not is_safe_id(job_id):
        return {}
    mux_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    completed_at = now if status in ("completed", "failed") else None

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO mux_jobs (
                id, job_id, output_path, output_format, status,
                error_message, custom_video_path, mux_mode, mute_all_audio, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status            = excluded.status,
                output_path       = COALESCE(excluded.output_path, mux_jobs.output_path),
                output_format     = excluded.output_format,
                error_message     = excluded.error_message,
                custom_video_path = COALESCE(excluded.custom_video_path, mux_jobs.custom_video_path),
                mux_mode          = excluded.mux_mode,
                mute_all_audio    = excluded.mute_all_audio,
                completed_at      = excluded.completed_at
            """,
            (
                mux_id, job_id, output_path, output_format, status,
                error_message, custom_video_path, mux_mode, 1 if mute_all_audio else 0, completed_at
            ),
        )

    return get_mux_job(job_id)


def get_mux_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Returns the mux_jobs row for a given job_id."""
    if not is_safe_id(job_id):
        return None
    with get_db() as conn:
        row = conn.execute("SELECT * FROM mux_jobs WHERE job_id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Markers CRUD
# ---------------------------------------------------------------------------

def get_markers(job_id: str) -> List[Dict[str, Any]]:
    """Returns all markers for a job ordered by time."""
    if not is_safe_id(job_id):
        return []
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, job_id, time, label, tag, created_at FROM markers WHERE job_id = ? ORDER BY time ASC",
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_marker(
    job_id: str,
    time_pos: float,
    label: str,
    tag: str = "note",
    marker_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Creates or updates a persistent marker/pin."""
    m_id = marker_id or f"m_{int(time.time() * 1000)}"
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO markers (id, job_id, time, label, tag)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                time = excluded.time,
                label = excluded.label,
                tag = excluded.tag
            """,
            (m_id, job_id, float(time_pos), label.strip(), tag.strip()),
        )
    return {
        "id": m_id,
        "job_id": job_id,
        "time": float(time_pos),
        "label": label.strip(),
        "tag": tag.strip(),
    }


def delete_marker(job_id: str, marker_id: str) -> bool:
    """Removes a marker by id."""
    with get_db() as conn:
        cursor = conn.execute(
            "DELETE FROM markers WHERE id = ? AND job_id = ?",
            (marker_id, job_id),
        )
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Intelligence CRUD
# ---------------------------------------------------------------------------

def save_intelligence(job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Persists structured executive intelligence report into SQLite."""
    if not is_safe_id(job_id):
        return {}
    now = datetime.now(timezone.utc).isoformat()
    tldr = data.get("tldr", "")
    summary = data.get("executive_summary", "")
    takeaways = json.dumps(data.get("key_takeaways", []), ensure_ascii=False)
    actions = json.dumps(data.get("action_items", []), ensure_ascii=False)
    chapters = json.dumps(data.get("chapters", []), ensure_ascii=False)
    questions = json.dumps(data.get("key_questions", []), ensure_ascii=False)
    sentiment = data.get("sentiment_and_tone", "")
    gen_by = data.get("generated_by", "Transcriber AI")

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO intelligence (
                job_id, tldr, executive_summary, key_takeaways, action_items,
                chapters, key_questions, sentiment_and_tone, generated_by, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                tldr = excluded.tldr,
                executive_summary = excluded.executive_summary,
                key_takeaways = excluded.key_takeaways,
                action_items = excluded.action_items,
                chapters = excluded.chapters,
                key_questions = excluded.key_questions,
                sentiment_and_tone = excluded.sentiment_and_tone,
                generated_by = excluded.generated_by,
                updated_at = excluded.updated_at
            """,
            (job_id, tldr, summary, takeaways, actions, chapters, questions, sentiment, gen_by, now),
        )
    res = dict(data)
    res["job_id"] = job_id
    return res


def get_intelligence(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves structured executive intelligence from SQLite."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM intelligence WHERE job_id = ?",
            (job_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return {
            "job_id": d["job_id"],
            "tldr": d["tldr"],
            "executive_summary": d["executive_summary"],
            "key_takeaways": json.loads(d["key_takeaways"] or "[]"),
            "action_items": json.loads(d["action_items"] or "[]"),
            "chapters": json.loads(d["chapters"] or "[]"),
            "key_questions": json.loads(d["key_questions"] or "[]"),
            "sentiment_and_tone": d["sentiment_and_tone"],
            "generated_by": d["generated_by"],
            "created_at": d["created_at"],
            "updated_at": d["updated_at"],
        }


# ---------------------------------------------------------------------------
# FTS5 Full-Text Search
# ---------------------------------------------------------------------------

def search_transcripts_fts(
    query: str,
    job_id: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Sub-millisecond full-text search across transcript speech using SQLite FTS5.
    Returns matched segments with BM25 relevance ranking and HTML highlighted snippets.
    """
    clean = query.strip().replace('"', '""')
    if not clean:
        return []

    # Clean FTS5 tokens: remove characters that might cause syntax errors
    terms = [re.sub(r'[^a-zA-Z0-9_\-\u0080-\uffff]', '', t) for t in clean.split()]
    terms = [t for t in terms if t]
    if not terms:
        return []

    # Prefix match on the last word for search-as-you-type
    fts_expr = " ".join([f'"{t}"' for t in terms[:-1]] + [f'"{terms[-1]}"*'])

    with get_db() as conn:
        cursor = conn.cursor()
        try:
            if job_id:
                sql = """
                SELECT 
                    fts.segment_id,
                    fts.job_id,
                    fts.speaker_label,
                    s.start_time,
                    s.end_time,
                    s.segment_index,
                    s.text,
                    s.text as full_text,
                    snippet(transcript_fts, 3, '<mark>', '</mark>', '...', 16) as snippet,
                    snippet(transcript_fts, 3, '<mark>', '</mark>', '...', 16) as highlight,
                    bm25(transcript_fts) as rank
                FROM transcript_fts fts
                JOIN segments s ON s.id = fts.segment_id
                WHERE transcript_fts MATCH ? AND fts.job_id = ?
                ORDER BY rank ASC
                LIMIT ?;
                """
                cursor.execute(sql, (fts_expr, job_id, limit))
            else:
                sql = """
                SELECT 
                    fts.segment_id,
                    fts.job_id,
                    fts.speaker_label,
                    s.start_time,
                    s.end_time,
                    s.segment_index,
                    s.text,
                    s.text as full_text,
                    snippet(transcript_fts, 3, '<mark>', '</mark>', '...', 16) as snippet,
                    snippet(transcript_fts, 3, '<mark>', '</mark>', '...', 16) as highlight,
                    bm25(transcript_fts) as rank,
                    j.filename as job_filename
                FROM transcript_fts fts
                JOIN segments s ON s.id = fts.segment_id
                JOIN jobs j ON j.id = fts.job_id
                WHERE transcript_fts MATCH ?
                ORDER BY rank ASC
                LIMIT ?;
                """
                cursor.execute(sql, (fts_expr, limit))
            return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []
