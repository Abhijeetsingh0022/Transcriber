"use client";

import React, { useState } from "react";
import {
  Bookmark,
  BarChart2,
  SlidersHorizontal,
  Sparkles,
  Plus,
  Trash2,
  X,
  Clock,
  Eye,
  AlertCircle,
  FileText,
  PanelRightClose,
  Download,
  Sliders,
  Play,
  RotateCcw,
  Check,
  Search,
  Loader2,
  Users,
  UserCheck,
  Layers,
} from "lucide-react";
import {
  AudioAnalytics,
  AudioMarker,
  ABLoopState,
  FontSize,
} from "../types";
import { formatTime, API_BASE } from "../utils";

export type InspectorTab = "tools" | "insights" | "markers" | "tuning";

interface StudioInspectorProps {
  isOpen: boolean;
  onClose: () => void;
  activeTab: InspectorTab;
  onTabChange: (tab: InspectorTab) => void;

  // Markers
  markers: AudioMarker[];
  newMarkerText: string;
  newMarkerTag: "note" | "review" | "highlight";
  onChangeMarkerText: (text: string) => void;
  onChangeMarkerTag: (tag: "note" | "review" | "highlight") => void;
  onAddMarker: (time?: number, label?: string, tag?: "note" | "review" | "highlight") => void;
  onDeleteMarker: (id: string) => void;
  onSeekTo: (time: number) => void;
  currentTime: number;
  isPlaying: boolean;
  onTogglePlay: () => void;

  // Insights
  audioAnalytics: AudioAnalytics;
  totalWords: number;
  dialogueTurnsCount: number;
  topKeywords: { word: string; count: number }[];
  onSelectKeyword: (word: string) => void;

  // Tuning
  abLoop: ABLoopState;
  onSetAbLoopPoint: (point: "a" | "b", time: number) => void;
  onToggleAbLoop: () => void;
  onClearAbLoop: () => void;
  skipStep: number;
  onChangeSkipStep: (step: number) => void;

  // Tools & Quick Options
  fontSize: FontSize;
  onFontSizeChange: (size: FontSize) => void;
  showConfidence: boolean;
  onToggleConfidence: () => void;
  followPlayhead: boolean;
  onToggleFollow: () => void;
  onOpenTemplateModal: () => void;
  jobId: string;
  mediaStem: string;
  onIdentifySpeakers?: () => void;
  isIdentifyingSpeakers?: boolean;
  onOpenSpeakerModal?: () => void;
  audioRef?: React.RefObject<HTMLAudioElement | null>;
}

export function StudioInspector({
  isOpen,
  onClose,
  activeTab,
  onTabChange,

  markers,
  newMarkerText,
  newMarkerTag,
  onChangeMarkerText,
  onChangeMarkerTag,
  onAddMarker,
  onDeleteMarker,
  onSeekTo,
  currentTime,
  isPlaying,
  onTogglePlay,

  audioAnalytics,
  totalWords,
  dialogueTurnsCount,
  topKeywords,
  onSelectKeyword,

  abLoop,
  onSetAbLoopPoint,
  onToggleAbLoop,
  onClearAbLoop,
  skipStep,
  onChangeSkipStep,

  fontSize,
  onFontSizeChange,
  showConfidence,
  onToggleConfidence,
  followPlayhead,
  onToggleFollow,
  onOpenTemplateModal,
  jobId,
  mediaStem,
  onIdentifySpeakers,
  isIdentifyingSpeakers,
  onOpenSpeakerModal,
  audioRef,
}: StudioInspectorProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Mobile / Tablet Drawer Backdrop */}
      <div
        onClick={onClose}
        aria-hidden="true"
        className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs z-30 lg:hidden animate-in fade-in duration-200"
      />

      <aside className="fixed inset-y-0 right-0 z-40 w-[88vw] max-w-[340px] lg:relative lg:inset-auto lg:z-20 lg:w-[290px] xl:w-[320px] 2xl:w-[350px] h-full rounded-none lg:rounded-lg border-l lg:border border-slate-200/80 bg-white/98 lg:bg-white/95 backdrop-blur-md flex flex-col shrink-0 overflow-hidden select-none shadow-2xl lg:shadow-lg lg:shadow-slate-900/5 animate-in slide-in-from-right-4 duration-200">
      {/* 1. TOP HEADER & TABS SWITCHER */}
      <div className="border-b border-slate-200 bg-slate-50/90 pt-2 px-3 pb-0 shrink-0">
        <div className="flex items-center justify-between pb-2">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-bold uppercase text-slate-800 tracking-wider">
              Studio Tools
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 rounded-lg transition-colors"
            title="Collapse Right Sidebar"
          >
            <PanelRightClose className="w-4 h-4" />
          </button>
        </div>

        {/* Modern 4-Tab Segmented Bar */}
        <div className="p-1 bg-slate-200/70 rounded-lg grid grid-cols-4 gap-1 mb-2">
          {[
            { id: "tools" as const, label: "Tools", icon: Sparkles },
            { id: "insights" as const, label: "Stats", icon: BarChart2 },
            { id: "markers" as const, label: "Pins", icon: Bookmark, badge: markers.length },
            { id: "tuning" as const, label: "Tune", icon: SlidersHorizontal },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center justify-center gap-1 py-1.5 px-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                  isActive
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900 hover:bg-white/60"
                }`}
                title={tab.label}
              >
                <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
                <span className="text-[11px] truncate">{tab.label}</span>
                {tab.badge !== undefined && tab.badge > 0 && (
                  <span
                    className={`text-[9px] px-1 rounded-full font-mono font-bold leading-none ${
                      isActive ? "bg-blue-100 text-blue-700" : "bg-slate-300 text-slate-700"
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* 2. TAB CONTENT SCROLLABLE AREA */}
      <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-4 bg-white">
        {/* TAB 1: INSIGHTS & ANALYTICS */}
        {activeTab === "insights" && (
          <div className="space-y-4 animate-in fade-in-50 duration-150">
            <span className="text-xs font-bold uppercase text-slate-700 tracking-wider block">
              Speech Activity &amp; Pacing
            </span>

            {/* Speech vs Pause Dual Meter */}
            <div className="p-3.5 border border-slate-200 rounded-lg bg-slate-50/50 space-y-2.5">
              <div className="flex justify-between items-center text-xs">
                <span className="font-semibold text-slate-700">Speech Activity</span>
                <span className="font-mono text-slate-700 font-bold text-[11px]">
                  {audioAnalytics.speechPct}% Active
                </span>
              </div>
              <div className="w-full h-2.5 rounded-full bg-slate-200 flex overflow-hidden shadow-inner">
                <div
                  className="bg-gradient-to-r from-blue-600 to-cyan-500 h-full transition-all duration-700 ease-out"
                  style={{ width: `${audioAnalytics.speechPct}%` }}
                  title={`Speech: ${audioAnalytics.speechTime}s (${audioAnalytics.speechPct}%)`}
                />
                <div
                  className="bg-gradient-to-r from-amber-400 to-amber-500 h-full transition-all duration-700 ease-out"
                  style={{ width: `${audioAnalytics.pausePct}%` }}
                  title={`Pauses: ${audioAnalytics.pauseTime}s (${audioAnalytics.pausePct}%)`}
                />
              </div>
              <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-0.5">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-blue-600 inline-block shadow-2xs" />
                  Speech: <strong>{audioAnalytics.speechTime}s</strong>
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-400 inline-block shadow-2xs" />
                  Pauses: <strong>{audioAnalytics.pauseTime}s</strong>
                </span>
              </div>
            </div>

            {/* Quantitative Stats Grid */}
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 hover:border-slate-300 transition-all hover:shadow-2xs">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Total Words</span>
                <span className="text-base font-bold font-mono text-slate-900">
                  {totalWords.toLocaleString()}
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 hover:border-slate-300 transition-all hover:shadow-2xs">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Dialogue Turns</span>
                <span className="text-base font-bold font-mono text-slate-900">{dialogueTurnsCount}</span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 hover:border-slate-300 transition-all hover:shadow-2xs">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Avg Turn Length</span>
                <span className="text-base font-bold font-mono text-slate-900">
                  {audioAnalytics.avgTurnDuration}s
                </span>
              </div>
              <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 hover:border-slate-300 transition-all hover:shadow-2xs">
                <span className="text-[10px] text-slate-400 uppercase font-semibold block">Estimated Read</span>
                <span className="text-base font-bold font-mono text-slate-900">
                  ~{Math.max(1, Math.round(totalWords / 180))} min
                </span>
              </div>
            </div>

            {/* Prominent Keywords Cloud (Curated Top 8) */}
            {topKeywords.length > 0 && (
              <div className="p-3 border border-slate-200/90 rounded-lg bg-white space-y-2 shadow-2xs">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                  Top Keywords (Click to Find)
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {topKeywords.slice(0, 8).map((k) => (
                    <button
                      key={k.word}
                      onClick={() => onSelectKeyword(k.word)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-50 hover:bg-blue-50 hover:text-blue-700 border border-slate-200 text-xs transition-all active:scale-95 cursor-pointer"
                      title={`Find "${k.word}" in transcript`}
                    >
                      <span className="font-semibold text-slate-800">{k.word}</span>
                      <span className="text-[10px] text-slate-400 font-mono">({k.count})</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: MARKERS & BOOKMARKS */}
        {activeTab === "markers" && (
          <div className="space-y-3 animate-in fade-in-50 duration-150">
            <div className="flex items-center justify-between pb-0.5">
              <div>
                <span className="text-xs font-bold uppercase text-slate-700 tracking-wider">
                  Timeline Bookmarks
                </span>
                <span className="text-[10px] text-slate-400 font-mono ml-1.5">({markers.length})</span>
              </div>
              <button
                onClick={() => onAddMarker(currentTime, undefined, "note")}
                className="flex items-center gap-1 text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 px-2 py-1 rounded-lg hover:bg-blue-100 transition-all active:scale-95 shadow-2xs"
              >
                <Plus className="w-3 h-3 text-blue-600" />
                <span>Bookmark @ {formatTime(currentTime)}</span>
              </button>
            </div>

            {/* Quick Add Marker Form */}
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
              <input
                type="text"
                placeholder="Add custom note at current time (e.g. Verify word)..."
                value={newMarkerText}
                onChange={(e) => onChangeMarkerText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") onAddMarker();
                }}
                className="w-full bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 transition-colors"
              />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1">
                  {(["note", "review", "highlight"] as const).map((tag) => (
                    <button
                      key={tag}
                      onClick={() => onChangeMarkerTag(tag)}
                      className={`px-2 py-0.5 rounded-lg text-[10px] font-medium capitalize transition-all ${
                        newMarkerTag === tag
                          ? tag === "review"
                            ? "bg-amber-100 text-amber-800 font-bold shadow-2xs"
                            : tag === "highlight"
                            ? "bg-emerald-100 text-emerald-800 font-bold shadow-2xs"
                            : "bg-blue-100 text-blue-800 font-bold shadow-2xs"
                          : "text-slate-500 hover:bg-slate-200"
                      }`}
                    >
                      {tag}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => onAddMarker()}
                  className="px-2.5 py-1 bg-slate-900 text-white rounded-lg text-[11px] font-medium hover:bg-slate-800 active:scale-95 transition-all shadow-xs"
                >
                  Add Pin
                </button>
              </div>
            </div>

            {/* Markers List */}
            {markers.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-slate-200 rounded-lg text-slate-400 text-xs space-y-1">
                <Bookmark className="w-5 h-5 mx-auto text-slate-300" />
                <p className="font-medium text-slate-600">No markers created yet</p>
                <p className="text-[11px]">Press &apos;M&apos; while playing audio to drop a bookmark instantly.</p>
              </div>
            ) : (
              <div className="space-y-1.5">
                {markers.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between p-2.5 rounded-lg border border-slate-200 bg-white hover:border-blue-300 transition-all group hover:shadow-xs"
                  >
                    <button
                      onClick={() => {
                        onSeekTo(m.time);
                        if (!isPlaying) onTogglePlay();
                      }}
                      className="flex items-center gap-2 text-left flex-1 min-w-0"
                      title="Seek & play from this marker"
                    >
                      <span className="font-mono text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded-lg border border-blue-200 shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                        {formatTime(m.time)}
                      </span>
                      <span className="text-xs text-slate-800 font-medium truncate">{m.label}</span>
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded-lg uppercase font-bold shrink-0 ${
                          m.tag === "review"
                            ? "bg-amber-100 text-amber-800"
                            : m.tag === "highlight"
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {m.tag}
                      </span>
                    </button>
                    <button
                      onClick={() => onDeleteMarker(m.id)}
                      className="p-1 text-slate-400 hover:text-rose-600 opacity-60 group-hover:opacity-100 transition-all hover:scale-110"
                      title="Delete marker"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* TAB 3: TUNING & REPEAT WORKSTATION */}
        {activeTab === "tuning" && (
          <div className="space-y-4 animate-in fade-in-50 duration-150">
            <span className="text-xs font-bold uppercase text-slate-700 tracking-wider block">
              Audio &amp; Transport Tuning
            </span>

            {/* A-B Repeat Loop Range Controller */}
            <div className="p-3.5 border border-slate-200 rounded-lg bg-slate-50/50 space-y-2.5 text-xs">
              <div className="flex justify-between items-center">
                <span className="font-bold text-slate-800">A-B Repeat Section</span>
                <span className="text-[10px] text-slate-400">Loop snippet repeatedly</span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => onSetAbLoopPoint("a", currentTime)}
                  className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium hover:bg-slate-50 text-left transition-colors active:scale-98"
                >
                  <span className="text-[10px] text-slate-400 block uppercase">Point A (Start)</span>
                  <span className="font-mono font-bold text-slate-900">
                    {abLoop.a !== null ? formatTime(abLoop.a) : "Not set"}
                  </span>
                </button>

                <button
                  onClick={() => onSetAbLoopPoint("b", currentTime)}
                  className="px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-medium hover:bg-slate-50 text-left transition-colors active:scale-98"
                >
                  <span className="text-[10px] text-slate-400 block uppercase">Point B (End)</span>
                  <span className="font-mono font-bold text-slate-900">
                    {abLoop.b !== null ? formatTime(abLoop.b) : "Not set"}
                  </span>
                </button>
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  onClick={onToggleAbLoop}
                  disabled={abLoop.a === null || abLoop.b === null}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    abLoop.active
                      ? "bg-amber-500 text-white font-bold shadow-xs animate-pulse"
                      : "bg-slate-900 text-white hover:bg-slate-800 disabled:opacity-40"
                  }`}
                >
                  {abLoop.active ? "A-B Loop Active" : "Activate A-B Loop"}
                </button>

                {(abLoop.a !== null || abLoop.b !== null) && (
                  <button
                    onClick={onClearAbLoop}
                    className="text-[11px] text-slate-400 hover:text-rose-600 transition-colors"
                  >
                    Clear Loop
                  </button>
                )}
              </div>
            </div>

            {/* Skip Step Precision Selector */}
            <div className="p-3.5 border border-slate-200 rounded-lg bg-white space-y-2 text-xs">
              <span className="font-bold text-slate-800 block">Skip Step Increment</span>
              <div className="grid grid-cols-4 gap-1.5">
                {[1, 3, 5, 10].map((step) => (
                  <button
                    key={step}
                    onClick={() => onChangeSkipStep(step)}
                    className={`py-1.5 rounded-lg text-xs font-mono font-medium border transition-all active:scale-95 ${
                      skipStep === step
                        ? "bg-blue-50 text-blue-700 border-blue-300 font-bold shadow-2xs"
                        : "bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100"
                    }`}
                  >
                    &plusmn;{step}s
                  </button>
                ))}
              </div>
            </div>

            {/* Keyboard Reference Guide */}
            <div className="p-3 border border-slate-200 rounded-lg bg-slate-50/50 space-y-1.5 text-xs font-mono">
              <span className="font-sans font-bold text-slate-800 block mb-1">Editor Hotkeys</span>
              <div className="flex justify-between text-slate-600">
                <span>Space</span>
                <span className="text-slate-900 font-semibold">Play / Pause</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>J / L</span>
                <span className="text-slate-900 font-semibold">&plusmn;{skipStep}s Skip</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>[ / ]</span>
                <span className="text-slate-900 font-semibold">Prev / Next Turn</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>M</span>
                <span className="text-slate-900 font-semibold">Add Marker</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Ctrl + F</span>
                <span className="text-slate-900 font-semibold">Find &amp; Replace</span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: OPTIONS, AI TOOLS & EXPORTS */}
        {activeTab === "tools" && (
          <div className="space-y-3.5 animate-in fade-in-50 duration-150">
            {/* 1. Smart AI Character Identification Card */}
            <div className="p-3.5 border border-amber-200/80 rounded-lg bg-gradient-to-br from-amber-50/70 via-orange-50/40 to-amber-50/20 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-amber-500/15 flex items-center justify-center text-amber-700">
                    <Sparkles className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-900 block leading-tight">Character Intelligence</span>
                    <span className="text-[10px] text-amber-700/80 font-medium">Dual-Tier AI Engine</span>
                  </div>
                </div>
                <span className="text-[9px] bg-amber-100/90 text-amber-800 font-bold px-1.5 py-0.5 rounded-lg font-mono">
                  AI ACTOR
                </span>
              </div>
              <p className="text-[11px] text-slate-600 leading-snug">
                Detect Narrators, characters, and conversational addressees (who is speaking to whom).
              </p>
              <div className="space-y-1.5 pt-0.5">
                {onIdentifySpeakers && (
                  <button
                    onClick={onIdentifySpeakers}
                    disabled={isIdentifyingSpeakers}
                    className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-slate-900 hover:bg-slate-800 active:scale-[0.98] text-white rounded-lg text-xs font-semibold transition-all shadow-xs disabled:opacity-50 cursor-pointer"
                  >
                    {isIdentifyingSpeakers ? (
                      <Loader2 className="w-3.5 h-3.5 text-amber-400 animate-spin" />
                    ) : (
                      <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    )}
                    <span>{isIdentifyingSpeakers ? "Detecting Characters..." : "Identify Characters & Dialogue"}</span>
                  </button>
                )}
                {onOpenSpeakerModal && (
                  <button
                    onClick={onOpenSpeakerModal}
                    className="w-full flex items-center justify-center gap-1.5 py-1.5 px-3 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-lg text-xs font-medium transition-colors shadow-2xs cursor-pointer"
                  >
                    <Users className="w-3.5 h-3.5 text-blue-600" />
                    <span>Manage Speaker Roster</span>
                  </button>
                )}
              </div>
            </div>

            {/* 2. Script Templates & Publishing Hub */}
            <div className="p-3.5 border border-blue-200/80 rounded-lg bg-gradient-to-br from-blue-50/60 via-sky-50/40 to-white space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded-lg bg-blue-600/15 flex items-center justify-center text-blue-700">
                    <FileText className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-900 block leading-tight">Script Templates</span>
                    <span className="text-[10px] text-blue-700/80 font-medium">Broadcast &amp; Legal Formats</span>
                  </div>
                </div>
                <span className="text-[9px] bg-blue-100 text-blue-800 font-bold px-1.5 py-0.5 rounded-lg font-mono">
                  7 FORMATS
                </span>
              </div>
              <p className="text-[11px] text-slate-600 leading-snug">
                Format into Broadcast Dialogue, Hollywood Screenplay, Legal Deposition, or Podcast Notes.
              </p>
              <button
                onClick={onOpenTemplateModal}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 bg-blue-600 hover:bg-blue-700 active:scale-[0.98] text-white rounded-lg text-xs font-semibold transition-all shadow-xs cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Open Script Templates Hub</span>
              </button>
            </div>


            {/* 4. Workspace Toggles */}
            <div className="p-3 border border-slate-200/90 rounded-lg bg-white space-y-2 shadow-2xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Workspace Toggles
              </span>
              <div className="space-y-1.5">
                <button
                  onClick={onToggleConfidence}
                  className={`w-full flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer ${
                    showConfidence
                      ? "bg-amber-50/90 border-amber-200 text-amber-900"
                      : "border-slate-200/80 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs">
                    <AlertCircle className={`w-3.5 h-3.5 ${showConfidence ? "text-amber-600" : "text-slate-400"}`} />
                    <span className="font-medium">Confidence Heatmap</span>
                  </div>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-lg ${showConfidence ? "bg-amber-200/80 text-amber-900" : "bg-slate-100 text-slate-500"}`}>
                    {showConfidence ? "ON" : "OFF"}
                  </span>
                </button>

                <button
                  onClick={onToggleFollow}
                  className={`w-full flex items-center justify-between p-2 rounded-lg border transition-all cursor-pointer ${
                    followPlayhead
                      ? "bg-blue-50/90 border-blue-200 text-blue-900"
                      : "border-slate-200/80 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs">
                    <Eye className={`w-3.5 h-3.5 ${followPlayhead ? "text-blue-600" : "text-slate-400"}`} />
                    <span className="font-medium">Follow Playhead Auto-Scroll</span>
                  </div>
                  <span className={`text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-lg ${followPlayhead ? "bg-blue-200/80 text-blue-900" : "bg-slate-100 text-slate-500"}`}>
                    {followPlayhead ? "ON" : "OFF"}
                  </span>
                </button>
              </div>
            </div>

            {/* 4. Font Size Selector */}
            <div className="p-3 border border-slate-200/90 rounded-lg bg-white space-y-2 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Transcript Font Size
                </span>
                <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold">{fontSize}</span>
              </div>
              <div className="grid grid-cols-4 gap-1 bg-slate-100 p-1 rounded-lg">
                {(["sm", "base", "lg", "xl"] as const).map((s) => (
                  <button
                    key={s}
                    onClick={() => onFontSizeChange(s)}
                    className={`py-1 text-xs rounded-lg uppercase font-mono font-semibold transition-all cursor-pointer ${
                      fontSize === s
                        ? "bg-white text-slate-900 shadow-xs font-bold"
                        : "text-slate-500 hover:text-slate-800"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* 5. Quick Document Downloads */}
            <div className="p-3 border border-slate-200/90 rounded-lg bg-white space-y-2 shadow-2xs">
              <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Quick Document Downloads
              </span>
              <div className="grid grid-cols-2 gap-1.5 text-xs">
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/pdf`}
                  download={`${mediaStem}_section_flow.pdf`}
                  className="flex items-center justify-between p-2 rounded-lg border border-rose-200/80 bg-rose-50/30 hover:bg-rose-50 text-rose-700 font-semibold transition-colors"
                >
                  <span>PDF Report</span>
                  <span className="text-[9px] bg-rose-100 text-rose-800 px-1 py-0.2 rounded-lg font-mono font-bold">PDF</span>
                </a>
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/docx`}
                  download={`${mediaStem}_transcript.docx`}
                  className="flex items-center justify-between p-2 rounded-lg border border-blue-200/80 bg-blue-50/30 hover:bg-blue-50 text-blue-700 font-semibold transition-colors"
                >
                  <span>Word Doc</span>
                  <span className="text-[9px] bg-blue-100 text-blue-800 px-1 py-0.2 rounded-lg font-mono font-bold">DOCX</span>
                </a>
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/srt`}
                  download={`${mediaStem}_transcript.srt`}
                  className="flex items-center justify-between p-2 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-slate-100 text-slate-700 font-semibold transition-colors"
                >
                  <span>Subtitles</span>
                  <span className="text-[9px] bg-slate-200 text-slate-700 px-1 py-0.2 rounded-lg font-mono">SRT</span>
                </a>
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/vtt`}
                  download={`${mediaStem}_transcript.vtt`}
                  className="flex items-center justify-between p-2 rounded-lg border border-amber-200/80 bg-amber-50/30 hover:bg-amber-50 text-amber-700 font-semibold transition-colors"
                  title="WebVTT format for custom HTML5 video players"
                >
                  <span>Web Player</span>
                  <span className="text-[9px] bg-amber-100 text-amber-800 px-1 py-0.2 rounded-lg font-mono font-bold">VTT</span>
                </a>
                <a
                  href={`${API_BASE}/jobs/${jobId}/export/csv`}
                  download={`${mediaStem}_transcript.csv`}
                  className="flex items-center justify-between p-2 rounded-lg border border-emerald-200/80 bg-emerald-50/30 hover:bg-emerald-50 text-emerald-700 font-semibold transition-colors"
                >
                  <span>Spreadsheet</span>
                  <span className="text-[9px] bg-emerald-100 text-emerald-800 px-1 py-0.2 rounded-lg font-mono font-bold">CSV</span>
                </a>
              </div>
            </div>
          </div>
        )}

      </div>

      {/* 3. PINNED BOTTOM FOOTER */}
      <div className="h-11 px-4 py-2 border-t border-slate-200 bg-slate-50/95 backdrop-blur-xs flex items-center justify-between text-xs text-slate-500 shrink-0 font-mono">
        <span className="text-[11px] text-slate-400 font-semibold">TMUX Inspector</span>
        <button
          onClick={onOpenTemplateModal}
          className="text-[11px] text-blue-600 hover:underline font-sans font-medium flex items-center gap-1"
        >
          <Sparkles className="w-3 h-3" />
          <span>Templates</span>
        </button>
      </div>
    </aside>
    </>
  );
}
