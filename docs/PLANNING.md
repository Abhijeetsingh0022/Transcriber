# Development Master Plan

This document defines the phased implementation strategy, engineering milestones, technical dependencies, and risk mitigation roadmap for **Transcriber**.

---

## Roadmap Overview

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PHASE TIMELINE & GATES                                 │
├─────────┬────────────────────────────────────────────┬─────────────────────────────────┤
│ Phase   │ Focus Area                                 │ Exit Gate / Deliverable         │
├─────────┼────────────────────────────────────────────┼─────────────────────────────────┤
│ **0**   │ Environment & Hardware Abstraction (HAL)   │ PyTorch CUDA & MPS auto-detect  │
│ **1**   │ Audio Demuxing & Preprocessing Pipeline    │ 16kHz mono audio & VAD chunks   │
│ **2**   │ Core Speech-to-Text & Acoustic Translation │ Whisper Large-v3 golden output  │
│ **3**   │ Forced Alignment & Speaker Diarization     │ <30ms alignment & PyAnnote 3.1  │
│ **4**   │ SQLite Persistence & Queue State Machine   │ Crash-resilient batch worker    │
│ **5**   │ FastAPI Backend & Telemetry Stream (SSE)   │ Full REST & SSE test suite      │
│ **6**   │ Multi-Format Exporters (SRT/VTT/DOCX/ZIP)  │ Validated subtitle & doc export │
│ **7**   │ Web Dashboard & Batch Queue UI             │ Drag & drop 50+ files with SSE  │
│ **8**   │ Interactive Transcript Studio & Player     │ Karaoke sync & speaker rename   │
│ **9**   │ Dual-Platform Validation & Stress Testing  │ 8 GB VRAM budget & Mac testing  │
└─────────┴────────────────────────────────────────────┴─────────────────────────────────┘
```

---

## Phase 0: Environment & Hardware Abstraction Layer (HAL)

### Objective
Establish cross-platform foundations ensuring the application boots on both **NVIDIA RTX 2080 (CUDA 12.x)** and **Apple Silicon (M1–M4 / macOS)** with zero configuration changes.

### Deliverables
* `pyproject.toml` & `requirements.txt` / `requirements-cuda.txt`
* `engine/hardware.py`: Runtime inspection module returning device strings, compute types (`float16` vs `int8`), and memory limits.
* `setup.sh`: Automated installer script for both platforms.

### Verification Criteria
* Executing `python -c "import engine.hardware; print(engine.hardware.get_compute_backend())"`:
  * On RTX 2080: Returns `cuda`, `float16`, and verifies Tensor Core compatibility.
  * On Mac: Returns `mps`, `int8`, and verifies Apple Accelerate/NEON support.

---

## Phase 1: Audio Ingestion & Preprocessing Pipeline

### Objective
Ingest raw audio and multi-gigabyte video files, standardize them to 16 kHz 16-bit mono PCM, clean background noise, and eliminate silence blocks.

### Deliverables
* `engine/audio.py`: Streaming FFmpeg wrapper that drops video frames and extracts audio without loading entire video containers into RAM.
* `engine/enhancer.py`: DeepFilterNet v3 integration for neural noise suppression and room reverberation reduction.
* `engine/vad.py`: Silero VAD v5 implementation to filter silence and segment audio into speech turns.

### Verification Criteria
* Pass a 4K 2 GB `.mp4` video: Audio is demuxed in under 5 seconds.
* Audio with heavy fan/AC noise: DeepFilterNet strips ambient hum while maintaining clear voice formants.
* Audio with 30s silence gaps: Silero VAD accurately discards non-speech intervals.

---

## Phase 2: Core Speech-to-Text & Translation Engine

### Objective
Integrate OpenAI Whisper models via `faster-whisper` (CTranslate2) to match TurboScribe’s word accuracy and provide direct acoustic speech-to-English translation.

### Deliverables
* `engine/transcriber.py`: Wrapper supporting the 4 engine tiers:
  * `Whale`: Whisper Large-v3 (1.55B parameters, 128 Mel bins)
  * `Whale Turbo`: Whisper Large-v3-Turbo
  * `Dolphin`: Whisper Small (244M parameters)
  * `Cheetah`: Whisper Base (74M parameters)
* Integration of beam search (`beam_size=5`), temperature fallback array, and custom prompt injection.
* Direct zero-shot speech-to-English translation mode (`task="translate"`).

### Verification Criteria
* Word Error Rate (WER) on standard test audio matches TurboScribe Whale output.
* Spanish/German audio file transcribed with `task="translate"` outputs coherent English text in a single pass.

---

## Phase 3: Forced Alignment & Neural Diarization

### Objective
Eliminate Whisper timestamp drift (<30ms accuracy) and attribute words to distinct speakers using PyAnnote 3.1.

### Deliverables
* `engine/aligner.py`: WhisperX Wav2Vec2 CTC phoneme forced alignment module.
* `engine/diarizer.py`: PyAnnote 3.1 pipeline supporting auto-clustering and constrained speaker counts ($K = 2$ to $8$).
* `engine/fusion.py`: Temporal intersection algorithm mapping words to speaker intervals using majority overlap.

### Verification Criteria
* Word timestamps match audio waveform start/end points within 30ms.
* Two-person interview with overlapping dialogue accurately distinguishes `SPEAKER_00` from `SPEAKER_01`.

---

## Phase 4: Persistence, State Machine & Queue Manager

### Objective
Create a rock-solid, crash-resilient SQLite database and background queue worker that processes multi-file batches sequentially without running out of memory.

### Deliverables
* `db/database.py` & `db/models.py`: SQLite 3 schema with WAL mode (`jobs`, `transcripts`, `segments`, `words`, `speakers`).
* `db/crud.py`: Database operations and cascading deletion routines.
* `engine/worker.py`: Background consumer thread running sequentially through queued jobs.
* `api/events.py`: Pub-sub event broadcaster for live progress streaming.

### Verification Criteria
* Queue 10 files and force-kill the application process halfway through job 3. On relaunch, unfinished jobs are preserved and resume without data corruption.

---

## Phase 5: FastAPI Backend & Streaming Telemetry

### Objective
Build the REST API endpoints and Server-Sent Events (SSE) telemetry pipeline.

### Deliverables
* `api/routes.py`:
  * `POST /api/jobs/upload`: Multipart upload supporting 50+ files.
  * `POST /api/jobs/url`: YouTube link submission via `yt-dlp`.
  * `GET /api/jobs`: Paginated job listings.
  * `GET /api/system/status`: Real-time VRAM, RAM, and hardware telemetry.
* `api/editor_routes.py`: Endpoints for transcript retrieval, inline editing, speaker renaming, and HTTP 206 partial audio streaming.
* `main.py`: Application entry point with Uvicorn.

### Verification Criteria
* All endpoints return valid JSON and comply with the OpenAPI specification in [API.md](file:///Users/abby/Desktop/Transcriber/API.md).
* Audio streaming endpoint (`/api/jobs/{id}/media`) supports browser seeking via `Range` request headers.

---

## Phase 6: Multi-Format Exporters

### Objective
Generate clean, production-ready subtitle files, formal documents, and bulk ZIP packages.

### Deliverables
* `engine/exporters/subtitles.py`: Formatted `.srt` and `.vtt` serializers with sentence-aware line breaking and customizable CPL.
* `engine/exporters/documents.py`: Styled `.docx` (via `python-docx`), `.pdf`, `.txt`, and `.csv` exporters.
* `engine/exporters/bulk.py`: ZIP package generator bundling all formats across selected jobs.

### Verification Criteria
* Subtitle `.srt` files import cleanly into Premiere Pro and VLC without syntax errors.
* `.docx` file contains properly formatted speaker headings and readable paragraphs.

---

## Phase 7: Web Dashboard & Batch Queue UI

### Objective
Deliver a responsive dark-themed dashboard allowing users to configure presets, drop dozens of files, and monitor live progress.

### Deliverables
* `web/index.html`: Modern semantic HTML structure.
* `web/css/style.css`: Curated dark theme following design tokens from [UI_UX.md](file:///Users/abby/Desktop/Transcriber/UI_UX.md).
* `web/js/queue.js`: Drag-and-drop handler, configuration drawer controls, and live SSE progress listener.

### Verification Criteria
* Drag-and-drop handles 50+ files simultaneously without UI freezing.
* Multi-phase progress bars update in real time via SSE without HTTP polling.

---

## Phase 8: Interactive Transcript Studio & Player

### Objective
Provide an in-browser transcript editor with synchronized audio playback, click-to-seek, and bulk speaker renaming.

### Deliverables
* `web/editor.html`: Split-screen layout featuring media player and transcript stream.
* `web/js/player.js`: Synchronized playback engine with karaoke word-level highlighting and click-to-seek.
* `web/js/editor.js`: Inline text editing with debounced auto-save and bulk speaker rename modal.

### Verification Criteria
* Clicking any word jumps playback to that exact audio timestamp.
* Editing text or renaming speakers persists to SQLite and updates export previews immediately.

---

## Phase 9: Stress Testing, Benchmarking & Polish

### Objective
Verify stability under heavy production loads on both the RTX 2080 and Apple Silicon Mac.

### Deliverables
* `tests/stress_test.py`: Batch processor verifying memory consumption across 10+ long files.
* Performance benchmark report comparing local output against TurboScribe cloud output.

### Verification Criteria
* **RTX 2080 Stress Test:** VRAM remains under 6.5 GB at all times with 0 OOM crashes.
* **Mac Test:** Validated on Apple Silicon with Metal Performance Shaders and ARM NEON SIMD.
* **Accuracy:** Zero hallucination loops on audio files containing long periods of silence.
