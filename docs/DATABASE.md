# Database Schema & Persistence Design

**Transcriber** uses an embedded **SQLite 3** database located at `data/transcriber.db`. It provides complete zero-configuration local persistence, crash resilience, and ACID compliance.

---

## 1. Engine Configuration & PRAGMAs

On every database connection pool initialization, the following PRAGMAs are executed:

```sql
PRAGMA journal_mode = WAL;          -- Write-Ahead Logging for high concurrency
PRAGMA synchronous = NORMAL;         -- Balances speed and durability
PRAGMA foreign_keys = ON;            -- Enforces relational integrity
PRAGMA busy_timeout = 5000;          -- 5-second lock timeout for background worker
PRAGMA cache_size = -64000;          -- Allocates 64 MB of page cache
```

---

## 2. Entity Relationship Diagram (ERD)

```
┌─────────────────────────┐
│          jobs           │
├─────────────────────────┤
│ id (PK, UUID)           │
│ filename, filepath      │
│ status, progress        │
│ config parameters       │
└────────────┬────────────┘
             │ 1:1
             ▼
┌─────────────────────────┐       1:N       ┌─────────────────────────┐
│       transcripts       │────────────────►│        speakers         │
├─────────────────────────┤                 ├─────────────────────────┤
│ id (PK, UUID)           │                 │ id (PK, UUID)           │
│ job_id (FK)             │                 │ job_id (FK)             │
│ full_text               │                 │ speaker_label, name     │
└────────────┬────────────┘                 └─────────────────────────┘
             │ 1:N
             ▼
┌─────────────────────────┐       1:N       ┌─────────────────────────┐
│        segments         │────────────────►│          words          │
├─────────────────────────┤                 ├─────────────────────────┤
│ id (PK, UUID)           │                 │ id (PK, UUID)           │
│ transcript_id (FK)      │                 │ segment_id (FK)         │
│ speaker_id, text        │                 │ word, start, end        │
│ start_time, end_time    │                 │ confidence score        │
└─────────────────────────┘                 └─────────────────────────┘
```

---

## 3. Table Definitions (DDL)

### 3.1 `jobs` Table
Tracks queued media files, configuration parameters, and execution state.

```sql
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,                             -- UUID v4
    filename TEXT NOT NULL,                          -- e.g. "interview_raw.mp4"
    filepath TEXT NOT NULL,                          -- Local absolute path
    file_size_bytes INTEGER NOT NULL,               -- Size in bytes
    duration_seconds REAL DEFAULT 0.0,              -- Media duration in seconds
    
    -- Processing Configuration
    mode TEXT NOT NULL DEFAULT 'whale',              -- 'whale', 'whale_turbo', 'dolphin', 'cheetah'
    language TEXT DEFAULT 'auto',                    -- Language code ('auto', 'en', 'es', etc.)
    task TEXT NOT NULL DEFAULT 'transcribe',         -- 'transcribe' or 'translate'
    diarize BOOLEAN NOT NULL DEFAULT 0,              -- 1 = enable speaker recognition
    num_speakers INTEGER DEFAULT NULL,               -- NULL = auto-detect, 2-8 = fixed count
    restore_audio BOOLEAN NOT NULL DEFAULT 0,        -- 1 = enable DeepFilterNet noise removal
    initial_prompt TEXT DEFAULT NULL,                -- Custom vocabulary / context bias
    
    -- Execution State
    status TEXT NOT NULL DEFAULT 'queued',           -- 'queued', 'preprocessing', 'transcribing', 'aligning', 'diarizing', 'completed', 'failed', 'cancelled'
    progress REAL NOT NULL DEFAULT 0.0,              -- Float 0.0 to 100.0
    current_stage TEXT DEFAULT 'Queued in line',     -- Human-readable stage description
    error_message TEXT DEFAULT NULL,                 -- Stack trace or error message if failed
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP DEFAULT NULL,
    completed_at TIMESTAMP DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC);
```

### 3.2 `transcripts` Table
Top-level transcript container linked to a completed job.

```sql
CREATE TABLE IF NOT EXISTS transcripts (
    id TEXT PRIMARY KEY,                             -- UUID v4
    job_id TEXT NOT NULL UNIQUE,                     -- 1:1 relationship with jobs
    full_text TEXT NOT NULL,                         -- Aggregated plain-text transcript
    detected_language TEXT DEFAULT NULL,             -- Result of Whisper LID
    language_probability REAL DEFAULT NULL,          -- Model confidence in detected language
    word_count INTEGER DEFAULT 0,
    segment_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_transcripts_job_id ON transcripts(job_id);
```

### 3.3 `speakers` Table
Stores discovered and renamed speakers for a job.

```sql
CREATE TABLE IF NOT EXISTS speakers (
    id TEXT PRIMARY KEY,                             -- UUID v4
    job_id TEXT NOT NULL,
    speaker_label TEXT NOT NULL,                     -- e.g. "SPEAKER_00"
    display_name TEXT NOT NULL,                      -- e.g. "Dr. Jane Smith"
    color_hex TEXT NOT NULL DEFAULT '#3b82f6',       -- Color tag for UI highlighting
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    UNIQUE(job_id, speaker_label)
);

CREATE INDEX IF NOT EXISTS idx_speakers_job_id ON speakers(job_id);
```

### 3.4 `segments` Table
Sentence- and phrase-level chunks with temporal bounds.

```sql
CREATE TABLE IF NOT EXISTS segments (
    id TEXT PRIMARY KEY,                             -- UUID v4
    transcript_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    segment_index INTEGER NOT NULL,                  -- Sequential index (0, 1, 2...)
    speaker_label TEXT DEFAULT NULL,                 -- "SPEAKER_00" or NULL
    start_time REAL NOT NULL,                        -- Seconds (e.g. 14.52)
    end_time REAL NOT NULL,                          -- Seconds (e.g. 19.84)
    text TEXT NOT NULL,                              -- Utterance text content
    FOREIGN KEY(transcript_id) REFERENCES transcripts(id) ON DELETE CASCADE,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_segments_transcript_id ON segments(transcript_id);
CREATE INDEX IF NOT EXISTS idx_segments_time ON segments(job_id, start_time, end_time);
```

### 3.5 `words` Table
Phoneme-level aligned words for millisecond-accurate seek and karaoke playback.

```sql
CREATE TABLE IF NOT EXISTS words (
    id TEXT PRIMARY KEY,                             -- UUID v4
    segment_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    word_index INTEGER NOT NULL,
    word TEXT NOT NULL,                              -- Individual word string
    start_time REAL NOT NULL,                        -- Millisecond-accurate timestamp
    end_time REAL NOT NULL,
    confidence_score REAL DEFAULT 1.0,               -- Wav2Vec2 / Whisper token confidence
    speaker_label TEXT DEFAULT NULL,
    FOREIGN KEY(segment_id) REFERENCES segments(id) ON DELETE CASCADE,
    FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_words_segment_id ON words(segment_id);
CREATE INDEX IF NOT EXISTS idx_words_time ON words(job_id, start_time, end_time);
```

---

## 4. Job State Machine & Transitions

```
                    ┌────────────┐
                    │   QUEUED   │
                    └──────┬─────┘
                           │ (Worker picks up)
                           ▼
                 ┌───────────────────┐
                 │   PREPROCESSING   │  (FFmpeg Extraction & DeepFilterNet)
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │   TRANSCRIBING    │  (Whisper Large-v3 ASR)
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │     ALIGNING      │  (WhisperX Wav2Vec2)
                 └─────────┬─────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │     DIARIZING     │  (PyAnnote 3.1; if enabled)
                 └─────────┬─────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼ (Success)               ▼ (Error thrown)
       ┌─────────────┐           ┌────────────┐
       │  COMPLETED  │           │   FAILED   │
       └─────────────┘           └────────────┘
```

---

## 5. Data Cleanup & Retention Policies

1. **Extracted Audio Cache:** Intermediate 16 kHz `.wav` tracks are purged automatically after transcript creation unless the user checks "Retain Extracted Audio".
2. **Cascading Deletions:** Deleting a job from the UI automatically deletes its associated `transcripts`, `segments`, `words`, and `speakers` via SQLite's `ON DELETE CASCADE`.
3. **Database Maintenance:** An automatic `PRAGMA incremental_vacuum;` is executed on application startup to reclaim unallocated disk blocks.
