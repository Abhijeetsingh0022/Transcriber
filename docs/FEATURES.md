# Features & Capabilities Specification

This document provides a detailed technical breakdown of every feature, parameter, algorithm, and user-facing control available in **Transcriber**.

---

## 1. Media Ingestion & Video Pipeline

### Supported Formats
* **Audio:** MP3, WAV, AAC, M4A, OGG, OPUS, WMA, FLAC, AIFF.
* **Video:** MP4, MOV, MKV, WEBM, AVI, WMV, FLV, M4V.

### Ingestion Controls & Mechanics
* **Non-Memory-Mapped Extraction:** Video files up to 10 GB and 10 hours in length are demuxed directly to disk using streaming FFmpeg subprocesses:
  ```bash
  ffmpeg -y -i input_video.mp4 -vn -acodec pcm_s16le -ar 16000 -ac 1 output_audio.wav
  ```
* **Streaming URL Ingestion:** Direct link ingestion for YouTube and video platforms via built-in `yt-dlp` integration (extracts audio stream directly without downloading high-res video streams).
* **Batch Drag-and-Drop:** Queue up to 100 media files in a single drop event with automatic duplicate detection and file hash verification.

---

## 2. Transcription Engine Tiers

Transcriber provides 4 transcription tiers, balancing throughput and Word Error Rate (WER):

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                TRANSCRIPTION TIERS                                     │
├───────────────┬──────────────────┬──────────────┬───────────────┬──────────────────────┤
│ Tier Name     │ Model Checkpoint │ Parameters   │ Mel Bins      │ Decoding Strategy    │
├───────────────┼──────────────────┼──────────────┼───────────────┼──────────────────────┤
│ **Whale**     │ Large-v3         │ 1.55 Billion │ 128 Mel Bins  │ Beam search (size=5) │
│ **Whale Turbo**│ Large-v3-Turbo  │ ~809 Million │ 128 Mel Bins  │ Beam search (size=4) │
│ **Dolphin**   │ Small            │ 244 Million  │ 80 Mel Bins   │ Beam search (size=2) │
│ **Cheetah**   │ Base             │ 74 Million   │ 80 Mel Bins   │ Greedy search (size=1)│
└───────────────┴──────────────────┴──────────────┴───────────────┴──────────────────────┘
```

### Advanced Inference Controls
* **Temperature Fallback:** Automatic decoding retries on repetition or high entropy across $T \in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]$.
* **Condition on Previous Text:** Toggle autoregressive context propagation across 30-second audio windows to improve long-range coherence.
* **Custom Vocabulary / Initial Prompt:** Input custom brand names, acronyms, and technical jargon (up to 224 tokens) to bias decoder token priors.
* **Repetition Penalty:** Configurable penalty factor (default `1.2`) to prevent Whisper hallucination loops.

---

## 3. Language & Translation Engine

### Multilingual Speech Recognition (ASR)
* Supports **98 spoken languages**.
* **Auto-Detect Language:** First 30s encoder forward pass computes argmax probability across 98 language tokens.
* **Forced Language Code:** Override auto-detection to prevent language hallucination on quiet, accented, or multilingual audio.

### Direct Acoustic "Transcribe to English" (`task="translate"`)
* **Zero-Shot Cross-Attention Translation:** Converts non-English audio directly into English text in a single inference pass.
* Unlike cascaded systems (ASR $\rightarrow$ Google Translate), direct acoustic translation retains conversational idioms, speaker intent, and eliminates compounding mistranslation errors.

---

## 4. Speaker Diarization Suite (PyAnnote 3.1)

Identifies who spoke when, assigning distinct identities across the transcript.

### Configuration Modes
* **Auto-Detect Speakers:** Unsupervised spectral clustering evaluates the eigengap of the affinity matrix to estimate speaker count dynamically.
* **Constrained Speaker Count ($K = 2$ to $8$):** Sets fixed cluster constraints in Agglomerative Hierarchical Clustering (AHC). Recommended for 2-person interviews, panel discussions, and podcasts to reduce Diarization Error Rate (DER).

### Diarization Pipeline Details
1. **Voice Activity Detection (VAD):** Segments continuous audio into active voice turns.
2. **Feature Extraction:** Computes 256-dimensional embedding vectors using `pyannote/embedding` (ResNet34 architecture).
3. **Cluster Assignment:** Assigns temporal voice segments to `Speaker 0`, `Speaker 1`, etc.
4. **Majority-Vote Word Intersection:** Overlaps diarization segments with word-level timestamps to output clean, speaker-labeled paragraphs.

---

## 5. Subtitle & Phoneme Forced Alignment (WhisperX)

Standard Whisper timestamps drift by up to 500ms due to attention head ambiguity. Transcriber includes a second-pass forced alignment stage using **Wav2Vec2**:

```
[Raw Whisper Output]  ──►  [Wav2Vec2 CTC Loss]  ──►  [Phoneme Alignment]
"Hello world"              "h-eh-l-ow w-er-l-d"      Exact ms Timestamps:
                                                     "Hello": [0.12s - 0.45s]
                                                     "world": [0.48s - 0.82s]
```

### Subtitle Formatting Controls
* **Max Characters Per Line (CPL):** Standard broadcast limits (default: 37 CPL for standard subtitles, 42 for social media).
* **Max Words Per Segment:** Grouping limits (default: 8–12 words).
* **Sentence-Aware Segmentation:** Breaks lines strictly on grammatical punctuation boundaries rather than arbitrary character cutoffs.

---

## 6. Audio Restoration & Cleaning ("Restore Audio")

Powered by **DeepFilterNet v3**:
* **Real-Time Speech Enhancement:** Suppresses non-stationary noise, HVAC rumble, room echo, and mechanical keyboard clicks.
* **Low Overhead:** Requires only ~300 MB of RAM/VRAM and processes at 30x–50x real-time speed.
* **Toggleable Per-Job:** Enable only for noisy field recordings, cell phone calls, or unproduced video footage.

---

## 7. Persistent Batch Queue Management

* **Zero-Crash Sequential Processing:** Videos in a 50-file queue are processed one by one to ensure VRAM never exceeds hardware limits.
* **State Recovery:** If the computer restarts or loses power, pending and failed jobs resume automatically from their last checkpoint.
* **Per-File Actions:** Pause, cancel, reorder, retry, or delete jobs in the queue.
* **Live Telemetry:** Emits real-time processing metrics via Server-Sent Events (SSE):
  * Active pipeline stage (`Extracting Audio`, `Running VAD`, `Transcribing`, `Aligning`, `Diarizing`).
  * Percent completed (0% – 100%).
  * Elapsed time and estimated time of arrival (ETA).

---

## 8. Web Dashboard & Interactive Editor

* **Interactive Audio/Video Player:** Plays extracted audio or preview video alongside the transcript.
* **Karaoke-Style Playback Sync:** Highlights words in real time as the audio plays.
* **Click-to-Seek:** Clicking any word or timestamp instantly jumps the media player to that exact millisecond.
* **Bulk Speaker Renamer:** Rename `Speaker 0` to `John Doe` across the entire document in one click.
* **Search & Replace:** Quickly correct recurring misheard technical terms or acronyms.
* **Editable Timecodes:** Adjust start and end timestamps directly in the web UI.

---

## 9. Multi-Format Export Engine

Exports can be downloaded individually or packaged as a bulk ZIP bundle:

| Format | Extension | Intended Use Case |
| :--- | :--- | :--- |
| **SubRip Subtitle** | `.srt` | YouTube, Premiere Pro, DaVinci Resolve, VLC |
| **WebVTT** | `.vtt` | HTML5 `<video>` tags, modern web video players |
| **Microsoft Word** | `.docx` | Cleanly styled reading document with speaker headings |
| **PDF Document** | `.pdf` | Formal reports and archival printing |
| **Plain Text** | `.txt` | Plain text output with or without timestamps |
| **Spreadsheet** | `.csv` | Tabular data: `Start Time`, `End Time`, `Speaker`, `Text` |
| **JSON Metadata** | `.json` | Full AST containing word-level confidence scores and phoneme boundaries |
| **Bulk ZIP** | `.zip` | Archive containing all selected formats for every completed file in the queue |
