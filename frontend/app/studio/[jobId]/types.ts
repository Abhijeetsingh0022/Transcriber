export interface Word {
  id?: string;
  word: string;
  start_time: number;
  end_time: number;
  confidence_score?: number;
  speaker_label?: string;
}

export interface Segment {
  id: string;
  segment_index: number;
  speaker_label?: string;
  addressed_to?: string;
  turn_intent?: string;
  start_time: number;
  end_time: number;
  text: string;
  words: Word[];
}

export interface Speaker {
  id: string;
  speaker_label: string;
  display_name: string;
  color_hex: string;
}

export interface Transcript {
  id: string;
  job_id: string;
  full_text: string;
  detected_language: string;
  word_count: number;
  segment_count: number;
  speakers: Speaker[];
  segments: Segment[];
}

export interface DialogueTurn {
  turnIndex: number;
  speakerLabel: string;
  displayName: string;
  colorHex: string;
  addressedTo?: string;
  intent?: string;
  startTime: number;
  endTime: number;
  duration: number;
  wordCount: number;
  wpm: number;
  text: string;
  words: Word[];
  segmentIds: string[];
  segments?: Segment[];
}

export interface AudioMarker {
  id: string;
  time: number;
  label: string;
  tag: "note" | "review" | "highlight";
}

export interface ABLoopState {
  a: number | null;
  b: number | null;
  active: boolean;
}

export interface SpeakerStat extends Speaker {
  talkTime: string;
  percentage: number;
  turnsCount: number;
  wordCount: number;
  avgWpm: number;
}

export interface AudioAnalytics {
  speechTime: string;
  pauseTime: string;
  speechPct: number;
  pausePct: number;
  avgTurnDuration: string;
}

export interface WaveformBar {
  index: number;
  time: number;
  height: number;
  color: string;
  isSpeech: boolean;
  speakerName: string;
}

export interface JobInfo {
  id?: string;
  filename?: string;
  duration_seconds?: number;
}

export interface TopicTurn {
  speaker: string;
  speaker_label: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface VideoTopic {
  section_no: number;
  section: string;
  topic: string;
  start_time: number;
  end_time: number;
  timecode: string;
  duration_seconds: number;
  duration_label: string;
  speaker: string;
  turns: TopicTurn[];
}

export type ViewMode = "script" | "karaoke" | "reader" | "topics" | "intelligence";
export type FontSize = "sm" | "base" | "lg" | "xl";
export type SidebarTab = "speakers" | "markers" | "insights" | "tuning" | "mux";
export type TemplateStyle = "broadcast" | "screenplay" | "legal" | "podcast" | "dialogue" | "topic_flow";
export type TimestampStyle = "range" | "short_range" | "single" | "short" | "ms" | "none";
export type SpeakerCase = "upper" | "title";

// ---------------------------------------------------------------------------
// Multi-audio track muxing
// ---------------------------------------------------------------------------

export interface MuxTrack {
  id: string;
  job_id: string;
  track_index: number;
  label: string;
  language: string;
  filepath: string;
  codec: string;
  bitrate: number;
  channels: number;
  sample_rate: number;
  disposition: string;
  is_default: boolean;
  gain?: number;
  is_muted?: boolean;
  delay_ms?: number;
  created_at?: string;
}

export type MuxStatus = "not_started" | "pending" | "processing" | "completed" | "failed";

export interface MuxJob {
  id?: string;
  job_id: string;
  output_path: string | null;
  output_format: string | null;
  status: MuxStatus;
  error_message: string | null;
  custom_video_path?: string | null;
  custom_video_name?: string | null;
  mux_mode?: "tracks" | "blend";
  mute_all_audio?: boolean;
  created_at?: string;
  completed_at?: string | null;
  progress?: number;
  stage?: string;
  logs?: string[];
}


