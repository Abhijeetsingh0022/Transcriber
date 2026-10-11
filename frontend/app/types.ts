import { LucideIcon } from "lucide-react";

export interface SystemTelemetry {
  platform: string;
  device_name: string;
  cpu_threads: number;
  cpu_usage_percent: number;
  system_ram_total_gb: number;
  system_ram_available_gb: number;
  vram_total_mb: number | null;
  vram_allocated_mb: number;
  vram_free_mb: number;
  worker_status: string;
  active_job_id: string | null;
  queued_jobs_count: number;
}

export interface Job {
  id: string;
  filename: string;
  file_size_bytes: number;
  duration_seconds: number;
  mode: string;
  language: string;
  task: string;
  diarize: boolean;
  num_speakers?: number | null;
  status: string;
  progress: number;
  current_stage: string;
  error_message: string | null;
  created_at: string;
  detected_language?: string | null;
  word_count?: number | null;
  segment_count?: number | null;
  snippet_text?: string | null;
}

export interface ModelOption {
  id: string;
  name: string;
  model: string;
  description: string;
  icon: LucideIcon;
  badge: string;
  badgeColor: string;
}

export interface LanguageOption {
  code: string;
  name: string;
  flag?: string;
}

export interface TaskOption {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
}

export interface DiarizationOption {
  id: string;
  label: string;
  sublabel: string;
  diarize: boolean;
  numSpeakers: number | "";
  badge: string;
  badgeColor?: string;
}

export interface QueueStats {
  total: number;
  completed: number;
  processing: number;
  queued: number;
  failed: number;
  totalWords: number;
  totalSec: number;
}

export interface ExportFormatOption {
  id: string;
  label: string;
  default: boolean;
}

export interface KeyPoolItem {
  id: number;
  masked: string;
  preview?: string;
}

export interface ApiKeySettings {
  gemini_configured: boolean;
  gemini_masked: string;
  gemini_count?: number;
  gemini_keys?: KeyPoolItem[];

  openrouter_configured: boolean;
  openrouter_masked: string;
  openrouter_count?: number;
  openrouter_keys?: KeyPoolItem[];

  tokenharbor_configured: boolean;
  tokenharbor_masked: string;
  tokenharbor_count?: number;
  tokenharbor_keys?: KeyPoolItem[];
}

export interface VerifyKeyResponse {
  valid: boolean;
  rate_limited?: boolean;
  latency_ms?: number;
  model?: string;
  label?: string;
  provider?: string;
  error?: string;
}

export interface ModelStatus {
  id: string;
  name: string;
  label: string;
  repo_id: string;
  approx_size_mb: number;
  ram_required: string;
  speed_rating: string;
  accuracy_rating: string;
  description: string;
  is_default_bundled: boolean;
  is_installed: boolean;
  actual_size_mb: number;
  download_status: "idle" | "downloading" | "completed" | "error";
  download_progress: number;
  download_percent?: number;
  error_message?: string | null;
}

export interface DownloadStatus {
  tier: string;
  tier_id?: string;
  status: "idle" | "downloading" | "completed" | "error";
  progress: number;
  progress_percent?: number;
  message?: string;
  error_message?: string | null;
}

export interface StorageInfo {
  models_directory: string;
  total_disk_gb: number;
  free_disk_gb: number;
  used_disk_gb: number;
}

export interface ActionItem {
  task: string;
  assignee: string;
  timestamp: string;
  time_seconds: number;
  priority: "high" | "medium" | "low";
}

export interface ShowNoteChapter {
  title: string;
  start_time: number;
  start_timestamp: string;
  description: string;
}

export interface KeyQuestion {
  question: string;
  answer: string;
  asked_by: string;
  timestamp: string;
}

export interface ExecutiveIntelligence {
  job_id: string;
  filename: string;
  tldr: string;
  executive_summary: string;
  key_takeaways: string[];
  action_items: ActionItem[];
  chapters: ShowNoteChapter[];
  key_questions?: KeyQuestion[];
  sentiment_and_tone?: string;
  generated_by?: string;
}

export interface AudioMarker {
  id: string;
  job_id?: string;
  time: number;
  label: string;
  tag: "note" | "review" | "highlight";
  created_at?: string;
}

export interface SearchResultItem {
  segment_id: number;
  job_id: string;
  speaker_label: string;
  text: string;
  start_time: number;
  end_time: number;
  highlight: string;
}
