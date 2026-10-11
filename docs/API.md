# API Reference & Telemetry Specifications

The **Transcriber** backend exposes a REST API alongside a Server-Sent Events (SSE) stream for real-time telemetry.

* **Base URL:** `http://localhost:8000/api`
* **Response Content Type:** `application/json` (unless downloading binary export artifacts)

---

## 1. System & Hardware Telemetry

### `GET /api/system/status`
Returns detected compute hardware, active VRAM/RAM usage, and backend readiness.

#### Response:
```json
{
  "platform": "NVIDIA CUDA",
  "device_name": "NVIDIA GeForce RTX 2080",
  "vram_total_mb": 8192,
  "vram_allocated_mb": 2240,
  "vram_free_mb": 5952,
  "cpu_threads": 16,
  "system_ram_free_gb": 11.4,
  "worker_status": "processing",
  "active_job_id": "8f3e2a1b-...",
  "queued_jobs_count": 4
}
```

---

## 2. Job Queue Management

### `POST /api/jobs/upload`
Uploads one or multiple audio/video files to the processing queue.

* **Content-Type:** `multipart/form-data`
* **Parameters:**
  * `files`: Array of media binary files.
  * `mode`: `"whale"` | `"whale_turbo"` | `"dolphin"` | `"cheetah"` (Default: `"whale"`).
  * `language`: Language code or `"auto"` (Default: `"auto"`).
  * `task`: `"transcribe"` | `"translate"` (Default: `"transcribe"`).
  * `diarize`: `true` | `false` (Default: `false`).
  * `num_speakers`: `null` (auto-detect) or integer `2`–`8`.
  * `restore_audio`: `true` | `false` (Default: `false`).
  * `initial_prompt`: Optional custom vocabulary string.

#### Response:
```json
{
  "queued_count": 2,
  "jobs": [
    {
      "id": "e4a19c5b-3a72-4b3d-9f21-70f92b7c02b1",
      "filename": "podcast_episode_42.mp4",
      "status": "queued",
      "mode": "whale",
      "diarize": true
    },
    {
      "id": "c1f88a21-4d32-491e-b873-1289cf29aa04",
      "filename": "lecture_audio.m4a",
      "status": "queued",
      "mode": "whale",
      "diarize": false
    }
  ]
}
```

---

### `POST /api/jobs/url`
Submits a YouTube or web video link for background audio extraction and transcription.

#### Request Body:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "mode": "whale_turbo",
  "diarize": true,
  "num_speakers": 2,
  "restore_audio": false
}
```

#### Response:
```json
{
  "id": "d98e7210-9b41-419b-a01c-6625aa87f123",
  "title": "Rick Astley - Never Gonna Give You Up",
  "status": "queued"
}
```

---

### `GET /api/jobs`
Retrieves a paginated list of all jobs with state and progress.

* **Query Parameters:**
  * `status`: Optional filter (`"queued"`, `"processing"`, `"completed"`, `"failed"`).
  * `page`: Default `1`.
  * `limit`: Default `50`.

#### Response:
```json
{
  "total": 12,
  "page": 1,
  "limit": 50,
  "jobs": [
    {
      "id": "e4a19c5b-3a72-4b3d-9f21-70f92b7c02b1",
      "filename": "podcast_episode_42.mp4",
      "file_size_bytes": 1048576000,
      "duration_seconds": 3612.4,
      "status": "transcribing",
      "progress": 64.2,
      "current_stage": "Transcribing chunk 28/45",
      "created_at": "2026-10-08T15:20:00Z"
    }
  ]
}
```

---

### `POST /api/jobs/{id}/retry`
Re-queues a failed or cancelled job.

---

### `POST /api/jobs/{id}/cancel`
Stops an in-progress job or removes a queued job.

---

### `DELETE /api/jobs/{id}`
Permanently deletes a job, its database records, and all associated media/export files.

---

## 3. Transcript & Editor Endpoints

### `GET /api/jobs/{id}/transcript`
Returns the complete structured transcript, word alignments, and speaker metadata.

#### Response:
```json
{
  "job_id": "e4a19c5b-...",
  "detected_language": "en",
  "word_count": 4820,
  "speakers": [
    { "label": "SPEAKER_00", "display_name": "Host", "color_hex": "#3b82f6" },
    { "label": "SPEAKER_01", "display_name": "Guest", "color_hex": "#10b981" }
  ],
  "segments": [
    {
      "id": "seg-1",
      "speaker_label": "SPEAKER_00",
      "start_time": 0.52,
      "end_time": 4.18,
      "text": "Welcome back to the podcast. Today we have an exciting guest.",
      "words": [
        { "word": "Welcome", "start_time": 0.52, "end_time": 0.98, "confidence": 0.99 },
        { "word": "back", "start_time": 1.02, "end_time": 1.25, "confidence": 0.98 }
      ]
    }
  ]
}
```

---

### `PATCH /api/jobs/{id}/speakers`
Updates speaker display names across the transcript.

#### Request Body:
```json
{
  "updates": [
    { "speaker_label": "SPEAKER_00", "display_name": "Lex Fridman" },
    { "speaker_label": "SPEAKER_01", "display_name": "Guido van Rossum" }
  ]
}
```

---

### `PUT /api/jobs/{id}/transcript`
Saves manual edits made to transcript text or segment boundaries.

---

### `GET /api/jobs/{id}/media`
Streams the extracted 16 kHz audio file with `Range` header support for browser seeking.

---

## 4. Export Endpoints

### `GET /api/jobs/{id}/export/{format}`
Generates and downloads the transcript in the requested file format.

* **Supported Formats:** `srt`, `vtt`, `docx`, `pdf`, `txt`, `csv`, `json`.
* **Headers:** `Content-Disposition: attachment; filename="filename.srt"`

---

### `POST /api/jobs/export/bulk`
Generates a `.zip` archive containing exports for multiple completed jobs.

#### Request Body:
```json
{
  "job_ids": ["e4a19c5b-...", "c1f88a21-..."],
  "formats": ["srt", "docx", "json"]
}
```

---

## 5. Real-Time Telemetry via Server-Sent Events (SSE)

### `GET /api/events`
A single, long-lived HTTP connection that streams real-time updates.

#### Event Stream Example:
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

event: progress
data: {"job_id":"e4a19c5b","progress":35.0,"stage":"transcribing","message":"Processing 00:25:00 / 01:00:12"}

event: stage_change
data: {"job_id":"e4a19c5b","stage":"aligning","message":"Calculating phoneme alignments via Wav2Vec2"}

event: job_completed
data: {"job_id":"e4a19c5b","status":"completed","duration_seconds":3612.4}
```
