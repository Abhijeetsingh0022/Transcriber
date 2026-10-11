import re
from typing import List, Optional
from pydantic import BaseModel, field_validator


class UrlJobRequest(BaseModel):
    url: str
    mode: str = "whale"
    language: str = "auto"
    task: str = "transcribe"
    diarize: bool = False
    num_speakers: Optional[int] = None
    restore_audio: bool = False
    initial_prompt: Optional[str] = None


class SegmentSpeakerUpdateRequest(BaseModel):
    segment_ids: List[str]
    speaker_label: str


class SegmentAddresseeUpdateRequest(BaseModel):
    segment_ids: List[str]
    addressed_to: str


class IdentifySpeakersRequest(BaseModel):
    tier: str = "auto"
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    job_ids: List[str]


class BulkExportRequest(BaseModel):
    job_ids: List[str]
    formats: List[str] = ["pdf", "docx", "srt", "txt"]


class SpeakerUpdateItem(BaseModel):
    speaker_label: str
    display_name: str
    color_hex: Optional[str] = "#2563eb"

    @field_validator("color_hex")
    @classmethod
    def validate_color_hex(cls, v: Optional[str]) -> str:
        if not v:
            return "#2563eb"
        v_clean = v.strip()
        if not re.match(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", v_clean):
            return "#2563eb"
        return v_clean


class SegmentTextUpdateRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return v.strip()


