"use client";

import React from "react";
import {
  Users,
  UserCheck,
  Check,
  X,
  Edit2,
  ArrowRightLeft,
  Sparkles,
  Loader2,
  Sliders,
} from "lucide-react";
import {
  AudioAnalytics,
  AudioMarker,
  DialogueTurn,
  SidebarTab,
  SpeakerStat,
  ABLoopState,
  WaveformBar,
} from "../types";
import { AudioDeck } from "./AudioDeck";

interface WorkstationDockProps {
  jobId: string;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  currentTime: number;
  duration: number;
  effectiveDuration: number;
  isPlaying: boolean;
  playbackSpeed: number;
  volume: number;
  isMuted: boolean;
  isLoopingTurn: boolean;
  loopTurnRange: { start: number; end: number } | null;
  abLoop: ABLoopState;
  currentActiveTurn: DialogueTurn | null;
  waveformBars: WaveformBar[];
  hoveredWaveTime: { time: number; xPercent: number; speakerName?: string } | null;
  skipStep: number;
  followPlayhead: boolean;
  onTimeUpdate: () => void;
  onLoadedMetadata: () => void;
  onDurationChange: () => void;
  onEnded: () => void;
  onTogglePlay: () => void;
  onSeekTo: (time: number) => void;
  onSkipSeconds: (sec: number) => void;
  onJumpPreviousTurn: () => void;
  onJumpNextTurn: () => void;
  onLoopTurn: (turn: DialogueTurn) => void;
  onToggleLoopTurn: () => void;
  onAddMarker: (time?: number, label?: string, tag?: "note" | "review" | "highlight") => void;
  onSetSpeed: (spd: number) => void;
  onVolumeChange: (vol: number) => void;
  onToggleMute: () => void;
  onToggleFollow: () => void;
  onWaveformMouseMove: (e: React.MouseEvent<HTMLDivElement>) => void;
  onWaveformMouseLeave: () => void;
  onWaveformClick: (e: React.MouseEvent<HTMLDivElement>) => void;
  waveformRef: React.RefObject<HTMLDivElement | null>;

  // Dock Tabs State & Handlers
  sidebarTab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
  speakerStats: SpeakerStat[];
  selectedSpeakerFilter: string | null;
  onToggleSpeakerFilter: (label: string | null) => void;
  onOpenSpeakerModal: () => void;
  inlineRenameLabel: string | null;
  inlineRenameVal: string;
  onStartInlineRename: (label: string, name: string) => void;
  onCancelInlineRename: () => void;
  onSaveInlineRename: (label: string, name: string) => void;
  onChangeInlineRenameVal: (val: string) => void;
  colorPickerLabel: string | null;
  onToggleColorPicker: (label: string | null) => void;
  onChangeSpeakerColor: (label: string, hex: string) => void;
  mergeSourceLabel: string | null;
  mergeTargetLabel: string;
  onStartMerge: (label: string) => void;
  onCancelMerge: () => void;
  onChangeMergeTarget: (target: string) => void;
  onConfirmMerge: (source: string, target: string) => void;
  onIdentifySpeakers?: () => void;
  isIdentifyingSpeakers?: boolean;

  // Markers
  markers: AudioMarker[];
  newMarkerText: string;
  newMarkerTag: "note" | "review" | "highlight";
  onChangeMarkerText: (text: string) => void;
  onChangeMarkerTag: (tag: "note" | "review" | "highlight") => void;
  onDeleteMarker: (id: string) => void;

  // Insights
  audioAnalytics: AudioAnalytics;
  totalWords: number;
  dialogueTurnsCount: number;
  topKeywords: { word: string; count: number }[];
  onSelectKeyword: (word: string) => void;

  // Tuning
  onSetAbLoopPoint: (point: "a" | "b", time: number) => void;
  onToggleAbLoop: () => void;
  onClearAbLoop: () => void;
  onChangeSkipStep: (step: number) => void;

  // Dock Footer
  saveStatus: string;
  isOpen?: boolean;
  onClose?: () => void;
}

export function WorkstationDock({
  jobId,
  audioRef,
  currentTime,
  duration,
  effectiveDuration,
  isPlaying,
  playbackSpeed,
  volume,
  isMuted,
  isLoopingTurn,
  loopTurnRange,
  abLoop,
  currentActiveTurn,
  waveformBars,
  hoveredWaveTime,
  skipStep,
  followPlayhead,
  onTimeUpdate,
  onLoadedMetadata,
  onDurationChange,
  onEnded,
  onTogglePlay,
  onSeekTo,
  onSkipSeconds,
  onJumpPreviousTurn,
  onJumpNextTurn,
  onLoopTurn,
  onToggleLoopTurn,
  onAddMarker,
  onSetSpeed,
  onVolumeChange,
  onToggleMute,
  onToggleFollow,
  onWaveformMouseMove,
  onWaveformMouseLeave,
  onWaveformClick,
  waveformRef,

  sidebarTab,
  onTabChange,
  speakerStats,
  selectedSpeakerFilter,
  onToggleSpeakerFilter,
  onOpenSpeakerModal,
  inlineRenameLabel,
  inlineRenameVal,
  onStartInlineRename,
  onCancelInlineRename,
  onSaveInlineRename,
  onChangeInlineRenameVal,
  colorPickerLabel,
  onToggleColorPicker,
  onChangeSpeakerColor,
  mergeSourceLabel,
  mergeTargetLabel,
  onStartMerge,
  onCancelMerge,
  onChangeMergeTarget,
  onConfirmMerge,

  markers,
  newMarkerText,
  newMarkerTag,
  onChangeMarkerText,
  onChangeMarkerTag,
  onDeleteMarker,

  audioAnalytics,
  totalWords,
  dialogueTurnsCount,
  topKeywords,
  onSelectKeyword,

  onSetAbLoopPoint,
  onToggleAbLoop,
  onClearAbLoop,
  onChangeSkipStep,

  saveStatus,
  isOpen = true,
  onClose,
  onIdentifySpeakers,
  isIdentifyingSpeakers,
}: WorkstationDockProps) {
  // 100% Purple-Free High-Contrast Studio Palette
  const COLOR_PALETTE = [
    "#2563eb", // Royal Blue
    "#10b981", // Emerald
    "#0284c7", // Sky Blue
    "#f59e0b", // Amber
    "#0d9488", // Teal
    "#06b6d4", // Cyan
    "#f97316", // Orange
    "#64748b", // Slate
  ];

  if (!isOpen) return null;

  return (
    <>
      {/* Mobile / Tablet Drawer Backdrop */}
      <div
        onClick={onClose}
        aria-hidden="true"
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-30 lg:hidden animate-in fade-in duration-200"
      />

      <aside className="fixed inset-y-0 left-0 z-40 w-[88vw] max-w-[340px] lg:relative lg:inset-auto lg:z-20 lg:w-[320px] xl:w-[340px] 2xl:w-[360px] h-full rounded-none lg:rounded-xl border-r lg:border border-slate-200/90 bg-white shadow-2xl lg:shadow-sm flex flex-col shrink-0 overflow-hidden select-none animate-in slide-in-from-left-4 duration-200">
        {/* 1. TOP PINNED SECTION: AUDIO DECK CONSOLE */}
        <AudioDeck
          jobId={jobId}
          audioRef={audioRef}
          currentTime={currentTime}
          duration={duration}
          effectiveDuration={effectiveDuration}
          isPlaying={isPlaying}
          playbackSpeed={playbackSpeed}
          volume={volume}
          isMuted={isMuted}
          isLoopingTurn={isLoopingTurn}
          loopTurnRange={loopTurnRange}
          abLoop={abLoop}
          currentActiveTurn={currentActiveTurn}
          waveformBars={waveformBars}
          hoveredWaveTime={hoveredWaveTime}
          skipStep={skipStep}
          followPlayhead={followPlayhead}
          onTimeUpdate={onTimeUpdate}
          onLoadedMetadata={onLoadedMetadata}
          onDurationChange={onDurationChange}
          onEnded={onEnded}
          onTogglePlay={onTogglePlay}
          onSeekTo={onSeekTo}
          onSkipSeconds={onSkipSeconds}
          onJumpPreviousTurn={onJumpPreviousTurn}
          onJumpNextTurn={onJumpNextTurn}
          onLoopTurn={onLoopTurn}
          onToggleLoopTurn={onToggleLoopTurn}
          onAddMarker={onAddMarker}
          onSetSpeed={onSetSpeed}
          onVolumeChange={onVolumeChange}
          onToggleMute={onToggleMute}
          onToggleFollow={onToggleFollow}
          onWaveformMouseMove={onWaveformMouseMove}
          onWaveformMouseLeave={onWaveformMouseLeave}
          onWaveformClick={onWaveformClick}
          waveformRef={waveformRef}
          onCollapse={onClose}
        />

        {/* 2. DOCK SPEAKERS ROSTER HEADER */}
        <div className="flex items-center justify-between border-b border-slate-200/80 bg-slate-50/80 px-3.5 sm:px-4 py-2.5 shrink-0">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-blue-600" />
            <span className="text-xs font-bold text-slate-900 tracking-wide">
              Speakers
            </span>
            <span className="text-[10px] text-slate-600 font-mono font-bold bg-white border border-slate-200 px-2 py-0.5 rounded-full shadow-2xs">
              {speakerStats.length}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {selectedSpeakerFilter && (
              <button
                onClick={() => onToggleSpeakerFilter(null)}
                className="text-[11px] text-blue-600 hover:text-blue-700 font-semibold cursor-pointer mr-1 hover:underline"
              >
                Clear Filter
              </button>
            )}

            {onIdentifySpeakers && (
              <button
                onClick={onIdentifySpeakers}
                disabled={isIdentifyingSpeakers}
                className="text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-blue-200/80 transition-colors shadow-2xs disabled:opacity-50 cursor-pointer"
                title="Auto-detect speaker roles using AI reasoner"
              >
                {isIdentifyingSpeakers ? (
                  <Loader2 className="w-3 h-3 text-blue-600 animate-spin" />
                ) : (
                  <Sparkles className="w-3 h-3 text-blue-600" />
                )}
                <span>Auto-Detect</span>
              </button>
            )}

            <button
              onClick={onOpenSpeakerModal}
              className="text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-slate-200 transition-colors shadow-2xs cursor-pointer"
              title="Manage and batch rename speakers"
            >
              <UserCheck className="w-3.5 h-3.5 text-blue-600" />
              <span>Manage</span>
            </button>
          </div>
        </div>

        {/* 3. DOCK CONTENT AREA: SPEAKERS ROSTER */}
        <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-3.5 space-y-2.5 bg-slate-50/30">
          <div className="space-y-2.5">
            {speakerStats.map((spk) => {
              const isFiltered = selectedSpeakerFilter === spk.speaker_label;
              const isEditing = inlineRenameLabel === spk.speaker_label;
              const isColorPicking = colorPickerLabel === spk.speaker_label;
              const isMerging = mergeSourceLabel === spk.speaker_label;
              const isSpeakingNow =
                isPlaying && currentActiveTurn?.speakerLabel === spk.speaker_label;

              return (
                <div
                  key={spk.id}
                  className={`p-3 rounded-xl border transition-all duration-200 relative group/card shadow-2xs ${
                    isSpeakingNow
                      ? "border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/30 shadow-xs"
                      : isFiltered
                      ? "bg-blue-50/70 border-blue-300 shadow-xs ring-1 ring-blue-200"
                      : "bg-white border-slate-200/90 hover:border-slate-300"
                  }`}
                >
                  {/* Header: Name, Speaking Indicator, & Time Share */}
                  <div className="flex justify-between items-center mb-2 gap-2">
                    {isEditing ? (
                      <div className="flex items-center gap-1.5 flex-1 min-w-0">
                        <input
                          type="text"
                          value={inlineRenameVal}
                          onChange={(e) => onChangeInlineRenameVal(e.target.value)}
                          onBlur={() =>
                            onSaveInlineRename(spk.speaker_label, inlineRenameVal)
                          }
                          onKeyDown={(e) => {
                            if (e.key === "Enter")
                              onSaveInlineRename(spk.speaker_label, inlineRenameVal);
                            if (e.key === "Escape") onCancelInlineRename();
                          }}
                          autoFocus
                          className="flex-1 bg-white border border-blue-500 rounded-lg px-2.5 py-1 text-xs text-slate-900 font-semibold focus:outline-none ring-1 ring-blue-500"
                        />
                        <button
                          onClick={() =>
                            onSaveInlineRename(spk.speaker_label, inlineRenameVal)
                          }
                          className="p-1 text-emerald-600 hover:bg-emerald-50 rounded-lg transition-colors cursor-pointer"
                          title="Save Name"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={onCancelInlineRename}
                          className="p-1 text-slate-400 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
                          title="Cancel"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {/* Interactive Color Swatch */}
                        <button
                          onClick={() =>
                            onToggleColorPicker(
                              isColorPicking ? null : spk.speaker_label
                            )
                          }
                          className="w-3.5 h-3.5 rounded-full shrink-0 ring-2 ring-white shadow-2xs hover:scale-125 transition-transform cursor-pointer"
                          style={{ backgroundColor: spk.color_hex }}
                          title="Click to change speaker color"
                        />

                        {/* Speaker Name with Inline Rename Trigger */}
                        <div
                          onClick={() =>
                            onStartInlineRename(spk.speaker_label, spk.display_name)
                          }
                          className="font-bold text-xs text-slate-900 truncate cursor-pointer hover:text-blue-600 flex items-center gap-1.5 group/rename"
                          title="Click to rename speaker"
                        >
                          <span className="truncate">{spk.display_name}</span>
                          <Edit2 className="w-2.5 h-2.5 text-slate-400 opacity-40 group-hover/rename:opacity-100 transition-opacity" />
                        </div>

                        {/* Live Speaking Indicator Badge */}
                        {isSpeakingNow && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80 shadow-2xs">
                            <span className="flex items-end gap-[1px] h-2">
                              <span className="w-0.5 bg-emerald-500 rounded-full animate-pulse h-1" />
                              <span className="w-0.5 bg-emerald-500 rounded-full animate-pulse h-2.5 delay-75" />
                              <span className="w-0.5 bg-emerald-500 rounded-full animate-pulse h-1.5 delay-150" />
                            </span>
                            <span>Speaking</span>
                          </span>
                        )}
                      </div>
                    )}

                    {/* Talk Time & Share Percentage */}
                    <div className="flex items-center gap-1 shrink-0 font-mono text-[11px]">
                      <span className="font-bold text-slate-800">
                        {spk.talkTime}s
                      </span>
                      <span className="text-[10px] text-slate-500 bg-slate-100 px-1.5 py-0.2 rounded border border-slate-200/60 font-semibold">
                        {spk.percentage}%
                      </span>
                    </div>
                  </div>

                  {/* Color Picker Popover */}
                  {isColorPicking && (
                    <div className="flex items-center justify-between p-2 mb-2 bg-slate-50 rounded-lg border border-slate-200 animate-in fade-in-50 zoom-in-95 duration-100">
                      <span className="text-[10px] text-slate-500 font-semibold">
                        Palette:
                      </span>
                      <div className="flex items-center gap-1.5">
                        {COLOR_PALETTE.map((c) => (
                          <button
                            key={c}
                            onClick={() =>
                              onChangeSpeakerColor(spk.speaker_label, c)
                            }
                            style={{ backgroundColor: c }}
                            className={`w-4 h-4 rounded-full transition-transform hover:scale-125 shadow-2xs cursor-pointer ${
                              spk.color_hex === c
                                ? "ring-2 ring-slate-900 ring-offset-1 scale-110"
                                : ""
                            }`}
                            title={c}
                          />
                        ))}
                      </div>
                      <button
                        onClick={() => onToggleColorPicker(null)}
                        className="text-slate-400 hover:text-slate-600 p-0.5 rounded hover:bg-slate-200 cursor-pointer"
                        title="Close palette"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  )}

                  {/* Speaking Percentage Progress Bar */}
                  <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden mb-2.5">
                    <div
                      className="h-full rounded-full transition-all duration-500 ease-out"
                      style={{
                        width: `${spk.percentage}%`,
                        backgroundColor: spk.color_hex,
                      }}
                    />
                  </div>

                  {/* 3-Column Metrics Grid */}
                  <div className="grid grid-cols-3 gap-1.5 text-[10px] font-mono text-slate-600 mb-2.5">
                    <div className="bg-slate-50 border border-slate-200/60 rounded px-1.5 py-1 text-center">
                      <span className="text-slate-400 text-[9px] uppercase font-bold block">
                        Turns
                      </span>
                      <span className="font-bold text-slate-800">
                        {spk.turnsCount}
                      </span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200/60 rounded px-1.5 py-1 text-center">
                      <span className="text-slate-400 text-[9px] uppercase font-bold block">
                        Words
                      </span>
                      <span className="font-bold text-slate-800">
                        {spk.wordCount}
                      </span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200/60 rounded px-1.5 py-1 text-center">
                      <span className="text-slate-400 text-[9px] uppercase font-bold block">
                        Pace
                      </span>
                      <span className="font-bold text-slate-800">
                        {spk.avgWpm} WPM
                      </span>
                    </div>
                  </div>

                  {/* Quick Actions: Filter Transcript & Merge */}
                  <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px]">
                    <button
                      onClick={() =>
                        onToggleSpeakerFilter(
                          isFiltered ? null : spk.speaker_label
                        )
                      }
                      className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold transition-all cursor-pointer ${
                        isFiltered
                          ? "bg-blue-600 text-white shadow-2xs"
                          : "bg-slate-50 text-slate-700 hover:text-slate-900 hover:bg-slate-100 border border-slate-200"
                      }`}
                    >
                      {isFiltered ? (
                        <span className="inline-flex items-center gap-1">
                          Filtered <X className="w-2.5 h-2.5" />
                        </span>
                      ) : (
                        "Filter Transcript"
                      )}
                    </button>

                    {isMerging ? (
                      <div className="flex items-center gap-1 animate-in fade-in-50 duration-100">
                        <select
                          value={mergeTargetLabel}
                          onChange={(e) => onChangeMergeTarget(e.target.value)}
                          className="text-[10px] bg-white border border-slate-300 rounded-lg px-2 py-0.5 text-slate-700 focus:outline-none focus:border-blue-500"
                        >
                          <option value="">Merge into...</option>
                          {speakerStats
                            .filter(
                              (other) =>
                                other.speaker_label !== spk.speaker_label
                            )
                            .map((other) => (
                              <option
                                key={other.speaker_label}
                                value={other.speaker_label}
                              >
                                {other.display_name}
                              </option>
                            ))}
                        </select>
                        <button
                          onClick={() =>
                            onConfirmMerge(spk.speaker_label, mergeTargetLabel)
                          }
                          disabled={!mergeTargetLabel}
                          className="px-2 py-0.5 bg-blue-600 text-white rounded-lg text-[10px] font-semibold disabled:opacity-40 hover:bg-blue-700 transition-colors cursor-pointer"
                        >
                          Confirm
                        </button>
                        <button
                          onClick={onCancelMerge}
                          className="text-[10px] text-slate-400 hover:text-slate-600 px-1 py-0.5 rounded cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => onStartMerge(spk.speaker_label)}
                        className="text-[10px] font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1 px-2 py-1 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer"
                        title="Merge dialogue turns into another speaker"
                      >
                        <ArrowRightLeft className="w-3 h-3 text-slate-400" />
                        <span>Merge</span>
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 4. DOCK PINNED FOOTER: SUFFICIENT HEIGHT AND STATUS TELEMETRY */}
        <div className="h-11 px-4 py-2 border-t border-slate-200/80 bg-slate-50/95 flex items-center justify-between text-xs text-slate-500 shrink-0 font-mono z-10 shadow-2xs">
          <span className="flex items-center gap-1.5 leading-none">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-slate-700 font-medium">{saveStatus}</span>
          </span>
          <span className="text-[10px] text-slate-400 leading-none font-semibold">
            TMUX Studio v2.0
          </span>
        </div>
      </aside>
    </>
  );
}
