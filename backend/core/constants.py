"""
Shared application-wide constants.
"""

from typing import Optional

SPEAKER_PALETTE = [
    "#2563eb",  # Blue
    "#10b981",  # Emerald
    "#0284c7",  # Sky
    "#f59e0b",  # Amber
    "#0d9488",  # Teal
    "#06b6d4",  # Cyan
    "#f97316",  # Orange
    "#64748b",  # Slate
]


def format_speaker_display_name(label: str, raw_name: Optional[str] = None) -> str:
    """
    Standardized speaker formatter: uses custom display_name if available,
    otherwise normalizes 'SPEAKER_00' -> 'Speaker 1'.
    """
    if raw_name and not raw_name.upper().startswith("SPEAKER_"):
        return raw_name
    if label and label.upper().startswith("SPEAKER_"):
        try:
            num = int(label.split("_")[-1]) + 1
            return f"Speaker {num}"
        except ValueError:
            pass
    return raw_name or label or "Speaker 1"
