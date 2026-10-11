# Product Requirements Document (PRD)

## Project: Transcriber
**Status:** Approved for Development  
**Target Environments:** macOS (Apple Silicon M-Series) & Linux/Windows (NVIDIA RTX 2080+ CUDA)  
**Author:** Senior Systems & AI Architect  

---

## 1. Executive Summary

**Transcriber** is a private, cross-platform, self-hosted transcription and speaker diarization engine accompanied by a queue-driven web dashboard. The system matches and exceeds the accuracy of proprietary cloud tools such as TurboScribe, without subjecting users to per-minute billing, file-size bottlenecks, cloud queues, or privacy risks.

By combining OpenAI’s **Whisper Large-v3**, **PyAnnote 3.1**, **WhisperX phoneme alignment**, **Silero VAD**, and **DeepFilterNet**, Transcriber delivers production-grade word-error-rate (WER) performance, millisecond-accurate subtitle synchronization, and multi-speaker attribution on commodity desktop hardware.

---

## 2. Problem Statement & Market Gaps

Commercial tools like TurboScribe, Otter.ai, and Rev present critical trade-offs:
1. **Privacy Concerns:** Cloud transcription requires uploading confidential legal depositions, medical consultations, unreleased media, or private interviews to third-party servers.
2. **Artificial Bottlenecks:** Cloud providers limit concurrent batch processing, throttle users exceeding arbitrary daily limits ("Fair Use" modes), or cap single files to 25–100 MB.
3. **Timestamp Drift:** Standard Whisper outputs timestamp offsets that drift by 200–500ms, making auto-generated subtitles clumsy and out-of-sync without tedious manual re-timing.
4. **Subscription Fatigue:** Continuous monthly charges ($10–$30/month) for software that can run faster and with higher fidelity directly on local hardware.

---

## 3. Goals & Non-Goals

### Goals
* **G-1: Accuracy Parity & Superiority:** Match or beat TurboScribe's "Whale" mode across complex audio, background noise, and varied accents.
* **G-2: Sub-Word Timestamp Precision:** Achieve <30ms alignment accuracy using Wav2Vec2 phoneme forced alignment.
* **G-3: High-Reliability Batch Queue:** Ingest queues of 50+ video/audio files (up to 10 hours and 10 GB per file) and process them sequentially without out-of-memory (OOM) crashes.
* **G-4: Cross-Platform Hardware Parity:** Auto-detect and optimize execution across NVIDIA CUDA (RTX 2080 8GB) and Apple Silicon (Mac M1–M4).
* **G-5: Zero-Cloud Footprint:** 100% of data processing, model inference, and storage occurs on the local machine.

### Non-Goals
* **NG-1: Real-Time Calendar Meeting Bots:** Not building bots to automatically join live Zoom/Teams meetings.
* **NG-2: Non-Linear Video Timeline Editing:** Not building a full timeline NLE (like Premiere or Descript). The focus is transcription, diarization, subtitle generation, and text correction.
* **NG-3: Multi-User Cloud SaaS:** Not designing a multi-tenant user authentication or billing infrastructure; this is a single-seat local workstation application.

---

## 4. User Personas

| Persona | Core Need | Key Feature Used |
| :--- | :--- | :--- |
| **Video Producer / Creator** | Subtitle generation for multi-gigabyte 4K MP4/MOV files | Bulk video queue, SRT/VTT export, phoneme alignment |
| **Journalist / Researcher** | 2-person interview transcription with speaker labels | Speaker diarization (2 speakers), Whale mode |
| **Legal / Compliance Officer** | Complete privacy and zero data leakage | Offline operation, AES-ready local storage |
| **Multilingual Content Specialist** | Instant translation of foreign interviews into English | "Transcribe to English" native acoustic translation |

---

## 5. Functional Requirements (FR)

### FR-1: Media Ingestion & Validation
* **FR-1.1:** Support audio containers: MP3, WAV, AAC, M4A, OGG, OPUS, FLAC, WMA.
* **FR-1.2:** Support video containers: MP4, MOV, MKV, WEBM, AVI.
* **FR-1.3:** Extract audio stream via FFmpeg without loading entire video containers into memory.
* **FR-1.4:** Enforce 16 kHz 16-bit mono PCM standardization for all downstream models.
* **FR-1.5:** Direct download and transcription from YouTube URLs.

### FR-2: Audio Preprocessing & Cleaning
* **FR-2.1:** Implement optional **DeepFilterNet v3** audio restoration toggle to suppress noise, air conditioning rumble, and static.
* **FR-2.2:** Implement **Silero VAD v5** to filter out non-speech segments and avoid Whisper hallucination loops on long silences.

### FR-3: Speech-to-Text Engine (ASR)
* **FR-3.1:** Integrate `faster-whisper` (CTranslate2) with dynamic model switching:
  * `Whale`: Whisper Large-v3 (1.55B parameters).
  * `Whale Turbo`: Whisper Large-v3-Turbo (8x faster inference).
  * `Dolphin`: Whisper Small (244M parameters).
  * `Cheetah`: Whisper Base (74M parameters).
* **FR-3.2:** Support 98+ languages with automatic detection and explicit override.
* **FR-3.3:** Support direct acoustic translation to English (`task="translate"`).
* **FR-3.4:** Support custom initial prompts (up to 224 tokens) for domain-specific terminology and proper nouns.

### FR-4: Speaker Diarization
* **FR-4.1:** Integrate **PyAnnote 3.1** neural speaker diarization.
* **FR-4.2:** Provide manual speaker count constraints ($K = 2$ to $8$ speakers) or auto-clustering.
* **FR-4.3:** Correlate speaker segment time bounds with word timestamps to label speakers per utterance.

### FR-5: Forced Alignment
* **FR-5.1:** Integrate **WhisperX Wav2Vec2** forced alignment pipeline to produce precise word-level start/end timestamps.

### FR-6: Job Queue & Persistence
* **FR-6.1:** Persist all jobs, settings, and progress in an embedded SQLite database.
* **FR-6.2:** Support background worker execution that survives application restarts (recovers unfinished jobs).
* **FR-6.3:** Real-time event streaming of job progress (0%–100%) and current pipeline phase via Server-Sent Events (SSE) or WebSockets.

### FR-7: Web Dashboard & Editor
* **FR-7.1:** Drag-and-drop file upload zone supporting 50+ files at once.
* **FR-7.2:** Job queue table with status indicators (`Queued`, `Extracting`, `VAD`, `Transcribing`, `Aligning`, `Diarizing`, `Completed`, `Failed`).
* **FR-7.3:** Interactive synchronized player: clicking any word in the transcript jumps the audio playback to that exact timestamp.
* **FR-7.4:** Inline transcript text editing and bulk speaker renaming (e.g., renaming `Speaker 1` to `Dr. Smith`).

### FR-8: Export Formats
* **FR-8.1:** Export single transcripts or bulk ZIP packages in:
  * Subtitles: `.srt`, `.vtt`
  * Documents: `.docx`, `.pdf`, `.txt`, `.csv`
  * Raw Data: `.json` (full word-level timestamp metadata)

---

## 6. Non-Functional Requirements (NFR)

* **NFR-1 (Memory Safety):** VRAM usage must not exceed 6.5 GB on an 8 GB GPU (leaving 1.5 GB overhead for OS/display).
* **NFR-2 (Throughput):** On an RTX 2080, transcription of a 1-hour audio file in Whale mode must complete in under 3.5 minutes. On an M2/M3 Mac, under 8 minutes.
* **NFR-3 (Reliability):** A corrupt file in a 50-file queue must fail gracefully, log the error, and allow the remaining 49 files to continue processing.
* **NFR-4 (Zero External Calls):** The core engine must operate fully air-gapped without making outbound HTTP requests (excluding optional initial model downloads).

---

## 7. Success Metrics

1. **Word Error Rate (WER):** Lower than or equal to TurboScribe's Whale mode across standard benchmark test sets (LibriSpeech test-clean < 2.5% WER).
2. **Timestamp Accuracy:** Subtitle boundary error < 30ms compared to reference audio cues.
3. **Queue Completion Rate:** 100% completion of 50-file bulk queues without memory exhaustion or process crashes.
