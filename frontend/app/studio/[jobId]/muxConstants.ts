/**
 * Shared Multi-Audio Track Muxing Constants & Types.
 * Reused across MuxModal, MuxPanel, and MuxTrackCard for DRY code.
 */

export interface TrackMixState {
  gain: number;
  muted: boolean;
  soloed: boolean;
}

export const DISPOSITION_LABELS: Record<string, string> = {
  none: "None",
  default: "Default",
  dub: "Dub",
  comment: "Commentary",
  hearing_impaired: "HI",
  lyrics: "Lyrics",
  karaoke: "Karaoke",
};

export const DISPOSITION_OPTIONS = [
  { value: "none", label: "None (Standard)" },
  { value: "default", label: "Default Track" },
  { value: "dub", label: "Dub / Translation" },
  { value: "comment", label: "Commentary" },
  { value: "hearing_impaired", label: "Hearing Impaired (HI)" },
  { value: "lyrics", label: "Lyrics" },
  { value: "karaoke", label: "Karaoke" },
];

export const CODEC_OPTIONS = [
  { value: "copy", label: "Copy (Lossless Passthrough)" },
  { value: "aac", label: "AAC (Universal Streaming)" },
  { value: "libopus", label: "Opus (High Efficiency)" },
  { value: "libmp3lame", label: "MP3 (Legacy Audio)" },
  { value: "flac", label: "FLAC (Lossless Master)" },
];

export const LANGUAGE_PRESETS = [
  { code: "und", label: "Undetermined" },
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "hi", label: "Hindi" },
  { code: "pt", label: "Portuguese" },
  { code: "ar", label: "Arabic" },
  { code: "ru", label: "Russian" },
];

export const OUTPUT_FORMAT_OPTIONS = [
  { id: "mp4", label: "MP4 (.mp4)", desc: "Web Ready (+FastStart)" },
  { id: "mkv", label: "MKV (.mkv)", desc: "Multi-Track Matroska" },
  { id: "mov", label: "MOV (.mov)", desc: "QuickTime Pro Master" },
] as const;
