"""
Data models and schemas for Transcriber jobs, transcripts, and telemetry.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobMode(str, Enum):
    WHALE = "whale"
    WHALE_TURBO = "whale_turbo"
    DOLPHIN = "dolphin"
    CHEETAH = "cheetah"


class JobTask(str, Enum):
    TRANSCRIBE = "transcribe"
    TRANSLATE = "translate"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    ALIGNING = "aligning"
    DIARIZING = "diarizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WordItem(BaseModel):
    id: Optional[str] = None
    word: str
    start_time: float
    end_time: float
    confidence_score: float = 1.0
    speaker_label: Optional[str] = None


class SegmentItem(BaseModel):
    id: Optional[str] = None
    segment_index: int
    speaker_label: Optional[str] = None
    addressed_to: Optional[str] = None
    turn_intent: Optional[str] = None
    start_time: float
    end_time: float
    text: str
    words: List[WordItem] = Field(default_factory=list)


class SpeakerItem(BaseModel):
    id: Optional[str] = None
    speaker_label: str
    display_name: str
    color_hex: str = "#2563eb"


class TranscriptResponse(BaseModel):
    id: str
    job_id: str
    full_text: str
    detected_language: Optional[str] = None
    language_probability: Optional[float] = None
    word_count: int = 0
    segment_count: int = 0
    speakers: List[SpeakerItem] = Field(default_factory=list)
    segments: List[SegmentItem] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class JobCreate(BaseModel):
    mode: JobMode = JobMode.WHALE
    language: str = "auto"
    task: JobTask = JobTask.TRANSCRIBE
    diarize: bool = False
    num_speakers: Optional[int] = None
    restore_audio: bool = False
    initial_prompt: Optional[str] = None


class JobItem(BaseModel):
    id: str
    filename: str
    filepath: str
    file_size_bytes: int
    duration_seconds: float = 0.0
    mode: JobMode
    language: str = "auto"
    task: JobTask = JobTask.TRANSCRIBE
    diarize: bool = False
    num_speakers: Optional[int] = None
    restore_audio: bool = False
    initial_prompt: Optional[str] = None
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    current_stage: str = "Queued in line"
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class SystemStatus(BaseModel):
    platform: str
    device_name: str
    cpu_threads: int
    cpu_usage_percent: float
    system_ram_total_gb: float
    system_ram_available_gb: float
    system_ram_used_percent: float
    vram_total_mb: Optional[int] = None
    vram_allocated_mb: int = 0
    vram_free_mb: int = 0
    worker_status: str
    active_job_id: Optional[str] = None
    queued_jobs_count: int = 0
