"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  FileText,
  Layers,
  Tv,
  Eye,
  AlertCircle,
  Search,
  Sparkles,
  UserCheck,
  Sliders,
  Download,
  ChevronDown,
  PanelRight,
  PanelLeft,
  FileAudio,
  CheckCircle2,
  Share2,
  Loader2,
  FileSpreadsheet,
  Film,
  Compass,
  SlidersHorizontal,
  Settings,
  Undo2,
  Redo2,
} from "lucide-react";
import { JobInfo, ViewMode } from "../types";
import { API_BASE } from "../utils";

interface StudioHeaderProps {
  jobId: string;
  jobInfo: JobInfo | null;
  isMounted: boolean;
  isPlaying: boolean;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  saveStatus: string;
  followPlayhead?: boolean;
  onToggleFollow?: () => void;
  showConfidence?: boolean;
  onToggleConfidence?: () => void;
  isSearchOpen: boolean;
  onToggleSearch: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
  onOpenTemplateModal?: () => void;
  onOpenSpeakerModal?: () => void;
  isSettingsOpen?: boolean;
  onToggleSettings?: () => void;
  onOpenPreferences?: () => void;
  isLeftSidebarOpen?: boolean;
  onToggleLeftSidebar?: () => void;
  isRightSidebarOpen?: boolean;
  onToggleRightSidebar?: () => void;
  mediaStem: string;
  onIdentifySpeakers?: () => void;
  isIdentifyingSpeakers?: boolean;
  onOpenMux?: () => void;
}

export function StudioHeader({
  jobId,
  jobInfo,
  isMounted,
  isPlaying,
  viewMode,
  onViewModeChange,
  saveStatus,
  followPlayhead,
  onToggleFollow,
  showConfidence,
  onToggleConfidence,
  isSearchOpen,
  onToggleSearch,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
  onOpenTemplateModal,
  onOpenSpeakerModal,
  isSettingsOpen,
  onToggleSettings,
  onOpenPreferences,
  isLeftSidebarOpen = true,
  onToggleLeftSidebar,
  isRightSidebarOpen = true,
  onToggleRightSidebar,
  mediaStem,
  onIdentifySpeakers,
  isIdentifyingSpeakers,
  onOpenMux,
}: StudioHeaderProps) {
  const [isExportOpen, setIsExportOpen] = useState(false);
  const exportDropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (exportDropdownRef.current && !exportDropdownRef.current.contains(event.target as Node)) {
        setIsExportOpen(false);
      }
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsExportOpen(false);
      }
    }
    if (isExportOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      document.addEventListener("keydown", handleKeyDown);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [isExportOpen]);

  return (
    <header className="h-14 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-3 sm:px-4 lg:px-5 flex items-center justify-between shrink-0 z-30 select-none sticky top-0 shadow-xs w-full max-w-full overflow-visible gap-2 sm:gap-4">
      {/* =========================================================================
          ZONE 1: SESSION IDENTITY, MEDIA CAPSULE & NAVIGATION (LEFT)
          ========================================================================= */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 shrink-0 min-w-0">
        {/* Back to Queue Navigation */}
        <Link
          href="/"
          className="group flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-slate-50 hover:bg-slate-100/90 border border-slate-200/90 px-2 sm:px-2.5 py-1.5 rounded-lg transition-all shadow-2xs hover:shadow-xs active:scale-95"
          title="Back to TMUX Queue"
        >
          <ArrowLeft className="w-3.5 h-3.5 text-slate-500 group-hover:-translate-x-0.5 transition-transform" />
          <img src="/tmux-icon.png" alt="TMUX" className="h-3 w-auto object-contain opacity-85 group-hover:opacity-100" />
          <span className="hidden sm:inline">Queue</span>
        </Link>

        {/* Left Dock Toggle Button */}
        {onToggleLeftSidebar && (
          <button
            onClick={onToggleLeftSidebar}
            className={`p-1.5 rounded-lg border transition-all shadow-2xs active:scale-95 cursor-pointer ${
              isLeftSidebarOpen
                ? "bg-slate-100 text-slate-900 border-slate-300"
                : "text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border-slate-200/80"
            }`}
            title={
              isLeftSidebarOpen
                ? "Collapse Left Dock (Audio Deck & Speakers)"
                : "Open Left Dock (Audio Deck & Speakers)"
            }
          >
            <PanelLeft
              className={`w-3.5 h-3.5 ${
                isLeftSidebarOpen ? "text-blue-600" : "text-slate-500"
              }`}
            />
          </button>
        )}

        <div className="h-4 w-px bg-slate-200/80 hidden lg:block" />

        {/* Source Media Identity Capsule */}
        <div className="flex items-center gap-1.5 sm:gap-2 bg-slate-50/90 border border-slate-200/80 pl-2 sm:pl-2.5 pr-1.5 sm:pr-2 py-1 rounded-lg shadow-2xs min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span className="p-1 rounded bg-blue-50 text-blue-600 shrink-0">
              <FileAudio className="w-3.5 h-3.5" />
            </span>
            <span
              className="text-xs font-bold text-slate-900 max-w-[70px] xs:max-w-[100px] sm:max-w-[140px] md:max-w-[170px] lg:max-w-[210px] truncate"
              title={jobInfo?.filename || jobId}
              suppressHydrationWarning
            >
              {isMounted && jobInfo?.filename
                ? jobInfo.filename
                : jobId
                ? jobId.slice(0, 8)
                : "TMUX Studio"}
            </span>
          </div>

          {/* Live Playback State Badge */}
          <span
            className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-semibold transition-all shrink-0 ${
              isPlaying
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200/90 shadow-2xs"
                : "bg-slate-200/60 text-slate-600 border border-slate-300/40"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                isPlaying ? "bg-emerald-500 animate-pulse" : "bg-slate-400"
              }`}
            />
            <span className="hidden xl:inline font-mono text-[9px] uppercase tracking-wider">
              {isPlaying ? "Playing" : "Paused"}
            </span>
          </span>
        </div>

        {/* Autosave Sync Status Indicator */}
        <div
          className="hidden 2xl:flex items-center gap-1 text-[11px] text-slate-400 font-mono pl-1"
          title={saveStatus}
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-500 shrink-0" />
          <span className="truncate max-w-[110px]">{saveStatus}</span>
        </div>
      </div>

      {/* =========================================================================
          ZONE 2: PRIMARY WORKSTATION MODE SWITCHER (CENTER HERO)
          ========================================================================= */}
      <div className="hidden md:flex flex-1 justify-center items-center px-1 sm:px-2 min-w-0">
        <nav
          aria-label="View Modes"
          className="flex items-center bg-slate-100/90 p-1 rounded-lg border border-slate-200/80 shadow-inner backdrop-blur-xs shrink-0"
        >
          {[
            {
              id: "script" as const,
              label: "Script",
              fullLabel: "Script Mode",
              icon: FileText,
              activeColor: "text-blue-600",
            },
            {
              id: "karaoke" as const,
              label: "Speeches",
              fullLabel: "Timestamped Speeches",
              icon: Layers,
              activeColor: "text-emerald-600",
            },
            {
              id: "reader" as const,
              label: "Teleprompter",
              fullLabel: "Teleprompter",
              icon: Tv,
              activeColor: "text-cyan-600",
            },
            {
              id: "topics" as const,
              label: "Topics",
              fullLabel: "Topic Flow",
              icon: Compass,
              activeColor: "text-sky-600",
            },
            {
              id: "intelligence" as const,
              label: "Briefing",
              fullLabel: "Executive AI Briefing",
              icon: Sparkles,
              activeColor: "text-amber-600",
            },
          ].map((mode) => {
            const Icon = mode.icon;
            const isActive = viewMode === mode.id;
            return (
              <button
                key={mode.id}
                onClick={() => onViewModeChange(mode.id)}
                className={`flex items-center gap-1.5 px-2.5 xl:px-3 py-1.5 text-xs rounded-lg transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "bg-white text-slate-900 font-semibold shadow-xs scale-[1.02]"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
                title={mode.fullLabel}
              >
                <Icon
                  className={`w-3.5 h-3.5 transition-transform ${
                    isActive ? `${mode.activeColor} scale-105` : "text-slate-400"
                  }`}
                />
                <span className="truncate">
                  <span className="inline lg:hidden">{mode.label}</span>
                  <span className="hidden lg:inline">{mode.fullLabel}</span>
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* =========================================================================
          ZONE 3: ESSENTIAL CONTROLS & WORKSPACE LAUNCHERS (RIGHT)
          ========================================================================= */}
      <div className="flex items-center gap-1.5 sm:gap-2 shrink-0 justify-end">
        {/* Undo / Redo Action Group */}
        {onUndo && (
          <div className="flex items-center rounded-lg border border-slate-200/80 bg-white shadow-2xs overflow-hidden">
            <button
              onClick={onUndo}
              disabled={!canUndo}
              className={`p-1.5 transition-all ${
                canUndo
                  ? "text-slate-700 hover:bg-slate-100 cursor-pointer active:scale-95"
                  : "text-slate-300 cursor-not-allowed"
              }`}
              title="Undo edit (⌘Z)"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </button>
            <div className="w-[1px] h-3.5 bg-slate-200" />
            <button
              onClick={onRedo}
              disabled={!canRedo}
              className={`p-1.5 transition-all ${
                canRedo
                  ? "text-slate-700 hover:bg-slate-100 cursor-pointer active:scale-95"
                  : "text-slate-300 cursor-not-allowed"
              }`}
              title="Redo edit (⌘⇧Z)"
            >
              <Redo2 className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Find & Replace Search Trigger */}
        <button
          onClick={onToggleSearch}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs transition-all shadow-2xs active:scale-95 cursor-pointer ${
            isSearchOpen
              ? "bg-slate-900 text-white border-slate-900"
              : "bg-white text-slate-700 border-slate-200/80 hover:bg-slate-50 hover:border-slate-300"
          }`}
          title="Find & Replace in transcript (Ctrl+F)"
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden sm:inline font-medium">Find</span>
          <kbd
            className={`text-[9px] font-mono px-1 py-0.2 rounded border transition-colors hidden md:inline ${
              isSearchOpen
                ? "bg-slate-800 border-slate-700 text-slate-300"
                : "bg-slate-100 border-slate-200 text-slate-500"
            }`}
          >
            ⌘F
          </kbd>
        </button>

        {/* Multi-Track Audio Mux Studio Trigger - Primary in White, Secondary with Green */}
        {onOpenMux && (
          <button
            onClick={onOpenMux}
            className="flex items-center gap-1.5 sm:gap-2 text-xs font-bold text-slate-800 px-2 sm:px-3.5 py-1.5 sm:py-2 rounded-lg bg-white hover:bg-emerald-50/50 border border-slate-200/90 hover:border-emerald-300/80 shadow-2xs hover:shadow-xs transition-all duration-150 active:scale-95 cursor-pointer ring-1 ring-emerald-500/15 group"
            title="Open Multi-Audio Track Mux Studio"
          >
            <div className="w-5 h-5 rounded-md bg-emerald-50 border border-emerald-200/80 flex items-center justify-center shrink-0 group-hover:scale-110 group-hover:bg-emerald-100/80 transition-all">
              <Layers className="w-3.5 h-3.5 text-emerald-600" />
            </div>
            <span className="tracking-wide font-extrabold text-slate-900 group-hover:text-emerald-700 transition-colors hidden xs:inline sm:inline">MUX</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse hidden sm:inline-block" />
          </button>
        )}

        {/* Optimized Export Dropdown Menu */}
        <div className="relative" ref={exportDropdownRef}>
          <button
            type="button"
            onClick={() => setIsExportOpen(!isExportOpen)}
            aria-expanded={isExportOpen}
            aria-haspopup="true"
            className={`flex items-center gap-1 sm:gap-1.5 text-xs font-semibold text-white px-2 sm:px-3 py-1.5 rounded-lg transition-all active:scale-95 cursor-pointer ${
              isExportOpen
                ? "bg-slate-800 shadow-md ring-2 ring-slate-900/15"
                : "bg-slate-900 hover:bg-slate-800 shadow-xs hover:shadow"
            }`}
          >
            <Download className="w-3.5 h-3.5 text-slate-300" />
            <span className="hidden xs:inline">Export</span>
            <ChevronDown
              className={`w-3 h-3 text-slate-400 transition-transform duration-200 ${
                isExportOpen ? "rotate-180" : ""
              }`}
            />
          </button>

          {/* Streamlined 6-Format Essential Menu */}
          {isExportOpen && (
            <div
              className="absolute right-0 mt-2 w-80 max-h-[85vh] overflow-y-auto bg-white/98 backdrop-blur-xl border border-slate-200/90 rounded-lg shadow-2xl p-2 z-50 animate-in fade-in-50 zoom-in-95 duration-150 origin-top-right ring-1 ring-slate-950/5 select-none"
              role="menu"
            >
              {/* Header info */}
              <div
                className="px-2.5 py-1.5 mb-1 border-b border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider"
                suppressHydrationWarning
              >
                <div className="flex items-center gap-1.5">
                  <img src="/tmux-icon.png" alt="TMUX" className="h-3 w-auto object-contain" />
                  <span className="text-slate-700 font-bold">TMUX Export</span>
                </div>
                <span
                  className="font-mono text-[9px] text-slate-500 max-w-[130px] truncate"
                  title={jobInfo?.filename}
                  suppressHydrationWarning
                >
                  {isMounted
                    ? jobInfo?.filename || (jobId ? jobId.slice(0, 8) : "")
                    : jobId
                    ? jobId.slice(0, 8)
                    : ""}
                </span>
              </div>

              {/* Section 1: Documents */}
              <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Documents
              </div>
              <div className="space-y-0.5">
                {/* Executive PDF */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/pdf`}
                  download={`${mediaStem}_transcript.pdf`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-rose-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-rose-50 border border-rose-100 text-rose-600 group-hover/item:scale-105 group-hover/item:bg-rose-100/70 transition-all shrink-0">
                      <FileText className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        Executive PDF
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        Formatted presentation with speaker colors
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-rose-100/90 text-rose-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    PDF
                  </span>
                </a>

                {/* Word Document */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/docx`}
                  download={`${mediaStem}_transcript.docx`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-blue-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-blue-50 border border-blue-100 text-blue-600 group-hover/item:scale-105 group-hover/item:bg-blue-100/70 transition-all shrink-0">
                      <FileText className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        Word Document
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        Editable rich text document (.docx)
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-blue-100/90 text-blue-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    DOCX
                  </span>
                </a>

                {/* Plain Text Transcript */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/txt`}
                  download={`${mediaStem}_transcript.txt`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-slate-100/70 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 group-hover/item:scale-105 group-hover/item:bg-slate-200/70 transition-all shrink-0">
                      <FileText className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        Plain Transcript
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        Clean timestamped dialogue text
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    TXT
                  </span>
                </a>
              </div>

              {/* Separator */}
              <div className="border-t border-slate-100 my-1.5 mx-1" />

              {/* Section 2: Subtitles & Data */}
              <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Captions &amp; Data
              </div>
              <div className="space-y-0.5">
                {/* SubRip Subtitles */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/srt`}
                  download={`${mediaStem}_transcript.srt`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-amber-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-amber-50 border border-amber-100 text-amber-600 group-hover/item:scale-105 group-hover/item:bg-amber-100/70 transition-all shrink-0">
                      <Film className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        SubRip Subtitles
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        Premiere, DaVinci &amp; YouTube captions
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-amber-100/90 text-amber-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    SRT
                  </span>
                </a>

                {/* WebVTT Captions */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/vtt`}
                  download={`${mediaStem}_transcript.vtt`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-cyan-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-cyan-50 border border-cyan-100 text-cyan-600 group-hover/item:scale-105 group-hover/item:bg-cyan-100/70 transition-all shrink-0">
                      <FileText className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        WebVTT Captions
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        HTML5 web video subtitle track
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-cyan-100/90 text-cyan-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    VTT
                  </span>
                </a>

                {/* Tabular CSV */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/csv`}
                  download={`${mediaStem}_transcript.csv`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-emerald-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-emerald-50 border border-emerald-100 text-emerald-600 group-hover/item:scale-105 group-hover/item:bg-emerald-100/70 transition-all shrink-0">
                      <FileSpreadsheet className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        Spreadsheet (CSV)
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        Timestamped table for Excel &amp; Sheets
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-emerald-100/90 text-emerald-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    CSV
                  </span>
                </a>
              </div>

              {/* Separator */}
              <div className="border-t border-slate-100 my-1.5 mx-1" />

              {/* Section 3: Audio Media */}
              <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                Audio Media
              </div>
              <div className="space-y-0.5">
                {/* MP3 Audio Export */}
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/mp3`}
                  download={`${mediaStem}.mp3`}
                  onClick={() => setIsExportOpen(false)}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-sky-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className="p-1.5 rounded-lg bg-sky-50 border border-sky-100 text-sky-600 group-hover/item:scale-105 group-hover/item:bg-sky-100/70 transition-all shrink-0">
                      <FileAudio className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex flex-col text-left min-w-0">
                      <span className="text-slate-900 font-semibold text-xs leading-snug">
                        MP3 Audio
                      </span>
                      <span className="text-[10px] text-slate-400 truncate">
                        High-quality 192kbps extracted audio
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] bg-sky-100/90 text-sky-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                    MP3
                  </span>
                </a>

                {/* Multi-Audio Muxer */}
                {onOpenMux && (
                  <button
                    onClick={() => {
                      setIsExportOpen(false);
                      onOpenMux();
                    }}
                    className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-emerald-50/60 active:scale-[0.99] transition-all group/item cursor-pointer text-left"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <span className="p-1.5 rounded-lg bg-emerald-50 border border-emerald-100 text-emerald-600 group-hover/item:scale-105 group-hover/item:bg-emerald-100/70 transition-all shrink-0">
                        <Layers className="w-3.5 h-3.5" />
                      </span>
                      <div className="flex flex-col text-left min-w-0">
                        <span className="text-slate-900 font-semibold text-xs leading-snug">
                          Multi-Audio Muxer
                        </span>
                        <span className="text-[10px] text-slate-400 truncate">
                          Package stems, dubs &amp; commentary
                        </span>
                      </div>
                    </div>
                    <span className="text-[9px] bg-emerald-100/90 text-emerald-800 px-1.5 py-0.5 rounded font-mono font-bold shrink-0 ml-2">
                      MUX
                    </span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Display Settings (Font Size & Playback Speed) */}
        {onToggleSettings && (
          <button
            type="button"
            onClick={onToggleSettings}
            className={`p-1.5 rounded-lg border transition-all shadow-2xs active:scale-95 cursor-pointer ${
              isSettingsOpen
                ? "bg-slate-100 text-slate-900 border-slate-300"
                : "text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border-slate-200/80"
            }`}
            title="Display & Typography Settings"
          >
            <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500" />
          </button>
        )}

        {/* AI & Engine Preferences */}
        {onOpenPreferences && (
          <button
            type="button"
            onClick={onOpenPreferences}
            className="p-1.5 rounded-lg border border-slate-200/80 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 shadow-2xs active:scale-95 cursor-pointer transition-all"
            title="Preferences & AI Engine Settings"
          >
            <Settings className="w-3.5 h-3.5 text-slate-500" />
          </button>
        )}

        {/* Right Dock Toggle Button */}
        {onToggleRightSidebar && (
          <button
            onClick={onToggleRightSidebar}
            className={`p-1.5 rounded-lg border transition-all shadow-2xs active:scale-95 cursor-pointer ${
              isRightSidebarOpen
                ? "bg-slate-100 text-slate-900 border-slate-300"
                : "text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-50 border-slate-200/80"
            }`}
            title={
              isRightSidebarOpen
                ? "Collapse Tools Inspector"
                : "Open Tools Inspector"
            }
          >
            <PanelRight
              className={`w-3.5 h-3.5 ${
                isRightSidebarOpen ? "text-blue-600" : "text-slate-500"
              }`}
            />
          </button>
        )}
      </div>
    </header>
  );
}
