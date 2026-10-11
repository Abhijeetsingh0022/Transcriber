"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Sparkles,
  X,
  FileText,
  Film,
  Scale,
  Mic,
  AlignLeft,
  Clock,
  ExternalLink,
  Download,
  Check,
  Copy,
  Search,
  Tv,
  Hash,
  WrapText,
  Type,
  SlidersHorizontal,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  FileCode2,
  Compass,
} from "lucide-react";
import { TemplateStyle, TimestampStyle, SpeakerCase } from "../types";
import { API_BASE } from "../utils";

interface TemplateModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  templateStyle: TemplateStyle;
  onSelectStyle: (style: TemplateStyle) => void;
  timestampStyle: TimestampStyle;
  onChangeTimestampStyle: (style: TimestampStyle) => void;
  speakerCase?: SpeakerCase;
  onChangeSpeakerCase?: (c: SpeakerCase) => void;
  includeStats: boolean;
  onToggleStats: (include: boolean) => void;
  renderedContent: string;
  copied: boolean;
  onCopy: () => void;
  onDownload: () => void;
  turnsCount: number;
  totalWords?: number;
  mediaStem?: string;
  duration?: number;
  speakersCount?: number;
}

interface TemplateCardMeta {
  id: TemplateStyle;
  title: string;
  tag: string;
  description: string;
  ext: "txt" | "md";
  icon: React.ElementType;
  accentColor: string;
  glowBorder: string;
  activeBg: string;
  badgeBg: string;
  iconColor: string;
}

const TEMPLATE_CARDS: TemplateCardMeta[] = [
  {
    id: "broadcast",
    title: "Broadcast Script",
    tag: "NEWS & MEDIA",
    description: "Two-column cues with timecode brackets & speech pacing metrics",
    ext: "txt",
    icon: Tv,
    accentColor: "border-sky-500",
    glowBorder: "ring-sky-500/40 shadow-sky-500/10",
    activeBg: "bg-sky-500/10",
    badgeBg: "bg-sky-500/20 text-sky-300 border-sky-500/30",
    iconColor: "text-sky-400",
  },
  {
    id: "screenplay",
    title: "Screenplay / Drama",
    tag: "HOLLYWOOD FORMAT",
    description: "Industry slugline, centered character cues, parentheticals & dialogue",
    ext: "txt",
    icon: Film,
    accentColor: "border-cyan-500",
    glowBorder: "ring-cyan-500/40 shadow-cyan-500/10",
    activeBg: "bg-cyan-500/10",
    badgeBg: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
    iconColor: "text-cyan-400",
  },
  {
    id: "legal",
    title: "Legal Deposition",
    tag: "COURT & COMPLIANCE",
    description: "Sequential line numbers, caption, appearances & certificate of verbatim",
    ext: "txt",
    icon: Scale,
    accentColor: "border-amber-500",
    glowBorder: "ring-amber-500/40 shadow-amber-500/10",
    activeBg: "bg-amber-500/10",
    badgeBg: "bg-amber-500/20 text-amber-300 border-amber-500/30",
    iconColor: "text-amber-400",
  },
  {
    id: "podcast",
    title: "Show Notes & Chapters",
    tag: "YOUTUBE & SPOTIFY",
    description: "Markdown format with chapter timestamps, summary hooks & dialogue",
    ext: "md",
    icon: Mic,
    accentColor: "border-emerald-500",
    glowBorder: "ring-emerald-500/40 shadow-emerald-500/10",
    activeBg: "bg-emerald-500/10",
    badgeBg: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
    iconColor: "text-emerald-400",
  },
  {
    id: "dialogue",
    title: "Clean Dialogue",
    tag: "DISTILLED PROSE",
    description: "Minimalist speaker conversation without timestamps or technical noise",
    ext: "txt",
    icon: AlignLeft,
    accentColor: "border-teal-500",
    glowBorder: "ring-teal-500/40 shadow-teal-500/10",
    activeBg: "bg-teal-500/10",
    badgeBg: "bg-teal-500/20 text-teal-300 border-teal-500/30",
    iconColor: "text-teal-400",
  },
  {
    id: "topic_flow",
    title: "Topic-Wise Video Flow",
    tag: "SECTIONS & TOPICS",
    description: "Pedagogical flow table with section groupings, slide topics, coral timecodes & speaker transcript",
    ext: "md",
    icon: Compass,
    accentColor: "border-blue-500",
    glowBorder: "ring-blue-500/40 shadow-blue-500/10",
    activeBg: "bg-blue-500/10",
    badgeBg: "bg-blue-500/20 text-blue-300 border-blue-500/30",
    iconColor: "text-blue-400",
  },
];

export function TemplateModal({
  isOpen,
  onClose,
  jobId,
  templateStyle,
  onSelectStyle,
  timestampStyle,
  onChangeTimestampStyle,
  speakerCase = "upper",
  onChangeSpeakerCase,
  includeStats,
  onToggleStats,
  renderedContent,
  copied,
  onCopy,
  onDownload,
  turnsCount,
  totalWords,
  mediaStem,
  duration,
  speakersCount = 1,
}: TemplateModalProps) {
  // Modal Local Customization States
  const [searchQuery, setSearchQuery] = useState("");
  const [showLineNumbers, setShowLineNumbers] = useState(false);
  const [wrapLines, setWrapLines] = useState(true);
  const [fontSize, setFontSize] = useState<"sm" | "base" | "lg">("sm");
  const [fontFamily, setFontFamily] = useState<"mono" | "sans">("mono");
  const previewRef = useRef<HTMLDivElement>(null);

  // Close on Escape Key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Derived content stats
  const characterCount = useMemo(() => renderedContent.length, [renderedContent]);
  const estimatedWords = useMemo(() => {
    if (totalWords && totalWords > 0) return totalWords;
    return renderedContent.trim().split(/\s+/).filter(Boolean).length;
  }, [totalWords, renderedContent]);

  const readingTimeMinutes = useMemo(() => {
    return Math.max(1, Math.ceil(estimatedWords / 150));
  }, [estimatedWords]);

  // Line splitting for line numbers & search
  const contentLines = useMemo(() => {
    return renderedContent.split("\n");
  }, [renderedContent]);

  // Search match count
  const searchMatchesCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const q = searchQuery.toLowerCase();
    let matches = 0;
    for (const line of contentLines) {
      let pos = line.toLowerCase().indexOf(q);
      while (pos !== -1) {
        matches++;
        pos = line.toLowerCase().indexOf(q, pos + q.length);
      }
    }
    return matches;
  }, [searchQuery, contentLines]);

  if (!isOpen) return null;

  const currentTemplate = TEMPLATE_CARDS.find((t) => t.id === templateStyle) || TEMPLATE_CARDS[0];

  const fontSizeClass =
    fontSize === "sm" ? "text-xs leading-relaxed" : fontSize === "base" ? "text-sm leading-relaxed" : "text-base leading-loose";

  return (
    <div
      className="fixed inset-0 bg-slate-950/80 backdrop-blur-md flex items-center justify-center z-50 p-3 sm:p-5 md:p-6 animate-in fade-in duration-200"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-slate-900 border border-slate-700/80 rounded-lg shadow-2xl max-w-6xl w-full flex flex-col h-[94dvh] sm:h-[92vh] max-h-[920px] overflow-hidden text-slate-100 ring-1 ring-white/10">
        {/* ========================================================= */}
        {/* 1. STUDIO HEADER                                          */}
        {/* ========================================================= */}
        <div className="p-3.5 sm:p-4 px-4 sm:px-6 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between gap-3 select-none shrink-0">
          <div className="flex items-center gap-2.5 sm:gap-3 min-w-0">
            <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-gradient-to-tr from-blue-600 via-sky-500 to-cyan-400 flex items-center justify-center shadow-md shadow-blue-500/20 text-white shrink-0">
              <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                <h3 className="font-semibold text-slate-100 text-sm sm:text-base tracking-tight truncate">
                  Transcription Script Studio
                </h3>
                <span className="px-1.5 sm:px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-medium tracking-wide bg-blue-500/15 text-blue-400 border border-blue-500/30 uppercase shrink-0">
                  Multi-Template Engine
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-slate-400 truncate hidden sm:block">
                Industry-standard screenplays, legal depositions, broadcast scripts & podcast show notes
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 shrink-0">
            <span className="hidden md:inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-mono text-slate-400 bg-slate-800/80 border border-slate-700">
              <span>ESC</span>
              <span className="text-slate-500">to close</span>
            </span>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white hover:bg-slate-800 p-1.5 sm:p-2 rounded-lg transition-colors cursor-pointer"
              title="Close modal (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ========================================================= */}
        {/* 2. TEMPLATE ARCHETYPE GALLERY CARDS                       */}
        {/* ========================================================= */}
        <div className="p-3 sm:p-4 px-4 sm:px-6 border-b border-slate-800 bg-slate-900/50 shrink-0">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase flex items-center gap-1.5">
              <FileCode2 className="w-3.5 h-3.5 text-blue-400" />
              <span>Choose Script Archetype</span>
            </span>
            <span className="text-xs text-slate-500 hidden sm:inline">
              Active: <span className="font-medium text-slate-300">{currentTemplate.title}</span> (.{currentTemplate.ext})
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 sm:gap-2.5">
            {TEMPLATE_CARDS.map((card) => {
              const Icon = card.icon;
              const isSelected = templateStyle === card.id;

              return (
                <button
                  key={card.id}
                  onClick={() => onSelectStyle(card.id)}
                  className={`text-left p-3 rounded-lg border transition-all duration-200 relative group flex flex-col justify-between ${
                    isSelected
                      ? `${card.accentColor} ${card.activeBg} ring-2 ${card.glowBorder} shadow-lg`
                      : "border-slate-800 bg-slate-800/40 hover:border-slate-700 hover:bg-slate-800/80"
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div
                        className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                          isSelected ? "bg-slate-900/90 shadow-xs" : "bg-slate-800/80"
                        }`}
                      >
                        <Icon className={`w-4 h-4 ${isSelected ? card.iconColor : "text-slate-400"}`} />
                      </div>
                      <span
                        className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-lg border uppercase tracking-wider ${
                          isSelected ? card.badgeBg : "bg-slate-800 text-slate-400 border-slate-700"
                        }`}
                      >
                        {card.ext.toUpperCase()}
                      </span>
                    </div>

                    <div className="font-semibold text-xs text-slate-200 group-hover:text-white transition-colors">
                      {card.title}
                    </div>
                    <div className="text-[11px] text-slate-400 leading-snug mt-1 line-clamp-2">
                      {card.description}
                    </div>
                  </div>

                  {isSelected && (
                    <div className="mt-2.5 pt-2 border-t border-slate-700/50 flex items-center justify-between text-[10px] text-slate-300 font-medium">
                      <span className="flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        Selected
                      </span>
                      <ChevronRight className="w-3 h-3 text-slate-400" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* ========================================================= */}
        {/* 3. FORMATTING & VIEWER TUNING TOOLBAR                     */}
        {/* ========================================================= */}
        <div className="px-6 py-2.5 border-b border-slate-800 bg-slate-900 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0 select-none">
          {/* Left: Script Format Options */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Timestamp Style Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-800/70 border border-slate-700/80 px-2.5 py-1 rounded-lg">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-slate-400 font-medium">Timecode:</span>
              <select
                value={timestampStyle}
                onChange={(e) => onChangeTimestampStyle(e.target.value as TimestampStyle)}
                className="bg-transparent text-slate-200 font-medium focus:outline-none cursor-pointer pr-1"
              >
                <option value="range" className="bg-slate-800 text-slate-200">
                  Range [00:00:00 - 00:00:06]
                </option>
                <option value="short_range" className="bg-slate-800 text-slate-200">
                  Short Range [00:00 - 00:06]
                </option>
                <option value="single" className="bg-slate-800 text-slate-200">
                  Single Marker [00:00:00]
                </option>
                <option value="short" className="bg-slate-800 text-slate-200">
                  Short Marker [00:00]
                </option>
                <option value="ms" className="bg-slate-800 text-slate-200">
                  Milliseconds [00:00.800]
                </option>
                <option value="none" className="bg-slate-800 text-slate-200">
                  Omit Timestamps
                </option>
              </select>
            </div>

            {/* Speaker Casing Toggle */}
            {onChangeSpeakerCase && (
              <div className="flex items-center gap-1 bg-slate-800/70 border border-slate-700/80 p-0.5 rounded-lg">
                <button
                  type="button"
                  onClick={() => onChangeSpeakerCase("upper")}
                  className={`px-2 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
                    speakerCase === "upper"
                      ? "bg-slate-700 text-white shadow-xs"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="Render speakers in UPPERCASE (e.g. SARAH:)"
                >
                  UPPER
                </button>
                <button
                  type="button"
                  onClick={() => onChangeSpeakerCase("title")}
                  className={`px-2 py-1 rounded-lg text-[11px] font-semibold transition-colors ${
                    speakerCase === "title"
                      ? "bg-slate-700 text-white shadow-xs"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                  title="Render speakers in Natural Title Case (e.g. Sarah:)"
                >
                  Title
                </button>
              </div>
            )}

            {/* Stats / WPM Toggle */}
            <label className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-700/80 bg-slate-800/70 text-slate-300 hover:text-white cursor-pointer transition-colors">
              <input
                type="checkbox"
                checked={includeStats}
                onChange={(e) => onToggleStats(e.target.checked)}
                className="rounded-lg accent-blue-500 cursor-pointer"
              />
              <span className="font-medium text-slate-300">Pacing (WPM & Secs)</span>
            </label>
          </div>

          {/* Right: In-Viewer Controls (Search, Line Numbers, Wrap, Font) */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Live Script Search */}
            <div className="relative flex items-center">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Find in script..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-800/80 border border-slate-700/80 rounded-lg pl-8 pr-16 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 w-36 sm:w-48 transition-all"
              />
              {searchQuery && (
                <div className="absolute right-2 flex items-center gap-1">
                  <span className="text-[10px] font-mono text-slate-400">
                    {searchMatchesCount}
                  </span>
                  <button
                    onClick={() => setSearchQuery("")}
                    className="text-slate-400 hover:text-white"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>

            {/* Line Numbers Toggle */}
            <button
              onClick={() => setShowLineNumbers(!showLineNumbers)}
              className={`p-1.5 rounded-lg border transition-colors flex items-center gap-1 ${
                showLineNumbers
                  ? "bg-blue-600/20 border-blue-500/50 text-blue-300"
                  : "bg-slate-800/70 border-slate-700/80 text-slate-400 hover:text-slate-200"
              }`}
              title="Toggle line numbers gutter"
            >
              <Hash className="w-3.5 h-3.5" />
            </button>

            {/* Wrap Lines Toggle */}
            <button
              onClick={() => setWrapLines(!wrapLines)}
              className={`p-1.5 rounded-lg border transition-colors flex items-center gap-1 ${
                wrapLines
                  ? "bg-blue-600/20 border-blue-500/50 text-blue-300"
                  : "bg-slate-800/70 border-slate-700/80 text-slate-400 hover:text-slate-200"
              }`}
              title={wrapLines ? "Disable soft wrap" : "Enable soft wrap"}
            >
              <WrapText className="w-3.5 h-3.5" />
            </button>

            {/* Font Family Switcher */}
            <button
              onClick={() => setFontFamily(fontFamily === "mono" ? "sans" : "mono")}
              className="px-2 py-1 rounded-lg border border-slate-700/80 bg-slate-800/70 text-slate-300 hover:text-white font-mono text-[11px]"
              title="Toggle monospace vs sans-serif typography"
            >
              {fontFamily === "mono" ? "MONO" : "SANS"}
            </button>

            {/* Font Size Adjusters */}
            <div className="flex items-center bg-slate-800/70 border border-slate-700/80 rounded-lg p-0.5">
              <button
                onClick={() => setFontSize(fontSize === "lg" ? "base" : "sm")}
                className="p-1 text-slate-400 hover:text-white rounded-lg"
                title="Decrease font size"
              >
                <ZoomOut className="w-3 h-3" />
              </button>
              <button
                onClick={() => setFontSize(fontSize === "sm" ? "base" : "lg")}
                className="p-1 text-slate-400 hover:text-white rounded-lg"
                title="Increase font size"
              >
                <ZoomIn className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>

        {/* ========================================================= */}
        {/* 4. LIVE FORMATTED SCRIPT PREVIEW STAGE                    */}
        {/* ========================================================= */}
        <div
          ref={previewRef}
          className="flex-1 overflow-auto bg-slate-950 p-4 sm:p-6 select-text relative font-mono text-slate-200"
        >
          {contentLines.length === 0 || !renderedContent ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-500">
              <FileText className="w-10 h-10 mb-2 opacity-40" />
              <p className="text-sm">No transcription dialogue turns available for this job.</p>
            </div>
          ) : showLineNumbers ? (
            <div className={`flex gap-4 ${fontFamily === "mono" ? "font-mono" : "font-sans"} ${fontSizeClass}`}>
              {/* Line Numbers Gutter */}
              <div className="select-none text-slate-600 text-right font-mono border-r border-slate-800 pr-3 shrink-0">
                {contentLines.map((_, idx) => (
                  <div key={idx}>{idx + 1}</div>
                ))}
              </div>

              {/* Text Lines */}
              <div className={`flex-1 ${wrapLines ? "whitespace-pre-wrap break-words" : "whitespace-pre overflow-x-auto"}`}>
                {contentLines.map((line, idx) => {
                  if (searchQuery.trim() && line.toLowerCase().includes(searchQuery.toLowerCase())) {
                    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
                    const parts = line.split(regex);
                    return (
                      <div key={idx}>
                        {parts.map((p, pIdx) =>
                          p.toLowerCase() === searchQuery.toLowerCase() ? (
                            <mark
                              key={pIdx}
                              className="bg-amber-400 text-slate-950 font-bold px-0.5 rounded-xs"
                            >
                              {p}
                            </mark>
                          ) : (
                            <span key={pIdx}>{p}</span>
                          )
                        )}
                      </div>
                    );
                  }
                  return <div key={idx}>{line || "\u00A0"}</div>;
                })}
              </div>
            </div>
          ) : (
            <pre
              className={`${wrapLines ? "whitespace-pre-wrap break-words" : "whitespace-pre"} ${
                fontFamily === "mono" ? "font-mono" : "font-sans"
              } ${fontSizeClass} select-text`}
            >
              {searchQuery.trim() ? (
                contentLines.map((line, idx) => {
                  if (line.toLowerCase().includes(searchQuery.toLowerCase())) {
                    const regex = new RegExp(`(${searchQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi");
                    const parts = line.split(regex);
                    return (
                      <span key={idx}>
                        {parts.map((p, pIdx) =>
                          p.toLowerCase() === searchQuery.toLowerCase() ? (
                            <mark
                              key={pIdx}
                              className="bg-amber-400 text-slate-950 font-bold px-0.5 rounded-xs"
                            >
                              {p}
                            </mark>
                          ) : (
                            <span key={pIdx}>{p}</span>
                          )
                        )}
                        {"\n"}
                      </span>
                    );
                  }
                  return (
                    <span key={idx}>
                      {line}
                      {"\n"}
                    </span>
                  );
                })
              ) : (
                renderedContent
              )}
            </pre>
          )}
        </div>

        {/* ========================================================= */}
        {/* 5. TELEMETRY STRIP & EXPORT ACTIONS FOOTER                */}
        {/* ========================================================= */}
        <div className="p-3.5 px-6 border-t border-slate-800 bg-slate-900/95 flex flex-wrap items-center justify-between gap-4 text-xs select-none shrink-0">
          {/* Telemetry Stats */}
          <div className="flex flex-wrap items-center gap-3 text-slate-400">
            <span className="flex items-center gap-1 font-medium text-slate-300">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              {turnsCount} Turns
            </span>
            <span className="text-slate-600">&bull;</span>
            <span>{estimatedWords.toLocaleString()} Words</span>
            <span className="text-slate-600">&bull;</span>
            <span>{characterCount.toLocaleString()} Chars</span>
            <span className="text-slate-600">&bull;</span>
            <span>~{readingTimeMinutes} min read</span>
            {speakersCount > 1 && (
              <>
                <span className="text-slate-600">&bull;</span>
                <span>{speakersCount} Speakers</span>
              </>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5">
            {/* Interactive & Printable HTML View */}
            <a
              href={templateStyle === "topic_flow" ? `${API_BASE}/jobs/${jobId}/export/topic_flow` : `${API_BASE}/jobs/${jobId}/export/script_html`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg font-medium transition-colors"
              title="Open print-ready, formatted HTML script in new tab (Cmd+P ready)"
            >
              <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
              <span>Printable HTML</span>
            </a>

            {/* Direct Download Button */}
            <button
              onClick={onDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-200 hover:text-white rounded-lg font-medium transition-colors"
              title={`Download as .${currentTemplate.ext} file`}
            >
              <Download className="w-3.5 h-3.5 text-slate-400" />
              <span>Download .{currentTemplate.ext}</span>
            </button>

            {/* Copy Script CTA */}
            <button
              onClick={onCopy}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg font-semibold transition-all shadow-md ${
                copied
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-500/20"
                  : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-500/20 hover:shadow-blue-500/30"
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-white" />
                  <span>Copied to Clipboard!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy Formatted Script</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
