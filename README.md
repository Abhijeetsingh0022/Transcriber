---
title: TMUX Transcriber
emoji: 🎙️
colorFrom: cyan
colorTo: blue
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
---

# Transcriber

> **High-Accuracy Local AI Transcription, Speaker Diarization & Audio Workstation**  
> Built with `faster-whisper` (Whisper Large-v3), PyAV/FFmpeg, FastAPI, SQLite WAL, and Next.js 16 (React 19).

---

## ⚡ Overview

**Transcriber** is a professional-grade, privacy-first transcription and audio intelligence platform designed for creators, journalists, podcasters, researchers, and video editors. It delivers local machine-learning transcription with zero data leakage, microsecond-accurate word alignment, multi-speaker diarization, directional dialogue turns, multi-track audio/video muxing, and an interactive DAW-inspired editing studio.

```
                      ┌──────────────────────────────────────────────┐
                      │          Ingestion & Audio Pipeline          │
                      │  Files • Microphones • URLs (yt-dlp) • PyAV  │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │          High-Accuracy Whisper Engine        │
                      │    Whisper Large-v3 (beam=5) • Silero VAD    │
                      │      Word Timestamps • Speaker Diarization   │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │         FastAPI Backend & SQLite WAL         │
                      │   SSE Job Stream • Subtitle Exporters • Mux  │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │         Next.js 16 Workstation Studio        │
                      │  Script • Teleprompter • Karaoke • Multi-Mux │
                      └──────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 🎙️ AI Transcription & Intelligence Engine
- **Highest Accuracy Whisper Models**: Default configuration utilizes **Whisper Large-v3** (`beam_size=5`, `best_of=5`, `int8_float32`) for maximum vocabulary precision and contextual understanding.
- **Voice Activity Detection (VAD)**: Silero VAD preprocessing strips non-speech noise, trims silence, and suppresses hallucination loops.
- **Speaker Diarization & Intent Analysis**: Automatic clustering of distinct speakers with directional intent parsing (`Speaker -> Addressee`) and turn classification (Statement, Question, Confirmation, Explanation).
- **Dual Engine Architecture**: Local offline execution by default, with optional cloud fallback support via TokenHarbor for high-throughput batching.
- **AI Briefing & Topics**: Automatic topic segmentation, chapter markers, executive TL;DR generation, and sentiment distribution metrics.

### 🎛️ DAW-Grade Studio Workspace
- **Word-Level Microsecond Alignment**: Hover any word to view microsecond timestamps, confidence ratings, and audio duration with zero tooltip collision.
- **Synchronized Playhead & Waveform**: Interactive canvas-rendered audio waveform with peak visualization, scrubber playhead, and draggable markers.
- **A/B Looping & Turn Looping**: Repeat difficult phrases or single dialogue turns seamlessly for transcription verification.
- **5 Specialized Studio Views**:
  - **Script View**: Natural reading format grouped into coherent dialogue turns with speaker pills.
  - **Speeches (Karaoke) View**: Granular audio segment cards with Words-Per-Minute (WPM) telemetry.
  - **Teleprompter Mode**: High-contrast, large-font read-along mode with real-time active word highlighting.
  - **Topic Flow View**: Chronological AI topic segmentation with keywords and summary chips.
  - **Executive Intelligence Briefing**: Structured summary, key takeaways, action items, and speaker time share.
- **Find & Replace Drawer**: Global regex-ready text search and batch replacement across transcript segments.
- **Undo / Redo History Stack**: Full history tracking for transcript edits and speaker reassignments.

### 🎬 Multi-Track Audio & Video Muxing (Stem Mixer)
- **Stem Ingestion**: Upload background music, translated voiceovers, sound effects, or commentary tracks alongside video.
- **Multi-Track Mixing**: Individual volume sliders, pan controls, solo/mute states, and audio delay offset adjustments.
- **Instant Muxing Preview**: Video player previewing custom muxed audio stems alongside synchronized subtitle burns.
- **FFmpeg Mux Rendering**: Server-side remuxing into distribution-ready `.mp4` video files with embedded audio streams.

### 📦 Comprehensive Export Suite
- **Subtitles**: SubRip (`.srt`) and WebVTT (`.vtt`) with strict timestamp formatting and null-segment safety.
- **Documents**: Plain Text (`.txt`), Formatted Markdown (`.md`), Microsoft Word (`.docx`), PDF (`.pdf`), and Structured CSV (`.csv`).
- **Developer APIs**: Complete JSON transcript (`.json`) with word-level confidence arrays and speaker schemas.
- **Bulk Export**: Download all formats in a single zipped package.

---

## 🏗️ Tech Stack

| Layer | Technologies |
|---|---|
| **Frontend** | [Next.js 16](https://nextjs.org/) (App Router & Turbopack), [React 19](https://react.dev/), [Tailwind CSS v4](https://tailwindcss.com/), [Lucide React](https://lucide.dev/) |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [Pydantic v2](https://docs.pydantic.dev/), [SQLite](https://www.sqlite.org/) (WAL mode) |
| **Machine Learning** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2), PyTorch, Torchaudio, Silero VAD |
| **Media Processing** | [PyAV](https://github.com/PyAV-Org/PyAV) (FFmpeg bindings), `yt-dlp` (stream downloader) |
| **Document Generation** | `python-docx` (Word), `reportlab` (PDF) |
| **Palette & Styling** | Strict Slate, Dark Navy, Cyan, and Emerald palette (**100% Zero-Purple Compliance**) |

---

## 📁 Repository Structure

```
Transcriber/
├── backend/
│   ├── api/
│   │   ├── routes/          # REST route handlers (jobs, mux, exports, speakers, settings)
│   │   ├── router.py        # Centralized /api route aggregation
│   │   └── schemas.py       # Pydantic v2 request & response models
│   ├── core/
│   │   ├── config.py        # Environment variables & engine defaults
│   │   ├── constants.py     # Preset thresholds, models, and supported formats
│   │   └── http_cache.py    # ETag & HTTP 304 conditional cache validators
│   ├── db/
│   │   ├── database.py      # SQLite connection & schema migrations (WAL mode)
│   │   └── crud.py          # Safe database operations & path-traversal sanitization
│   ├── engine/
│   │   ├── audio.py         # PyAV container conversion, normalization, & waveform extraction
│   │   ├── transcriber.py   # faster-whisper inference runner & VAD filtering
│   │   ├── intelligence.py  # AI summary generation, intent classification, & topic modeling
│   │   └── exporters/       # Format renderers (SRT, VTT, DOCX, PDF, CSV, JSON, TXT)
│   ├── services/
│   │   └── mux_service.py   # Multi-track audio stem mixing & video muxing service
│   ├── tests/               # 65+ automated unit, integration, and security tests
│   ├── pyproject.toml       # Python dependencies & packaging configuration
│   └── main.py              # Application entrypoint & lifespan lifecycle manager
│
├── frontend/
│   ├── app/
│   │   ├── components/      # Shared components (Modals, IngestionSuite, Header)
│   │   ├── studio/[jobId]/  # Studio Workstation pages & components
│   │   │   ├── components/  # AudioDeck, WorkstationDock, AccurateHoverHud, MuxVideoPlayer
│   │   │   ├── types.ts     # TypeScript interface contracts
│   │   │   ├── utils.ts     # Time formatting, analytics math, & turn aggregation
│   │   │   └── page.tsx     # Studio route wrapper
│   │   ├── lib/             # API client & fetch helpers
│   │   ├── layout.tsx       # Root Next.js layout & typography tokens
│   │   └── page.tsx         # Ingestion dashboard, job queue, & recording deck
│   └── package.json         # Node.js dependencies & Turbopack build scripts
│
├── docs/                    # Deep-dive architecture, API, and database specifications
└── README.md                # Project documentation
```

---

## 🚀 Getting Started

### Prerequisites
- **Python**: Version `3.10` or higher (`3.11` / `3.12` / `3.13` supported).
- **Node.js**: Version `20.0` or higher (`npm` or `pnpm`).
- **FFmpeg**: System library installed (`brew install ffmpeg` on macOS, `apt install ffmpeg` on Ubuntu).
- **Package Managers**: [`uv`](https://github.com/astral-sh/uv) (recommended for Python) and `npm`.

---

### 1. Backend Setup

```bash
cd backend

# Option A: Using uv (Recommended for speed)
uv run python main.py

# Option B: Standard Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
python main.py
```

The backend server starts at:
- **API Server**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Explorer**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Database File**: `backend/data/transcriber.db` (created automatically)

---

### 2. Frontend Setup

```bash
cd frontend

# Install Node dependencies
npm install

# Start the Next.js development server
npm run dev
```

The web application opens at:
- **Web App**: [http://localhost:3000](http://localhost:3000)

---

### 3. Production Deployment & Hosting (One-Command)

Transcriber can be deployed to any VPS (Hetzner, DigitalOcean, AWS EC2, GCP, RunPod) or container host using Docker:

```bash
# Build and run unified production container (Frontend + Backend on Port 8000)
docker compose up -d --build
```

- **Unified Web & API**: Serves the optimized Next.js static build and FastAPI engine from [http://localhost:8000](http://localhost:8000).
- **Persistent Data**: SQLite database, media uploads, and HuggingFace Whisper model weights persist in named Docker volumes.
- **Healthcheck**: Automatic container health monitoring via `/api/system/status`.

---

## 🧪 Testing & Verification

The project includes an automated test suite verifying performance, path traversal defense, resource management, and output correctness.

```bash
# Run backend pytest suite
cd backend
uv run pytest

# Verify frontend TypeScript types & compile
cd frontend
npx tsc --noEmit
npm run build
```

---

## 🔒 Security & Reliability Guardrails

- **Strict Path-Traversal Sanitization**: All job identifiers, track keys, and filename requests pass through regex-enforced sanitization (`^[a-zA-Z0-9_\-]+$`) before disk access, preventing directory escape vulnerabilities.
- **PyAV Container Lifecycle Safety**: Every audio frame decode and container conversion is protected by nested `try...finally: container.close()` blocks to prevent file descriptor and memory leaks during high-throughput workloads.
- **Null-Safe Timestamp Formatting**: Exporters and analytics gracefully handle missing or irregular timestamps with zero `KeyError` crashes.
- **HTTP 304 Conditional Caching**: Large transcript and telemetry endpoints include ETag validation to minimize bandwidth on repeated client inspections.
- **Zero-Purple Palette Compliance**: The entire application uses a Slate, Dark Navy, Cyan, and Emerald palette—completely devoid of purple, violet, indigo, or fuchsia tones.

---

## ⌨️ Studio Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Space` | Play / Pause audio playback |
| `J` / `←` | Jump back 5 seconds |
| `L` / `→` | Jump forward 5 seconds |
| `[` | Jump to previous dialogue turn |
| `]` | Jump to next dialogue turn |
| `R` | Toggle A/B or Turn Repeat loop |
| `F` | Toggle playhead autoscroll tracking |
| `M` | Add an audio marker at current playhead |
| `Cmd + F` / `Ctrl + F` | Open Find & Replace drawer |
| `Cmd + Z` / `Ctrl + Z` | Undo transcript edit |
| `Cmd + Shift + Z` | Redo transcript edit |

---

## 📄 License

Transcriber is licensed under the [MIT License](LICENSE).
Built with open-source models and libraries from the PyTorch, faster-whisper, and Next.js communities.
