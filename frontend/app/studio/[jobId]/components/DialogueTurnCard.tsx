"use client";

import React, { useState } from "react";
import {
  Clock,
  Repeat,
  Copy,
  Check,
  Edit2,
  ChevronDown,
  Save,
  Play,
  Bookmark,
  Volume2,
  Layers,
} from "lucide-react";
import { DialogueTurn, Speaker, Word, VideoTopic } from "../types";
import {
  formatTime,
  formatTimePrecise,
  formatAccurateTimestamp,
  formatTimeMinutesOnly,
} from "../utils";
import { AccurateHoverHud } from "./AccurateHoverHud";

interface DialogueTurnCardProps {
  turn: DialogueTurn;
  isActive: boolean;
  isPlaying: boolean;
  isLooping: boolean;
  isEditing: boolean;
  editingText: string;
  fontClass: string;
  showConfidence: boolean;
  currentTime: number;
  copiedTurnIndex: number | null;
  speakers: Speaker[];
  activeTurnRef: React.RefObject<HTMLDivElement | null>;
  onSeekTo: (time: number) => void;
  onLoopTurn: (turn: DialogueTurn) => void;
  onCopyTurn: (turn: DialogueTurn) => void;
  onStartEdit: (turn: DialogueTurn) => void;
  onCancelEdit: () => void;
  onChangeEditText: (text: string) => void;
  onSaveEditText: (turn: DialogueTurn) => void;
  onReassignSpeaker: (segmentIds: string[], newSpeakerLabel: string) => void;
  onReassignAddressee?: (segmentIds: string[], newAddressee: string) => void;
  onAddMarker?: (time?: number, label?: string, tag?: "note" | "review" | "highlight") => void;
  topics?: VideoTopic[];
}

export const DialogueTurnCard = React.memo(function DialogueTurnCard({
  turn,
  isActive,
  isPlaying,
  isLooping,
  isEditing,
  editingText,
  fontClass,
  showConfidence,
  currentTime,
  copiedTurnIndex,
  speakers,
  activeTurnRef,
  onSeekTo,
  onLoopTurn,
  onCopyTurn,
  onStartEdit,
  onCancelEdit,
  onChangeEditText,
  onSaveEditText,
  onReassignSpeaker,
  onReassignAddressee,
  onAddMarker,
  topics = [],
}: DialogueTurnCardProps) {
  const [isSpeakerMenuOpen, setIsSpeakerMenuOpen] = useState(false);
  const [isAddresseeMenuOpen, setIsAddresseeMenuOpen] = useState(false);
  const [showSpeechBreakdown, setShowSpeechBreakdown] = useState(false);
  const [activeSegmentMenuId, setActiveSegmentMenuId] = useState<string | null>(null);

  // Microsecond-accurate HUD hover states
  const [hoveredWord, setHoveredWord] = useState<{
    word: Word;
    rect: DOMRect;
  } | null>(null);

  const [hoveredSpeech, setHoveredSpeech] = useState<{
    label: string;
    start: number;
    end: number;
    rect: DOMRect;
  } | null>(null);

  const isTurnPlaying = isActive && isPlaying;
  const hasSpeechesBreakdown = Boolean(turn.segments && turn.segments.length > 1);
  const isAnyMenuOpen = isSpeakerMenuOpen || isAddresseeMenuOpen || Boolean(activeSegmentMenuId);

  return (
    <div
      id={`turn-${turn.turnIndex}`}
      ref={isActive ? activeTurnRef : null}
      className={`rounded-lg border transition-all duration-200 relative group/card overflow-visible ${
        isAnyMenuOpen ? "z-30 shadow-md" : "z-0"
      } ${
        isActive
          ? "border-blue-400 bg-blue-50/25 shadow-xs ring-1 ring-blue-500/15"
          : "border-slate-200/80 hover:border-slate-300 bg-white hover:bg-slate-50/30 hover:shadow-2xs"
      }`}
    >
      <div className="p-3.5 sm:p-4 space-y-2.5">
        {/* Minimal Dialogue Header Row */}
        <div className="flex items-center justify-between gap-2 select-none">
          {/* Left Cluster: Index, Speaker Pill, Timestamp, Speeches Link */}
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            {/* Subtle Turn Index */}
            <span className="font-mono text-[10px] text-slate-400 font-semibold tracking-tight">
              #{turn.turnIndex}
            </span>

            {/* Compact Character Selector Pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsSpeakerMenuOpen(!isSpeakerMenuOpen)}
                className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold text-white shadow-2xs hover:brightness-105 active:scale-95 transition-all cursor-pointer"
                style={{ backgroundColor: turn.colorHex }}
                title="Click to reassign dialogue speaker"
              >
                <span className="truncate max-w-[120px]">{turn.displayName}</span>
                <ChevronDown className="w-2.5 h-2.5 opacity-80" />
              </button>

              {isSpeakerMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsSpeakerMenuOpen(false)}
                  />
                  <div className="absolute left-0 mt-1.5 w-52 max-h-64 overflow-y-auto bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1 z-50 animate-in fade-in-50 zoom-in-95 duration-100 ring-1 ring-slate-900/10">
                    <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Reassign Speaker
                    </div>
                    {speakers.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => {
                          onReassignSpeaker(turn.segmentIds, s.speaker_label);
                          setIsSpeakerMenuOpen(false);
                        }}
                        className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2.5 text-slate-700 transition-colors cursor-pointer"
                      >
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0 shadow-2xs"
                          style={{ backgroundColor: s.color_hex }}
                        />
                        <span className="truncate font-medium">{s.display_name}</span>
                        {s.speaker_label === turn.speakerLabel && (
                          <Check className="w-3 h-3 text-blue-600 ml-auto" />
                        )}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Directional Addressee Selector Pill: Speaker -> Addressee */}
            <div className="relative">
              {turn.addressedTo ? (
                <button
                  type="button"
                  onClick={() => setIsAddresseeMenuOpen(!isAddresseeMenuOpen)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80 shadow-2xs hover:bg-emerald-100/70 transition-colors cursor-pointer"
                  title={`Click to reassign addressee (currently ${turn.addressedTo})`}
                >
                  <span className="text-emerald-500 font-semibold text-[10px]">→</span>
                  <span className="font-semibold truncate max-w-[110px]">{turn.addressedTo}</span>
                  {turn.intent && turn.intent !== "statement" && (
                    <span className="text-[9px] uppercase tracking-wider text-emerald-600/70 ml-0.5 font-bold">
                      ({turn.intent})
                    </span>
                  )}
                  <ChevronDown className="w-2.5 h-2.5 opacity-60 ml-0.5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setIsAddresseeMenuOpen(!isAddresseeMenuOpen)}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border border-dashed border-slate-300 text-slate-400 hover:text-slate-600 hover:border-slate-400 transition-colors cursor-pointer"
                  title="Assign recipient or addressee"
                >
                  <span>→ Addressee</span>
                  <ChevronDown className="w-2.5 h-2.5 opacity-60 ml-0.5" />
                </button>
              )}

              {isAddresseeMenuOpen && onReassignAddressee && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsAddresseeMenuOpen(false)}
                  />
                  <div className="absolute left-0 mt-1.5 w-52 max-h-64 overflow-y-auto bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1 z-50 animate-in fade-in-50 zoom-in-95 duration-100 ring-1 ring-slate-900/10">
                    <div className="px-3 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                      Addressed To
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        onReassignAddressee(turn.segmentIds, "Audience");
                        setIsAddresseeMenuOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2 text-slate-700 transition-colors cursor-pointer"
                    >
                      <span className="w-2 h-2 rounded-full bg-cyan-600 shrink-0" />
                      <span className="font-medium">Audience</span>
                      {turn.addressedTo === "Audience" && (
                        <Check className="w-3 h-3 text-blue-600 ml-auto" />
                      )}
                    </button>
                    {speakers.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => {
                          onReassignAddressee(turn.segmentIds, s.display_name);
                          setIsAddresseeMenuOpen(false);
                        }}
                        className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 flex items-center gap-2 text-slate-700 transition-colors cursor-pointer"
                      >
                        <span
                          className="w-2.5 h-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: s.color_hex }}
                        />
                        <span className="truncate font-medium">{s.display_name}</span>
                        {turn.addressedTo === s.display_name && (
                          <Check className="w-3 h-3 text-blue-600 ml-auto" />
                        )}
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Click-to-seek Accurate Speech Timestamp Range */}
            <button
              type="button"
              onClick={() => onSeekTo(turn.startTime)}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setHoveredSpeech({
                  label: `Turn #${turn.turnIndex} • ${turn.displayName}`,
                  start: turn.startTime,
                  end: turn.endTime,
                  rect,
                });
              }}
              onMouseLeave={() => setHoveredSpeech(null)}
              className="font-mono text-[11px] text-slate-500 hover:text-blue-600 transition-colors cursor-pointer flex items-center gap-1 bg-slate-50 hover:bg-blue-50 px-2 py-0.5 rounded-md border border-slate-200/70"
              aria-label={`Speech Turn #${turn.turnIndex}: [${formatAccurateTimestamp(turn.startTime, turn.endTime, 3)}] • Click to seek`}
            >
              <Clock className="w-3 h-3 text-slate-400 group-hover/card:text-blue-500" />
              <span>[{formatTimeMinutesOnly(turn.startTime)} &ndash; {formatTimeMinutesOnly(turn.endTime)}]</span>
            </button>

            {/* Speeches Breakdown Expandable Chip (if multi-segment) */}
            {hasSpeechesBreakdown && (
              <button
                type="button"
                onClick={() => setShowSpeechBreakdown(!showSpeechBreakdown)}
                className={`px-1.5 py-0.5 rounded-lg text-[10px] font-medium transition-all cursor-pointer flex items-center gap-1 ${
                  showSpeechBreakdown
                    ? "bg-blue-100/70 text-blue-700 font-semibold"
                    : "text-slate-500 hover:text-blue-600 hover:bg-slate-100"
                }`}
                title={showSpeechBreakdown ? "Hide speech breakdown" : "Expand speeches breakdown"}
              >
                <Layers className="w-2.5 h-2.5" />
                <span>{turn.segments?.length} speeches</span>
              </button>
            )}

            {/* Active Audio Wave Indicator */}
            {isTurnPlaying && (
              <span className="inline-flex items-end gap-0.5 h-3 px-1 pb-0.5" title="Playing">
                <span className="w-0.5 bg-blue-600 rounded-full animate-wave-1" />
                <span className="w-0.5 bg-cyan-600 rounded-full animate-wave-2" />
                <span className="w-0.5 bg-blue-500 rounded-full animate-wave-3" />
              </span>
            )}
          </div>

          {/* Right Cluster: Telemetry & Progressive-Disclosure Action Toolbar */}
          <div className="flex items-center gap-1.5 ml-auto">
            {/* Minimal Duration & Word Count */}
            <span className="hidden sm:inline font-mono text-[11px] text-slate-400 select-none mr-0.5">
              {turn.duration.toFixed(1)}s &bull; {turn.wordCount}w
            </span>

            {/* Actions: Primary Play is always ready; utilities reveal smoothly on hover */}
            <div className="flex items-center gap-0.5">
              <div
                className={`flex items-center gap-0.5 transition-opacity duration-150 ${
                  isEditing || isLooping || copiedTurnIndex === turn.turnIndex
                    ? "opacity-100"
                    : "opacity-100 sm:opacity-0 sm:group-hover/card:opacity-100 focus-within:opacity-100"
                }`}
              >
                {/* Loop Turn */}
                <button
                  type="button"
                  onClick={() => onLoopTurn(turn)}
                  className={`p-1 rounded-lg transition-all active:scale-95 cursor-pointer ${
                    isLooping
                      ? "text-amber-700 bg-amber-100 border border-amber-300 animate-pulse"
                      : "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                  }`}
                  title={isLooping ? "Disable loop" : "Loop this turn"}
                >
                  <Repeat className="w-3.5 h-3.5" />
                </button>

                {/* Bookmark Marker */}
                {onAddMarker && (
                  <button
                    type="button"
                    onClick={() =>
                      onAddMarker(
                        turn.startTime,
                        `Turn #${turn.turnIndex} - ${turn.displayName}`,
                        "review"
                      )
                    }
                    className="p-1 text-slate-400 hover:text-amber-600 hover:bg-slate-100 rounded-lg transition-all active:scale-95 cursor-pointer"
                    title="Bookmark marker"
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                  </button>
                )}

                {/* Copy Text */}
                <button
                  type="button"
                  onClick={() => onCopyTurn(turn)}
                  className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all active:scale-95 cursor-pointer"
                  title="Copy dialogue"
                >
                  {copiedTurnIndex === turn.turnIndex ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>

                {/* Edit Text */}
                <button
                  type="button"
                  onClick={() => {
                    if (isEditing) {
                      onCancelEdit();
                    } else {
                      onStartEdit(turn);
                    }
                  }}
                  className={`p-1 rounded-lg transition-all active:scale-95 cursor-pointer ${
                    isEditing
                      ? "text-blue-700 bg-blue-100 font-bold"
                      : "text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                  }`}
                  title="Edit dialogue"
                >
                  <Edit2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Primary Play Button */}
              <button
                type="button"
                onClick={() => onSeekTo(turn.startTime)}
                className={`p-1.5 rounded-lg transition-all active:scale-95 cursor-pointer ${
                  isTurnPlaying
                    ? "bg-blue-600 text-white shadow-2xs"
                    : "text-slate-500 hover:text-blue-600 hover:bg-blue-50/70"
                }`}
                title={isTurnPlaying ? "Playing turn" : "Play turn"}
              >
                {isTurnPlaying ? (
                  <Volume2 className="w-3.5 h-3.5 fill-current animate-pulse" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current ml-0.2" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Dialogue Body: Editable Textarea vs Word Chips */}
        {isEditing ? (
          <div className="space-y-2 pt-1 animate-in fade-in-50 duration-150">
            <textarea
              value={editingText}
              onChange={(e) => onChangeEditText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSaveEditText(turn);
                }
                if (e.key === "Escape") {
                  onCancelEdit();
                }
              }}
              rows={3}
              className="w-full bg-slate-50/60 border border-blue-500 rounded-lg p-2.5 text-sm text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 font-sans shadow-inner transition-colors"
              autoFocus
            />
            <div className="flex flex-wrap justify-between items-center text-xs gap-2">
              <span className="text-[10px] text-slate-400 font-mono">
                Press <kbd className="px-1 py-0.2 bg-slate-100 border border-slate-200 rounded-lg">Enter</kbd> to save &bull;{" "}
                <kbd className="px-1 py-0.2 bg-slate-100 border border-slate-200 rounded-lg">Esc</kbd> to cancel
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={onCancelEdit}
                  className="px-2.5 py-1 text-xs border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => onSaveEditText(turn)}
                  className="px-3 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium flex items-center gap-1 shadow-2xs transition-all active:scale-95 cursor-pointer"
                >
                  <Save className="w-3 h-3" />
                  <span>Save</span>
                </button>
              </div>
            </div>
          </div>
        ) : showSpeechBreakdown && turn.segments && turn.segments.length > 1 ? (
          /* Granular Speeches Breakdown */
          <div className="space-y-1.5 pt-1 animate-in fade-in-50 duration-150">
            {turn.segments.map((seg, sIdx) => {
              const isSegActive = currentTime >= seg.start_time && currentTime <= seg.end_time;
              const segSpk = speakers.find((s) => s.speaker_label === seg.speaker_label) || {
                speaker_label: seg.speaker_label || turn.speakerLabel,
                display_name: turn.displayName,
                color_hex: turn.colorHex,
              };
              return (
                <div
                  key={seg.id || sIdx}
                  className={`p-2.5 rounded-lg transition-all border ${
                    isSegActive
                      ? "bg-blue-50/40 border-blue-300/80 shadow-2xs"
                      : "bg-slate-50/50 hover:bg-slate-50 border-slate-200/50"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] mb-1">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => onSeekTo(seg.start_time)}
                        onMouseEnter={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          setHoveredSpeech({
                            label: `Speech #${sIdx + 1} • ${segSpk.display_name}`,
                            start: seg.start_time,
                            end: seg.end_time,
                            rect,
                          });
                        }}
                        onMouseLeave={() => setHoveredSpeech(null)}
                        className="font-mono text-[10px] text-slate-400 hover:text-blue-600 cursor-pointer"
                        aria-label={`Speech #${sIdx + 1}: [${formatAccurateTimestamp(seg.start_time, seg.end_time, 3)}] • Click to seek`}
                      >
                        [{formatTime(seg.start_time, 2)} &ndash; {formatTime(seg.end_time, 2)}]
                      </button>

                      {/* Inline Segment Speaker Selector */}
                      <div className="relative">
                        <button
                          type="button"
                          onClick={() =>
                            setActiveSegmentMenuId(
                              activeSegmentMenuId === seg.id ? null : seg.id
                            )
                          }
                          className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded-full text-[10px] font-medium text-white shadow-2xs cursor-pointer"
                          style={{ backgroundColor: segSpk.color_hex }}
                        >
                          <span>{segSpk.display_name}</span>
                          <ChevronDown className="w-2 h-2" />
                        </button>

                        {seg.addressed_to && (
                          <span
                            className="inline-flex items-center gap-0.5 px-1.5 py-0.2 rounded-full text-[9px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/60"
                            title={`Addressed to ${seg.addressed_to}`}
                          >
                            <span className="text-emerald-500 font-bold">→</span>
                            <span>{seg.addressed_to}</span>
                          </span>
                        )}

                        {activeSegmentMenuId === seg.id && (
                          <>
                            <div
                              className="fixed inset-0 z-40"
                              onClick={() => setActiveSegmentMenuId(null)}
                            />
                            <div className="absolute left-0 mt-1 w-52 max-h-64 overflow-y-auto bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1 z-50 ring-1 ring-slate-900/10">
                              {speakers.map((s) => (
                                <button
                                  key={s.id}
                                  type="button"
                                  onClick={() => {
                                    onReassignSpeaker([seg.id], s.speaker_label);
                                    setActiveSegmentMenuId(null);
                                  }}
                                  className="w-full text-left px-2.5 py-1 text-xs hover:bg-slate-50 flex items-center gap-2 text-slate-700 cursor-pointer"
                                >
                                  <span
                                    className="w-2 h-2 rounded-full shrink-0"
                                    style={{ backgroundColor: s.color_hex }}
                                  />
                                  <span>{s.display_name}</span>
                                </button>
                              ))}
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => onSeekTo(seg.start_time)}
                      className="p-1 text-slate-400 hover:text-blue-600 rounded-lg cursor-pointer"
                      title="Play speech"
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                    </button>
                  </div>

                  <p className={`${fontClass} text-slate-800 text-xs sm:text-[13px] leading-relaxed`}>
                    {seg.words && seg.words.length > 0 ? (
                      seg.words.map((w, wIdx) => {
                        const isWordActive = currentTime >= w.start_time && currentTime <= w.end_time;
                        const isHovered = hoveredWord?.word === w;
                        return (
                          <span
                            key={wIdx}
                            onClick={() => onSeekTo(w.start_time)}
                            onMouseEnter={(e) => {
                              const rect = e.currentTarget.getBoundingClientRect();
                              setHoveredWord({ word: w, rect });
                            }}
                            onMouseLeave={() => setHoveredWord(null)}
                            className={`cursor-pointer transition-colors px-0.5 rounded-[2px] ${
                              isWordActive
                                ? "bg-blue-600 text-white font-medium"
                                : isHovered
                                ? "bg-blue-100 text-blue-800 font-medium"
                                : "hover:bg-blue-50 hover:text-blue-700"
                            }`}
                            aria-label={`Word: "${(w.word || "").trim()}" • [${formatAccurateTimestamp(w.start_time, w.end_time, 3)}] • Click to seek`}
                          >
                            {w.word}{" "}
                          </span>
                        );
                      })
                    ) : (
                      seg.text
                    )}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          /* Main Dialogue Text with Microsecond-Accurate Hover & Reading Highlighting */
          <div className={`${fontClass} text-slate-800 text-[14px] sm:text-[15px] leading-relaxed selection:bg-blue-100`}>
            {turn.words && turn.words.length > 0 ? (
              turn.words.map((w, wIdx) => {
                const isWordActive = currentTime >= w.start_time && currentTime <= w.end_time;
                const isLowConfidence = showConfidence && (w.confidence_score ?? 1.0) < 0.65;
                const isHovered = hoveredWord?.word === w;

                return (
                  <span
                    key={wIdx}
                    onClick={() => onSeekTo(w.start_time)}
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setHoveredWord({ word: w, rect });
                    }}
                    onMouseLeave={() => setHoveredWord(null)}
                    className={`cursor-pointer transition-colors px-0.5 py-0.2 rounded-[2px] inline-block select-text ${
                      isWordActive
                        ? "bg-blue-600 text-white font-medium shadow-2xs"
                        : isHovered
                        ? "bg-blue-100 text-blue-800 font-medium"
                        : isLowConfidence
                        ? "border-b-2 border-amber-400 bg-amber-50/70 text-amber-950"
                        : "hover:bg-blue-50 hover:text-blue-700"
                    }`}
                    aria-label={`Word: "${(w.word || "").trim()}" • [${formatAccurateTimestamp(w.start_time, w.end_time, 3)}] • Click to seek`}
                  >
                    {w.word}{" "}
                  </span>
                );
              })
            ) : (
              <p
                onClick={() => onSeekTo(turn.startTime)}
                className="cursor-pointer hover:text-blue-700 transition-colors"
              >
                {turn.text}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Fixed High-Precision Word & Speech Hover HUD Overlays ───────── */}
      {hoveredWord && !isAnyMenuOpen && (
        <AccurateHoverHud
          type="word"
          rect={hoveredWord.rect}
          word={hoveredWord.word}
          topics={topics}
        />
      )}

      {hoveredSpeech && !isAnyMenuOpen && (
        <AccurateHoverHud
          type="speech"
          rect={hoveredSpeech.rect}
          speech={hoveredSpeech}
          topics={topics}
        />
      )}
    </div>
  );
});
