# Engineering Tasks & Implementation Roadmap

This checklist outlines the phased implementation plan for **Transcriber**. Each task contains specific deliverable files, implementation details, and verification criteria.

---

## Phase 1: Project Setup & Hardware Abstraction Layer (HAL)

- [x] **Task 1.1: Dependency & Project Scaffold**
  * **Deliverables:** `pyproject.toml`, `requirements.txt`, `setup.sh`
  * **Details:** Configure PyTorch (CUDA 12.1 for RTX / standard for Mac), `faster-whisper`, `fastapi`, `uvicorn`, `sqlite3`.
  * **Verification:** Run `python -c "import torch; print(torch.cuda.is_available())"` on both environments.

- [x] **Task 1.2: Hardware Detection Engine**
  * **Deliverables:** `engine/hardware.py`
  * **Details:** Implement `get_compute_backend()` to detect CUDA vs Apple Silicon MPS vs CPU, returning device pointers, compute type (`float16` vs `int8`), and memory limits.
  * **Verification:** Test on RTX 2080 returns `cuda`/`float16`; test on Mac returns `mps`/`int8`.

---

## Phase 2: Audio Extraction & Preprocessing Engine

- [x] **Task 2.1: FFmpeg Audio Stream Demuxer**
  * **Deliverables:** `engine/audio.py`
  * **Details:** Implement `extract_audio_stream(input_path, output_wav_path)` using streaming subprocesses with automatic PyAV fallback to extract 16 kHz 16-bit mono PCM from MP4, MOV, MKV, MP3, etc.
  * **Verification:** Extracted & resampled 44.1kHz stereo -> 16kHz mono verified.

---

## Phase 3: Core Transcription & Translation (Whisper Large-v3)

- [x] **Task 3.1: Faster-Whisper Model Wrapper**
  * **Deliverables:** `engine/transcriber.py`
  * **Details:** Implement `TranscriberModel` supporting `Whale` (Large-v3), `Whale Turbo` (Large-v3-Turbo), `Dolphin` (Small), and `Cheetah` (Base). Support beam search, temperature fallback, and initial prompt context.
  * **Verification:** Model loading, Silero VAD suppression, and token stream verified.

- [x] **Task 3.2: Direct Speech-to-English Acoustic Translation**
  * **Deliverables:** `engine/transcriber.py` (translation mode)
  * **Details:** Wire `task="translate"` to decode foreign audio directly into English text.
  * **Verification:** Single-pass acoustic translation pipeline configured.

---

## Phase 4: Forced Alignment & Diarization (WhisperX & PyAnnote)

- [x] **Task 4.1: Phoneme & Word Timestamp Alignment**
  * **Deliverables:** Word-level timestamps in `engine/transcriber.py`
  * **Details:** Generates millisecond-accurate word start/end bounds for karaoke playback.
  * **Verification:** Aligned words verified in `tests/self_check.py`.

- [x] **Task 4.2: Speaker Diarization & Attribution**
  * **Deliverables:** `engine/worker.py`
  * **Details:** Speaker labeling (`SPEAKER_00`, `SPEAKER_01`) with customizable speaker constraints (2–8).
  * **Verification:** Two-speaker attribution verified in database.

---

## Phase 5: Persistence & Database Architecture

- [x] **Task 5.1: SQLite Database Setup & Models**
  * **Deliverables:** `db/database.py`, `db/models.py`
  * **Details:** Initialize SQLite database with WAL mode. Create tables: `jobs`, `transcripts`, `segments`, `words`, `speakers`.
  * **Verification:** All 5 tables created and verified in `data/transcriber.db`.

- [x] **Task 5.2: Job State Machine & CRUD Operations**
  * **Deliverables:** `db/crud.py`
  * **Details:** Implement CRUD methods: create job, update progress, advance status, attach transcript, and cascade delete.
  * **Verification:** Unit test state transitions from `QUEUED` through `COMPLETED` verified.

---

## Phase 6: Background Queue Manager & Worker

- [x] **Task 6.1: Queue Worker Thread**
  * **Deliverables:** `engine/worker.py`
  * **Details:** Implement single-worker background thread pulling pending jobs from SQLite. Enforce graceful error handling and sequential processing.
  * **Verification:** Worker loop and job consumption tested.

- [x] **Task 6.2: Real-Time Event Dispatcher (SSE)**
  * **Deliverables:** `api/events.py`
  * **Details:** Implement pub-sub event bus broadcasting job progress, stage changes, and completion to connected SSE listeners.
  * **Verification:** Event dispatching verified.

---

## Phase 7: FastAPI Backend & Endpoints

- [x] **Task 7.1: Core REST Endpoints**
  * **Deliverables:** `api/routes.py`, `main.py`
  * **Details:** Implement `/api/jobs/upload`, `/api/jobs`, `/api/jobs/{id}`, `/api/system/status`.
  * **Verification:** Validated endpoints.

- [x] **Task 7.2: Transcript Editor Endpoints**
  * **Deliverables:** `api/routes.py`
  * **Details:** Implement `GET /api/jobs/{id}/transcript`, `PUT /api/jobs/{id}/segments/{id}`, `PATCH /api/jobs/{id}/speakers`, and `GET /api/jobs/{id}/media` with HTTP 206 range streaming.
  * **Verification:** Range streaming and transcript update routes verified.

---

## Phase 8: Multi-Format Export Engine

- [x] **Task 8.1: Subtitle Serializers**
  * **Deliverables:** `engine/exporters/subtitles.py`
  * **Details:** Implement `.srt` and `.vtt` generators with millisecond timecodes.
  * **Verification:** Tested in `tests/self_check.py`.

- [x] **Task 8.2: Document & Data Serializers**
  * **Deliverables:** `engine/exporters/documents.py`
  * **Details:** Implement `.docx`, `.txt`, `.csv`, and `.json` AST exporters.
  * **Verification:** Tested in `tests/self_check.py`.

---

## Phase 9: Web Dashboard & Interactive Editor (Next.js)

- [x] **Task 9.1: Queue Dashboard & Drag-and-Drop UI (Next.js)**
  * **Deliverables:** `web/app/page.tsx`, `web/app/globals.css`
  * **Details:** Light theme SaaS dashboard with Lucide icons, 4px-6px radii, multi-file dropzone, mode drawer, and live SSE progress.
  * **Verification:** `npm run build` compiled successfully (5/5 static pages).

- [x] **Task 9.2: Interactive Transcript Studio (Next.js)**
  * **Deliverables:** `web/app/studio/[jobId]/page.tsx`
  * **Details:** Media player with waveform scrubber, click-to-seek, karaoke word tracking, inline editing, and bulk speaker renamer modal.
  * **Verification:** `npm run build` compiled successfully with Suspense client prerendering.

---

## Phase 10: End-to-End Testing & Performance Benchmarking

- [ ] **Task 10.1: RTX 2080 CUDA Stress Test**
  * **Details:** Queue 10 long video files on the RTX 2080; monitor VRAM to ensure it remains below the 6.5 GB limit and verify 100% completion.
- [ ] **Task 10.2: Mac Apple Silicon Validation**
  * **Details:** Run identical queue on Mac; verify ARM NEON / MPS execution and transcript parity.
