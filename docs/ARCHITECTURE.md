# Architecture & System Design

This document details the internal architecture, component interactions, hardware execution strategies, and memory budgets of **Transcriber**.

---

## 1. High-Level Architecture

Transcriber follows a decoupled, single-node architecture optimized for high-throughput batch media processing without cloud dependencies.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   PRESENTATION LAYER                                   │
│            Web Dashboard (HTML5, Vanilla CSS, Modern ES6 JavaScript)                   │
│   • Multi-file Drag & Drop Zone   • Live Queue Monitor (SSE)   • Transcript Editor     │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ HTTP REST / SSE Stream
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                   APPLICATION LAYER                                    │
│                         FastAPI Server (Asynchronous ASGI)                             │
│   • Route Handlers (`/api/jobs`, `/api/export`)   • SSE Event Dispatcher               │
└─────────────────────┬───────────────────────────────────────────┬──────────────────────┘
                      │                                           │
                      ▼                                           ▼
┌────────────────────────────────────────┐     ┌─────────────────────────────────────────┐
│           DATA PERSISTENCE             │     │             QUEUE DISPATCHER            │
│       SQLite 3 (`transcriber.db`)      │     │         Single-Worker Consumer          │
│   • Jobs State Table                   │◄────┤   • Sequentially pulls pending jobs     │
│   • Transcript AST Storage             │     │   • Dispatches to Execution Engine      │
└────────────────────────────────────────┘     └──────────────────┬──────────────────────┘
                                                                  │
                                                                  ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              LOCAL INFERENCE ENGINE (PIPELINE)                         │
│                                                                                        │
│   [1. Ingestion]       FFmpeg Stream Demuxer (Extracts 16kHz Mono PCM)                 │
│         │                                                                              │
│         ▼                                                                              │
│   [2. Vocal Filter]    DeepFilterNet v3 (Optional Noise & Reverb Suppression)          │
│         │                                                                              │
│         ▼                                                                              │
│   [3. VAD Slicing]     Silero VAD v5 (Splits into Speech Segments; Filters Silence)    │
│         │                                                                              │
│         ▼                                                                              │
│   [4. ASR Inference]   `faster-whisper` (Whisper Large-v3 / Large-v3-Turbo)            │
│         │                                                                              │
│         ▼                                                                              │
│   [5. Alignment]       WhisperX (Wav2Vec2 Phoneme Forced Alignment)                    │
│         │                                                                              │
│         ▼                                                                              │
│   [6. Diarization]     PyAnnote Audio 3.1 (Speaker Embedding & Clustering)             │
│         │                                                                              │
│         ▼                                                                              │
│   [7. Fusion & AST]    Correlates word timestamps with speaker intervals               │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hardware Abstraction Layer (HAL)

To run seamlessly across both **NVIDIA RTX 2080** and **Apple Silicon Macs**, the system abstracts hardware execution via `engine/hardware.py`:

```
                           [get_compute_backend()]
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
     [torch.cuda.is_available()]                  [torch.backends.mps.is_available()]
               │                                             │
      (NVIDIA RTX 2080)                                (Apple Silicon)
 ├── Whisper Device: "cuda"                     ├── Whisper Device: "cpu"
 ├── Compute Type: "float16"                    ├── Compute Type: "int8" (ARM NEON)
 ├── PyTorch Device: torch.device("cuda")       ├── PyTorch Device: torch.device("mps")
 └── VRAM Budget: 8 GB Strict Cap               └── RAM Budget: Unified Memory
```

### Strategy per Platform:
1. **NVIDIA RTX 2080 (8 GB GDDR6):**
   * Uses CUDA 12.x + cuDNN.
   * `faster-whisper` runs on dedicated Turing Tensor Cores in `float16` precision.
   * Wav2Vec2 and PyAnnote run in CUDA memory.
   * PyTorch cache is cleared via `torch.cuda.empty_cache()` between pipeline stages.
2. **Apple Silicon (M1/M2/M3/M4):**
   * CTranslate2 runs on CPU using high-performance **Apple Accelerate** and **ARM NEON SIMD** vector instructions with `int8` quantization.
   * Neural network models (PyAnnote segmentation and Wav2Vec2 alignment) utilize Apple **Metal Performance Shaders (MPS)**.

---

## 3. Memory & VRAM Budget (RTX 2080 8 GB Profile)

The pipeline is explicitly partitioned to prevent CUDA Out-of-Memory (OOM) errors:

```
Total Dedicated VRAM: 8,192 MB
┌──────────────────────────────────────┬──────────────┬───────────────────────────┐
│ Component                            │ VRAM Usage   │ Management Strategy       │
├──────────────────────────────────────┼──────────────┼───────────────────────────┤
│ OS & Display Buffers                 │ ~1,000 MB    │ Reserved by system        │
│ DeepFilterNet (Speech Cleaning)      │ ~350 MB      │ Run & unallocated         │
│ Silero VAD (Voice Detection)         │ ~150 MB      │ Lightweight Torch buffer  │
│ Faster-Whisper Large-v3 (FP16)       │ ~2,200 MB    │ Persistent during ASR     │
│ WhisperX Wav2Vec2 Alignment          │ ~450 MB      │ Run after ASR completes   │
│ PyAnnote 3.1 Diarization             │ ~1,600 MB    │ Sequential execution pass │
├──────────────────────────────────────┼──────────────┼───────────────────────────┤
│ **Peak Concurrent VRAM Usage**       │ **~4,800 MB**│ **Well under 8,192 MB**   │
└──────────────────────────────────────┴──────────────┴───────────────────────────┘
```

> **Sequential Stage Handoff:** Whisper and PyAnnote are not run in lockstep parallel threads. Whisper finishes transcribing the complete audio first; its intermediate text and attention tensors are flushed, leaving ample VRAM headroom for PyAnnote to extract embeddings and perform clustering.

---

## 4. Component Deep Dive

### A. The Processing Worker (`engine/worker.py`)
* The worker runs on an isolated background thread (`threading.Thread`) managed by the queue manager.
* It polls the SQLite database for jobs with `status = 'queued'`.
* It transitions job status through a deterministic state machine:
  $$\text{QUEUED} \longrightarrow \text{PREPROCESSING} \longrightarrow \text{TRANSCRIBING} \longrightarrow \text{ALIGNING} \longrightarrow \text{DIARIZING} \longrightarrow \text{COMPLETED}$$
* If any stage throws an exception, the job is marked `FAILED`, the error message and stack trace are persisted to the database, and the worker immediately proceeds to the next job in the queue.

### B. Audio Preprocessing Pipeline (`engine/audio.py`)
* Uses native streaming FFmpeg via `subprocess.Popen` to extract raw mono 16 kHz audio into a temporary working directory (`/tmp/transcriber/` or `data/cache/`).
* If "Restore Audio" is active, `DeepFilterNet` processes the 16 kHz WAV file, outputting an enhanced audio file before Whisper ingestion.

### C. Forced Alignment & Diarization Fusion (`engine/fusion.py`)
* Combines two temporal streams:
  1. **Word-Level Timeline:** `[ {word: "hello", start: 0.12, end: 0.45}, ... ]` from WhisperX.
  2. **Speaker Interval Timeline:** `[ {speaker: "SPEAKER_00", start: 0.00, end: 2.30}, ... ]` from PyAnnote.
* **Interval Intersection Algorithm:** For each word with interval $[t_{\text{start}}, t_{\text{end}}]$, computes the overlap duration with all active speaker segments. The word is assigned to the speaker cluster with the maximum temporal overlap.

---

## 5. Persistence & Storage Architecture

* **Database Engine:** Embedded SQLite 3 located at `data/transcriber.db`.
* **Audio Artifacts Directory:** `data/media/` stores temporary and cached extracted audio tracks.
* **Transcript Output Directory:** `data/outputs/{job_id}/` contains generated `.srt`, `.vtt`, `.docx`, `.pdf`, `.txt`, and `.json` artifacts.
* **Write-Ahead Logging (WAL):** SQLite is configured in WAL mode (`PRAGMA journal_mode=WAL;`) to allow concurrent reads from the FastAPI web server while the background worker writes progress updates.

---

## 6. Real-Time Telemetry via Server-Sent Events (SSE)

The web frontend subscribes to an SSE endpoint (`GET /api/events`):
```
event: job_progress
data: {"job_id": "4a7f...", "status": "transcribing", "progress": 42.5, "stage_detail": "Transcribing chunk 14/32"}

event: job_completed
data: {"job_id": "4a7f...", "status": "completed", "duration": 184.2}
```
This enables zero-latency UI updates without aggressive HTTP polling.
