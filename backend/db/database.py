"""
SQLite Database Connection and Initialization with WAL mode and ACID persistence.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# Data directory lives inside backend/ or can be overridden via DATA_DIR env var
_custom_data_dir = os.environ.get("DATA_DIR")
DATA_DIR = Path(_custom_data_dir).resolve() if _custom_data_dir else Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "transcriber.db"


def ensure_data_directories():
    """Ensure data/, media/, and outputs/ directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "media").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "outputs").mkdir(parents=True, exist_ok=True)


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and configures a new SQLite connection with fast pragmas, foreign keys, and WAL auto-checkpoint.
    """
    ensure_data_directories()
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    
    # Fast per-connection SQLite PRAGMAs
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 10000;")      # 10s timeout prevents database lock errors during concurrency
    conn.execute("PRAGMA cache_size = -64000;")       # 64 MB page cache
    conn.execute("PRAGMA temp_store = MEMORY;")        # In-memory temporary tables & sorts
    conn.execute("PRAGMA mmap_size = 268435456;")      # 256 MB memory-mapped I/O
    conn.execute("PRAGMA wal_autocheckpoint = 1000;")  # Auto-checkpoint every 1,000 pages (~4 MB)
    
    return conn


@contextmanager
def get_db():
    """Context manager for safe transactional database sessions."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initializes tables and indexes defined in DATABASE.md."""
    ensure_data_directories()
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Ensure persistent database-level journal mode
        cursor.execute("PRAGMA journal_mode = WAL;")
        
        # 1. Jobs Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL,
            file_size_bytes INTEGER NOT NULL,
            duration_seconds REAL DEFAULT 0.0,
            
            mode TEXT NOT NULL DEFAULT 'whale',
            language TEXT DEFAULT 'auto',
            task TEXT NOT NULL DEFAULT 'transcribe',
            diarize BOOLEAN NOT NULL DEFAULT 0,
            num_speakers INTEGER DEFAULT NULL,
            restore_audio BOOLEAN NOT NULL DEFAULT 0,
            initial_prompt TEXT DEFAULT NULL,
            
            status TEXT NOT NULL DEFAULT 'queued',
            progress REAL NOT NULL DEFAULT 0.0,
            current_stage TEXT DEFAULT 'Queued in line',
            error_message TEXT DEFAULT NULL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP DEFAULT NULL,
            completed_at TIMESTAMP DEFAULT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_created ON jobs(status, created_at DESC);")

        # 2. Transcripts Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL UNIQUE,
            full_text TEXT NOT NULL,
            detected_language TEXT DEFAULT NULL,
            language_probability REAL DEFAULT NULL,
            word_count INTEGER DEFAULT 0,
            segment_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_job_id ON transcripts(job_id);")

        # 3. Speakers Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS speakers (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            speaker_label TEXT NOT NULL,
            display_name TEXT NOT NULL,
            color_hex TEXT NOT NULL DEFAULT '#2563eb',
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(job_id, speaker_label)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_speakers_job_id ON speakers(job_id);")

        # 4. Segments Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS segments (
            id TEXT PRIMARY KEY,
            transcript_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            segment_index INTEGER NOT NULL,
            speaker_label TEXT DEFAULT NULL,
            addressed_to TEXT DEFAULT NULL,
            turn_intent TEXT DEFAULT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_segments_transcript_id ON segments(transcript_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_segments_transcript_index ON segments(transcript_id, segment_index ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_segments_job_index ON segments(job_id, segment_index ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_segments_time ON segments(job_id, start_time, end_time);")

        # Safe schema migration for existing databases
        cursor.execute("PRAGMA table_info(segments);")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        if "addressed_to" not in existing_cols:
            cursor.execute("ALTER TABLE segments ADD COLUMN addressed_to TEXT DEFAULT NULL;")
        if "turn_intent" not in existing_cols:
            cursor.execute("ALTER TABLE segments ADD COLUMN turn_intent TEXT DEFAULT NULL;")

        # 5. Words Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id TEXT PRIMARY KEY,
            segment_id TEXT NOT NULL,
            job_id TEXT NOT NULL,
            word_index INTEGER NOT NULL,
            word TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            confidence_score REAL DEFAULT 1.0,
            speaker_label TEXT DEFAULT NULL,
            FOREIGN KEY(segment_id) REFERENCES segments(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_segment_id ON words(segment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_segment_index ON words(segment_id, word_index ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_job_index ON words(job_id, word_index ASC);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_time ON words(job_id, start_time, end_time);")

        # 6. Mux Tracks Table — stores per-track audio configuration for multi-audio muxing
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mux_tracks (
            id          TEXT PRIMARY KEY,
            job_id      TEXT NOT NULL,
            track_index INTEGER NOT NULL,
            label       TEXT NOT NULL,
            language    TEXT NOT NULL DEFAULT 'und',
            filepath    TEXT NOT NULL,
            codec       TEXT NOT NULL DEFAULT 'copy',
            bitrate     INTEGER NOT NULL DEFAULT 192000,
            channels    INTEGER NOT NULL DEFAULT 2,
            sample_rate INTEGER NOT NULL DEFAULT 44100,
            disposition TEXT NOT NULL DEFAULT 'none',
            is_default  BOOLEAN NOT NULL DEFAULT 0,
            gain        REAL NOT NULL DEFAULT 1.0,
            is_muted    BOOLEAN NOT NULL DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
            UNIQUE(job_id, track_index)
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mux_tracks_job_id ON mux_tracks(job_id);")

        # Migrations for mux_tracks
        for col, col_def in [
            ("gain", "REAL NOT NULL DEFAULT 1.0"),
            ("is_muted", "BOOLEAN NOT NULL DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE mux_tracks ADD COLUMN {col} {col_def};")
            except sqlite3.OperationalError:
                pass

        # 7. Mux Jobs Table — tracks the status of each mux operation
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mux_jobs (
            id                TEXT PRIMARY KEY,
            job_id            TEXT NOT NULL UNIQUE,
            output_path       TEXT DEFAULT NULL,
            output_format     TEXT NOT NULL DEFAULT 'mp4',
            status            TEXT NOT NULL DEFAULT 'pending',
            error_message     TEXT DEFAULT NULL,
            custom_video_path TEXT DEFAULT NULL,
            mux_mode          TEXT NOT NULL DEFAULT 'tracks',
            mute_all_audio    BOOLEAN NOT NULL DEFAULT 0,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at      TIMESTAMP DEFAULT NULL,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mux_jobs_job_id ON mux_jobs(job_id);")

        # Migrations for mux_jobs
        for col, col_def in [
            ("custom_video_path", "TEXT DEFAULT NULL"),
            ("mux_mode", "TEXT NOT NULL DEFAULT 'tracks'"),
            ("mute_all_audio", "BOOLEAN NOT NULL DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE mux_jobs ADD COLUMN {col} {col_def};")
            except sqlite3.OperationalError:
                pass

        # 8. App Settings Table — stores user preferences, API keys, and model paths
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 9. Markers Table — persistent timestamps bookmarks and pin notes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS markers (
            id         TEXT PRIMARY KEY,
            job_id     TEXT NOT NULL,
            time       REAL NOT NULL,
            label      TEXT NOT NULL,
            tag        TEXT NOT NULL DEFAULT 'note',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_markers_job_id ON markers(job_id, time ASC);")

        # 10. Executive Intelligence Table — structured AI briefings and action items
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence (
            job_id             TEXT PRIMARY KEY,
            tldr               TEXT,
            executive_summary  TEXT,
            key_takeaways      TEXT,
            action_items       TEXT,
            chapters           TEXT,
            key_questions      TEXT,
            sentiment_and_tone TEXT,
            generated_by       TEXT,
            created_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_intelligence_job_id ON intelligence(job_id);")

        # 11. Full-Text Search (FTS5) Virtual Table for sub-millisecond search across transcripts
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS transcript_fts USING fts5(
            segment_id UNINDEXED,
            job_id UNINDEXED,
            speaker_label UNINDEXED,
            text,
            tokenize = 'unicode61'
        );
        """)

        # Triggers to keep FTS5 synchronized with segments table on insert, delete, and update
        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_segments_fts_insert AFTER INSERT ON segments BEGIN
            INSERT INTO transcript_fts(segment_id, job_id, speaker_label, text)
            VALUES (new.id, new.job_id, coalesce(new.speaker_label, ''), new.text);
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_segments_fts_delete AFTER DELETE ON segments BEGIN
            DELETE FROM transcript_fts WHERE segment_id = old.id;
        END;
        """)

        cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_segments_fts_update AFTER UPDATE OF text, speaker_label ON segments BEGIN
            DELETE FROM transcript_fts WHERE segment_id = old.id;
            INSERT INTO transcript_fts(segment_id, job_id, speaker_label, text)
            VALUES (new.id, new.job_id, coalesce(new.speaker_label, ''), new.text);
        END;
        """)

        # Initial backfill if transcript_fts is empty but segments has data
        try:
            cursor.execute("SELECT count(*) FROM transcript_fts;")
            fts_count = cursor.fetchone()[0]
            if fts_count == 0:
                cursor.execute("""
                INSERT INTO transcript_fts(segment_id, job_id, speaker_label, text)
                SELECT id, job_id, coalesce(speaker_label, ''), text FROM segments;
                """)
        except Exception:
            pass


def wal_checkpoint(mode: str = "TRUNCATE") -> dict:
    """
    Forces a WAL checkpoint back into the database file.
    Modes:
        - PASSIVE: Checkpoints as many frames as possible without blocking.
        - FULL: Waits for active readers/writers to finish, then checkpoints all frames.
        - RESTART: Same as FULL, plus resets the WAL file.
        - TRUNCATE: Same as RESTART, and truncates the WAL file to zero bytes.
    """
    mode_upper = mode.upper()
    if mode_upper not in ("PASSIVE", "FULL", "RESTART", "TRUNCATE"):
        mode_upper = "TRUNCATE"
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA wal_checkpoint({mode_upper});")
        row = cursor.fetchone()
        busy = row[0] if row else 0
        log_frames = row[1] if row else 0
        checkpointed = row[2] if row else 0
        return {
            "status": "ok" if busy == 0 else "busy",
            "mode": mode_upper,
            "busy": busy,
            "log_frames": log_frames,
            "checkpointed_frames": checkpointed,
        }


def vacuum_db(incremental: bool = False, pages: int = 1000) -> dict:
    """
    Reclaims unused disk space and defragments SQLite pages.
    If incremental=True, runs PRAGMA incremental_vacuum(N) without long-held exclusive locks.
    If incremental=False, runs full VACUUM.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        if incremental:
            cursor.execute(f"PRAGMA incremental_vacuum({pages});")
            mode = f"incremental ({pages} pages)"
        else:
            cursor.execute("VACUUM;")
            mode = "full"

    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    return {
        "status": "ok",
        "vacuum_mode": mode,
        "db_size_bytes": db_size,
        "db_size_mb": round(db_size / (1024 * 1024), 2),
    }


def optimize_db() -> dict:
    """
    Runs SQLite PRAGMA optimize; to update query planner statistics.
    Recommended to run periodically and before application shutdown.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA optimize;")
        return {"status": "ok"}


def get_db_stats() -> dict:
    """
    Returns comprehensive SQLite health metrics, file sizes, page allocation, and table statistics.
    """
    ensure_data_directories()
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    wal_path = DB_PATH.parent / f"{DB_PATH.name}-wal"
    shm_path = DB_PATH.parent / f"{DB_PATH.name}-shm"
    wal_size = wal_path.stat().st_size if wal_path.exists() else 0
    shm_size = shm_path.stat().st_size if shm_path.exists() else 0

    table_counts = {}
    with get_db() as conn:
        cursor = conn.cursor()

        # Integrity
        cursor.execute("PRAGMA integrity_check;")
        integrity_rows = [r[0] for r in cursor.fetchall()]
        is_healthy = len(integrity_rows) == 1 and integrity_rows[0] == "ok"

        # Pragmas
        page_size = cursor.execute("PRAGMA page_size;").fetchone()[0]
        page_count = cursor.execute("PRAGMA page_count;").fetchone()[0]
        freelist_count = cursor.execute("PRAGMA freelist_count;").fetchone()[0]
        journal_mode = cursor.execute("PRAGMA journal_mode;").fetchone()[0]
        auto_vacuum = cursor.execute("PRAGMA auto_vacuum;").fetchone()[0]

        # Tables and rows
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
        tables = [r[0] for r in cursor.fetchall()]
        for t in tables:
            try:
                count_row = cursor.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()
                table_counts[t] = count_row[0] if count_row else 0
            except Exception:
                table_counts[t] = -1

    return {
        "status": "healthy" if is_healthy else "degraded",
        "integrity_check": integrity_rows,
        "db_path": str(DB_PATH),
        "db_size_bytes": db_size,
        "db_size_mb": round(db_size / (1024 * 1024), 2),
        "wal_size_bytes": wal_size,
        "wal_size_mb": round(wal_size / (1024 * 1024), 2),
        "shm_size_bytes": shm_size,
        "page_size": page_size,
        "total_pages": page_count,
        "freelist_pages": freelist_count,
        "reclaimable_mb": round((freelist_count * page_size) / (1024 * 1024), 2),
        "journal_mode": journal_mode,
        "auto_vacuum": auto_vacuum,
        "tables": table_counts,
    }


if __name__ == "__main__":
    init_db()
    print(f"Database initialized successfully at: {DB_PATH}")
    stats = get_db_stats()
    print(f"Database stats: {stats}")
