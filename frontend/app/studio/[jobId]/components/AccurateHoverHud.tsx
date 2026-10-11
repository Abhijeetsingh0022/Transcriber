"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { Clock, Volume2, Compass } from "lucide-react";
import { formatTimePrecise } from "../utils";
import { VideoTopic } from "../types";

export interface AccurateHoverHudProps {
  type: "word" | "speech";
  rect: DOMRect;
  word?: {
    word: string;
    start_time: number;
    end_time: number;
    confidence_score?: number;
  };
  speech?: {
    label: string;
    start: number;
    end: number;
  };
  topic?: VideoTopic | null;
  topics?: VideoTopic[];
}

export const AccurateHoverHud: React.FC<AccurateHoverHudProps> = ({
  type,
  rect,
  word,
  speech,
  topic,
  topics,
}) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || typeof document === "undefined") {
    return null;
  }

  const viewportWidth = window.innerWidth;
  const wordCenterX = rect.left + rect.width / 2;

  // Resolve matching section from topic flowchart data
  const targetTime = word ? word.start_time : speech ? speech.start : 0;
  const activeTopic =
    topic ||
    (topics && topics.length > 0
      ? topics.find((t) => targetTime >= t.start_time && targetTime <= t.end_time) ||
        topics.find((t, i) => {
          const nextT = topics[i + 1];
          return targetTime >= t.start_time && (!nextT || targetTime < nextT.start_time);
        }) ||
        (targetTime < topics[0].start_time ? topics[0] : null)
      : null);

  // Approximate half-width of HUD for boundary clamping
  const hudHalfWidth = activeTopic ? 135 : type === "word" ? 105 : 115;
  const minCenterX = hudHalfWidth + 12;
  const maxCenterX = viewportWidth - hudHalfWidth - 12;
  const clampedCenterX = Math.max(minCenterX, Math.min(maxCenterX, wordCenterX));

  // Compute horizontal arrow offset relative to the tooltip's center
  const rawOffset = wordCenterX - clampedCenterX;
  const maxCaretOffset = hudHalfWidth - 16;
  const caretOffset = Math.max(-maxCaretOffset, Math.min(maxCaretOffset, rawOffset));

  // Determine whether to show above or below based on top header clearance
  // Header height is 56px. If activeTopic is present, HUD is ~68px tall.
  const isAbove = activeTopic ? rect.top >= 135 : rect.top >= 90;
  // Position tooltip 7px above or below the element so the 5px diamond leaves a tight ~2-3px gap
  const topPosition = isAbove ? rect.top - 7 : rect.bottom + 7;

  const content = (() => {
    if (type === "word" && word) {
      const durationMs = Math.round((word.end_time - word.start_time) * 1000);
      const durationLabel =
        durationMs >= 1000 ? `${(durationMs / 1000).toFixed(2)}s` : `${durationMs}ms`;

      return (
        <div
          className="pointer-events-none fixed z-[9999] px-2.5 py-1.5 rounded-lg bg-slate-900/98 text-white font-mono text-xs shadow-2xl border border-slate-700/90 backdrop-blur-md flex flex-col gap-0.5 select-none animate-in fade-in duration-75"
          style={{
            left: `${clampedCenterX}px`,
            top: `${topPosition}px`,
            transform: isAbove ? "translate(-50%, -100%)" : "translate(-50%, 0)",
          }}
        >
          {/* Precise Caret Diamond pointing directly at the hovered word */}
          <div
            className={`absolute w-2.5 h-2.5 bg-slate-900 border-slate-700/90 rotate-45 -translate-x-1/2 ${
              isAbove
                ? "bottom-[-5px] border-b border-r"
                : "top-[-5px] border-t border-l"
            }`}
            style={{
              left: `calc(50% + ${caretOffset}px)`,
            }}
          />

          {/* Header row: Clock icon, start-end timestamps, duration badge */}
          <div className="flex items-center gap-1.5 whitespace-nowrap">
            <Clock className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span className="font-bold text-slate-100 tracking-tight">
              {formatTimePrecise(word.start_time, 3)}
            </span>
            <span className="text-slate-400">&ndash;</span>
            <span className="font-bold text-slate-100 tracking-tight">
              {formatTimePrecise(word.end_time, 3)}
            </span>
            <span className="text-blue-300 font-semibold text-[10px] bg-blue-950/90 px-1.5 py-0.2 rounded border border-blue-800/70 ml-0.5 font-mono">
              {durationLabel}
            </span>
          </div>

          {/* Subtitle row: Quoted word, confidence score, jump hint */}
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-sans gap-2 whitespace-nowrap">
            <span className="truncate max-w-[130px] italic text-slate-200 font-medium">
              &ldquo;{(word.word || "").trim()}&rdquo;
            </span>
            <div className="flex items-center gap-1.5 shrink-0">
              {word.confidence_score !== undefined && (
                <span className="text-emerald-400 font-mono text-[9px] font-medium">
                  {Math.round(word.confidence_score * 100)}% conf
                </span>
              )}
              <span className="text-slate-400 text-[9px] font-sans">
                &bull; Click to seek
              </span>
            </div>
          </div>

          {/* Topic Flowchart Section Context Row */}
          {activeTopic && (
            <div className="flex items-center gap-1.5 pt-1 mt-0.5 border-t border-slate-800/90 text-[10px] whitespace-nowrap">
              <div className="flex items-center gap-1 shrink-0 text-cyan-400 font-mono text-[9px] font-bold bg-cyan-950/90 px-1.5 py-0.2 rounded border border-cyan-800/70">
                <Compass className="w-2.5 h-2.5 text-cyan-400 shrink-0" />
                <span>Sec {activeTopic.section_no}</span>
              </div>
              <span className="truncate max-w-[210px] text-slate-300 font-sans font-medium text-[10px]">
                {activeTopic.section || activeTopic.topic}
              </span>
            </div>
          )}
        </div>
      );
    }

    if (type === "speech" && speech) {
      const durationSec = (speech.end - speech.start).toFixed(2);

      return (
        <div
          className="pointer-events-none fixed z-[9999] px-2.5 py-1.5 rounded-lg bg-slate-900/98 text-white font-mono text-xs shadow-2xl border border-slate-700/90 backdrop-blur-md flex flex-col gap-0.5 select-none animate-in fade-in duration-75"
          style={{
            left: `${clampedCenterX}px`,
            top: `${topPosition}px`,
            transform: isAbove ? "translate(-50%, -100%)" : "translate(-50%, 0)",
          }}
        >
          {/* Precise Caret Diamond pointing directly at the hovered speech timestamp */}
          <div
            className={`absolute w-2.5 h-2.5 bg-slate-900 border-slate-700/90 rotate-45 -translate-x-1/2 ${
              isAbove
                ? "bottom-[-5px] border-b border-r"
                : "top-[-5px] border-t border-l"
            }`}
            style={{
              left: `calc(50% + ${caretOffset}px)`,
            }}
          />

          {/* Header row: Volume icon, start-end timestamps, duration badge */}
          <div className="flex items-center gap-1.5 whitespace-nowrap">
            <Volume2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="font-bold text-slate-100 tracking-tight">
              {formatTimePrecise(speech.start, 3)}
            </span>
            <span className="text-slate-400">&ndash;</span>
            <span className="font-bold text-slate-100 tracking-tight">
              {formatTimePrecise(speech.end, 3)}
            </span>
            <span className="text-emerald-300 font-semibold text-[10px] bg-emerald-950/90 px-1.5 py-0.2 rounded border border-emerald-800/70 ml-0.5 font-mono">
              {durationSec}s
            </span>
          </div>

          {/* Subtitle row: Speech label, jump hint */}
          <div className="flex items-center justify-between text-[10px] text-slate-400 font-sans gap-2 whitespace-nowrap">
            <span className="truncate max-w-[150px] text-slate-200 font-medium">
              {speech.label}
            </span>
            <span className="text-slate-400 text-[9px]">
              &bull; Click to seek
            </span>
          </div>

          {/* Topic Flowchart Section Context Row */}
          {activeTopic && (
            <div className="flex items-center gap-1.5 pt-1 mt-0.5 border-t border-slate-800/90 text-[10px] whitespace-nowrap">
              <div className="flex items-center gap-1 shrink-0 text-cyan-400 font-mono text-[9px] font-bold bg-cyan-950/90 px-1.5 py-0.2 rounded border border-cyan-800/70">
                <Compass className="w-2.5 h-2.5 text-cyan-400 shrink-0" />
                <span>Sec {activeTopic.section_no}</span>
              </div>
              <span className="truncate max-w-[210px] text-slate-300 font-sans font-medium text-[10px]">
                {activeTopic.section || activeTopic.topic}
              </span>
            </div>
          )}
        </div>
      );
    }

    return null;
  })();

  if (!content) return null;

  // Mount directly into document.body to avoid parent containing-block offsets
  return createPortal(content, document.body);
};
