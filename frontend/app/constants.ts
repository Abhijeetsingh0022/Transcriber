import {
  Sparkles,
  Zap,
  Layers,
  Gauge,
  ArrowRightLeft,
  FileText,
} from "lucide-react";
import {
  ModelOption,
  LanguageOption,
  TaskOption,
  DiarizationOption,
  ExportFormatOption,
} from "./types";

// Single source of truth — do not re-declare here
export { API_BASE } from "./lib/api";

export const MODES: ModelOption[] = [
  {
    id: "whale",
    name: "Whale",
    model: "Large-v3",
    description: "Maximum accuracy, 1.55B parameters, 128 Mel bins",
    icon: Sparkles,
    badge: "Gold Standard",
    badgeColor: "bg-amber-50 text-amber-700 border-amber-200/80",
  },
  {
    id: "whale_turbo",
    name: "Whale Turbo",
    model: "Large-v3-Turbo",
    description: "8x faster inference with near-identical word accuracy",
    icon: Zap,
    badge: "Fast & Precise",
    badgeColor: "bg-blue-50 text-blue-700 border-blue-200/80",
  },
  {
    id: "dolphin",
    name: "Dolphin",
    model: "Small",
    description: "244M parameters, ideal for clean speech & podcasts",
    icon: Layers,
    badge: "Low Memory",
    badgeColor: "bg-slate-100 text-slate-700 border-slate-200",
  },
  {
    id: "cheetah",
    name: "Cheetah",
    model: "Base",
    description: "74M parameters, instant draft turnaround",
    icon: Gauge,
    badge: "Fastest",
    badgeColor: "bg-slate-100 text-slate-700 border-slate-200",
  },
];

export const LANGUAGES: LanguageOption[] = [
  { code: "auto", name: "Auto-Detect Language" },
  { code: "en", name: "English" },
  { code: "es", name: "Spanish" },
  { code: "fr", name: "French" },
  { code: "de", name: "German" },
  { code: "it", name: "Italian" },
  { code: "pt", name: "Portuguese" },
  { code: "nl", name: "Dutch" },
  { code: "ru", name: "Russian" },
  { code: "zh", name: "Chinese (Mandarin)" },
  { code: "ja", name: "Japanese" },
  { code: "ko", name: "Korean" },
  { code: "ar", name: "Arabic" },
  { code: "hi", name: "Hindi" },
  { code: "tr", name: "Turkish" },
  { code: "pl", name: "Polish" },
  { code: "uk", name: "Ukrainian" },
  { code: "sv", name: "Swedish" },
  { code: "vi", name: "Vietnamese" },
  { code: "id", name: "Indonesian" },
];

export const TASK_OPTIONS: TaskOption[] = [
  {
    id: "transcribe",
    name: "Transcribe Audio",
    description: "Transcribes audio in original spoken language with word timestamps",
    icon: FileText,
  },
  {
    id: "translate",
    name: "Translate to English",
    description: "Direct speech-to-text translation into natural English",
    icon: ArrowRightLeft,
  },
];

export const DIARIZATION_OPTIONS: DiarizationOption[] = [
  {
    id: "auto",
    label: "Auto Detect Count",
    sublabel: "Dynamic clustering",
    diarize: true,
    numSpeakers: "",
    badge: "Adaptive",
  },
  {
    id: "narrator_2",
    label: "Narrator + 2 Speakers",
    sublabel: "Smart Auto-ID (Narrator, Teacher & Student)",
    diarize: true,
    numSpeakers: 3,
    badge: "Smart Auto-ID",
    badgeColor: "bg-amber-50 text-amber-700 border-amber-200/90",
  },
  {
    id: "2",
    label: "2 Speakers",
    sublabel: "Interview / Dialogue / 2-Host",
    diarize: true,
    numSpeakers: 2,
    badge: "Interview",
  },
  {
    id: "4",
    label: "4 Speakers",
    sublabel: "Panel discussion or group chat",
    diarize: true,
    numSpeakers: 4,
    badge: "Panel",
  },
  {
    id: "5",
    label: "5+ Speakers",
    sublabel: "Multi-speaker meeting / classroom",
    diarize: true,
    numSpeakers: 5,
    badge: "Group",
  },
  {
    id: "off",
    label: "Single Speaker (Off)",
    sublabel: "Disable speaker segmentation",
    diarize: false,
    numSpeakers: "",
    badge: "Single",
  },
];


export const BULK_EXPORT_FORMAT_OPTIONS: ExportFormatOption[] = [
  { id: "pdf", label: "Executive PDF Document (.pdf) - Executive Tables", default: true },
  { id: "docx", label: "Word Document (.docx) - Executive Tables", default: true },
  { id: "srt", label: "SubRip Subtitles (.srt)", default: true },
  { id: "vtt", label: "WebVTT Subtitles (.vtt)", default: false },
  { id: "txt", label: "Plain Text Dialogue (.txt)", default: true },
  { id: "script_html", label: "Interactive HTML Script (.html)", default: false },
  { id: "csv", label: "Tabular CSV Segments (.csv)", default: false },
  { id: "mp3", label: "MP3 Audio (.mp3) - 192kbps Audio", default: false },
  { id: "json", label: "Full AST JSON (.json)", default: false },
];
