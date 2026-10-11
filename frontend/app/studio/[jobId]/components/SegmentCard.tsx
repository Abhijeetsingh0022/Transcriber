"use client";

import React, { useState } from "react";
import { Play, Pause, ChevronDown, Clock, UserCheck } from "lucide-react";
import { Segment, Speaker, Word, VideoTopic } from "../types";
import { formatTime, formatTimePrecise, formatAccurateTimestamp } from "../utils";
import { AccurateHoverHud } from "./AccurateHoverHud";

interface SegmentCardProps {
  segment: Segment;
  isActive: boolean;
  speakerName: string;
  fontClass: string;
  currentTime: number;
  isPlaying?: boolean;
  speakers?: Speaker[];
  onSeekTo: (time: number) => void;
  onReassignSpeaker?: (segmentIds: string[], newSpeakerLabel: string) => void;
  topics?: VideoTopic[];
}

export const SegmentCard = React.memo(function SegmentCard({
  segment,
  isActive,
  speakerName,
  fontClass,
  currentTime,
  isPlaying = false,
  speakers = [],
  onSeekTo,
  onReassignSpeaker,
  topics = [],
}: SegmentCardProps) {
  const [isSpeakerMenuOpen, setIsSpeakerMenuOpen] = useState(false);

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

  const duration = Number((segment.end_time - segment.start_time).toFixed(2));
  const wordsList = segment.text.trim().split(/\s+/).filter(Boolean);
  const wordCount = wordsList.length;
  const durMin = Math.max(duration / 60.0, 0.01);
  const wpm = Math.round(wordCount / durMin);

  const currentSpeaker = speakers.find(
    (s) => s.speaker_label === (segment.speaker_label || "SPEAKER_00")
  );
  const speakerColor = currentSpeaker?.color_hex || "#2563eb";
  const isSegmentPlaying = isActive && isPlaying;

  return (
    <div
      className={`rounded-lg border transition-all duration-200 relative group/seg overflow-visible ${
        isSpeakerMenuOpen ? "z-30 shadow-md" : "z-0"
      } ${
        isActive
          ? "border-blue-400 bg-blue-50/25 shadow-xs ring-1 ring-blue-500/15"
          : "border-slate-200/80 hover:border-slate-300 bg-white hover:bg-slate-50/30 hover:shadow-2xs"
      }`}
    >
      <div className="p-3.5 sm:p-4 space-y-2">
        {/* Header Bar: Speaker Pill, Timestamp, Metrics, Play */}
        <div className="flex items-center justify-between text-xs mb-2.5 gap-2 select-none">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Inline Speaker Reassignment Pill */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setIsSpeakerMenuOpen(!isSpeakerMenuOpen)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold text-white transition-all shadow-2xs hover:brightness-110 active:scale-95 cursor-pointer"
                style={{ backgroundColor: speakerColor }}
                title="Click to reassign character for this speech segment"
              >
                <span>{speakerName}</span>
                <ChevronDown className="w-3 h-3 text-white/80" />
              </button>

              {/* Speaker Selection Dropdown */}
              {isSpeakerMenuOpen && (
                <>
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsSpeakerMenuOpen(false)}
                  />
                  <div className="absolute left-0 mt-1.5 w-52 max-h-64 overflow-y-auto bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1 z-50 animate-in fade-in-50 zoom-in-95 duration-100 ring-1 ring-slate-900/10">
                    <div className="px-3 py-1.5 border-b border-slate-100 text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                      <span>Reassign Speech #{((segment.segment_index || 0) + 1)}</span>
                      <UserCheck className="w-3 h-3 text-blue-600" />
                    </div>
                    {speakers.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => {
                          setIsSpeakerMenuOpen(false);
                          if (onReassignSpeaker) {
                            onReassignSpeaker([segment.id], s.speaker_label);
                          }
                        }}
                        className={`w-full flex items-center justify-between px-3 py-1.5 text-xs text-left transition-colors cursor-pointer ${
                          s.speaker_label === segment.speaker_label
                            ? "bg-blue-50 font-semibold text-blue-700"
                            : "hover:bg-slate-50 text-slate-700"
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full shrink-0"
                            style={{ backgroundColor: s.color_hex }}
                          />
                          <span>{s.display_name}</span>
                        </div>
                        <span className="font-mono text-[10px] text-slate-400 uppercase">
                          {s.speaker_label}
                        </span>
                      </button>
                    ))}
                  </div>
                </>
              )}
            </div>

            {/* Directional Addressee Badge: Speaker -> Addressee */}
            {segment.addressed_to && (
              <div
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/80 shadow-2xs"
                title={`Addressed to ${segment.addressed_to}${segment.turn_intent ? ` (${segment.turn_intent})` : ""}`}
              >
                <span className="text-emerald-500 font-semibold text-[10px]">→</span>
                <span className="font-semibold">{segment.addressed_to}</span>
                {segment.turn_intent && segment.turn_intent !== "statement" && (
                  <span className="text-[9px] uppercase tracking-wider text-emerald-600/70 ml-0.5 font-bold">
                    ({segment.turn_intent})
                  </span>
                )}
              </div>
            )}

            {/* Click to Seek Accurate Timestamp Badge */}
            <button
              type="button"
              onClick={() => onSeekTo(segment.start_time)}
              onMouseEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setHoveredSpeech({
                  label: `Speech #${(segment.segment_index || 0) + 1} • ${speakerName}`,
                  start: segment.start_time,
                  end: segment.end_time,
                  rect,
                });
              }}
              onMouseLeave={() => setHoveredSpeech(null)}
              className="flex items-center gap-1 font-mono text-[11px] text-slate-500 hover:text-blue-600 bg-slate-100/80 hover:bg-blue-50 px-2 py-0.5 rounded-lg transition-colors border border-slate-200/60 cursor-pointer"
              aria-label={`Speech: [${formatAccurateTimestamp(segment.start_time, segment.end_time, 3)}] • Click to jump`}
            >
              <Clock className="w-3 h-3 text-slate-400" />
              <span>[{formatTime(segment.start_time, 2)} &ndash; {formatTime(segment.end_time, 2)}]</span>
            </button>

            {/* Duration & Word Pace */}
            <span className="text-[11px] text-slate-400 font-mono hidden sm:inline">
              {duration}s &bull; {wordCount} words
            </span>

            {wpm > 0 && (
              <span
                className={`text-[10px] font-mono px-1.5 py-0.2 rounded-lg border hidden md:inline ${
                  wpm > 185
                    ? "bg-amber-50 text-amber-700 border-amber-200"
                    : wpm < 130
                    ? "bg-slate-100 text-slate-600 border-slate-200"
                    : "bg-blue-50 text-blue-700 border-blue-200"
                }`}
              >
                {wpm} WPM
              </span>
            )}
          </div>

          {/* Right Action: Play Button & Speech Index */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => onSeekTo(segment.start_time)}
              className={`p-1.5 rounded-lg border transition-all active:scale-95 cursor-pointer ${
                isSegmentPlaying
                  ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                  : "bg-white hover:bg-slate-50 text-slate-600 hover:text-blue-600 border-slate-200/90 shadow-2xs"
              }`}
              title={isSegmentPlaying ? "Playing this speech" : "Play this speech"}
            >
              {isSegmentPlaying ? (
                <Pause className="w-3 h-3 fill-current" />
              ) : (
                <Play className="w-3 h-3 fill-current ml-0.5" />
              )}
            </button>
            <span className="text-[11px] font-mono text-slate-400 font-medium">
              #{(segment.segment_index || 0) + 1}
            </span>
          </div>
        </div>

        {/* Speech Text Content with Word-level Interactive Highlighting */}
        <div className={`${fontClass} text-slate-800 leading-relaxed text-sm`}>
          {segment.words && segment.words.length > 0 ? (
            segment.words.map((w, wIdx) => {
              const isWordActive =
                currentTime >= w.start_time && currentTime <= w.end_time;
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
                  className={`cursor-pointer transition-colors px-0.5 rounded-[3px] select-text ${
                    isWordActive
                      ? "bg-blue-600 text-white font-medium shadow-2xs"
                      : isHovered
                      ? "bg-blue-100 text-blue-800 font-medium"
                      : "hover:bg-blue-50 hover:text-blue-700"
                  }`}
                  aria-label={`Word: "${(w.word || "").trim()}" • [${formatAccurateTimestamp(w.start_time, w.end_time, 3)}] • Click to jump`}
                >
                  {w.word}{" "}
                </span>
              );
            })
          ) : (
            <span
              onClick={() => onSeekTo(segment.start_time)}
              className="cursor-pointer select-text hover:text-blue-700 transition-colors"
            >
              {segment.text}
            </span>
          )}
        </div>
      </div>

      {/* ── Fixed High-Precision Word & Speech Hover HUD Overlays ───────── */}
      {hoveredWord && !isSpeakerMenuOpen && (
        <AccurateHoverHud
          type="word"
          rect={hoveredWord.rect}
          word={hoveredWord.word}
          topics={topics}
        />
      )}

      {hoveredSpeech && !isSpeakerMenuOpen && (
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
