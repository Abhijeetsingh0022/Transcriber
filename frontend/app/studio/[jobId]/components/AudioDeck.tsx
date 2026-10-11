"use client";

import React from "react";
import {
  Volume2,
  VolumeX,
  Clock,
  Bookmark,
  RotateCcw,
  SkipBack,
  SkipForward,
  Play,
  Pause,
  Repeat,
  Eye,
  PanelLeftClose,
} from "lucide-react";
import { ABLoopState, DialogueTurn, WaveformBar } from "../types";
import { API_BASE, formatTime } from "../utils";

interface AudioDeckProps {
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
  onCollapse?: () => void;
}

export function AudioDeck({
  jobId,
  audioRef,
  currentTime,
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
  onCollapse,
}: AudioDeckProps) {
  const BARS_COUNT = 52;
  const progressRatio =
    effectiveDuration > 0
      ? Math.min(1, Math.max(0, currentTime / effectiveDuration))
      : 0;
  const progressPercent = Math.round(progressRatio * 100);

  return (
    <div className="p-3 sm:p-3.5 border-b border-slate-200/80 bg-slate-50/50 space-y-2.5 shrink-0">
      {/* ── Audio Console Header ─────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-blue-50 border border-blue-200/60 text-blue-600 flex items-center justify-center shadow-2xs">
            <Volume2 className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-bold text-slate-800 tracking-wide">
            Audio Player
          </span>
          <span
            className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold transition-all ${
              isPlaying
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-2xs"
                : "bg-slate-100 text-slate-500 border border-slate-200"
            }`}
            suppressHydrationWarning
          >
            {isPlaying ? (
              <span className="flex items-end gap-[1.5px] h-2">
                <span className="w-0.5 bg-emerald-500 rounded-full animate-[pulse_0.6s_ease-in-out_infinite] h-1.5" />
                <span className="w-0.5 bg-emerald-500 rounded-full animate-[pulse_0.8s_ease-in-out_infinite_0.15s] h-2.5" />
                <span className="w-0.5 bg-emerald-500 rounded-full animate-[pulse_0.5s_ease-in-out_infinite_0.3s] h-1" />
              </span>
            ) : (
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            )}
            <span>{isPlaying ? "Live" : "Idle"}</span>
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="text-[10px] font-mono text-slate-500 bg-white px-2 py-0.5 rounded-md border border-slate-200 shadow-2xs">
            16 kHz • VAD Active
          </span>
          {onCollapse && (
            <button
              onClick={onCollapse}
              className="p-1 text-slate-400 hover:text-slate-700 hover:bg-slate-100 rounded-md transition-colors cursor-pointer"
              title="Collapse audio panel"
            >
              <PanelLeftClose className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Hidden HTML5 Audio Element */}
      <audio
        ref={audioRef}
        src={`${API_BASE}/jobs/${jobId}/media`}
        onTimeUpdate={onTimeUpdate}
        onLoadedMetadata={onLoadedMetadata}
        onDurationChange={onDurationChange}
        onEnded={onEnded}
      />

      {/* ── Studio Audio Console HUD Card ────────────────────────────── */}
      <div className="bg-slate-950 text-slate-100 rounded-xl p-3 sm:p-3.5 space-y-2.5 shadow-xl border border-slate-800 ring-1 ring-white/5 relative overflow-hidden transition-all">
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-500/40 to-transparent pointer-events-none" />

        {/* 1. Timecode Readout & Stream Telemetry */}
        <div className="flex items-center justify-between font-mono">
          <div className="flex items-baseline gap-1.5">
            <span
              className="text-white font-bold text-base tracking-tight"
              suppressHydrationWarning
            >
              {formatTime(currentTime)}
            </span>
            <span
              className="text-slate-500 text-[11px]"
              suppressHydrationWarning
            >
              / {formatTime(effectiveDuration)}
            </span>
          </div>

          <div className="flex items-center gap-1.5 text-[10px]">
            {abLoop.active && abLoop.a !== null && abLoop.b !== null && (
              <span className="text-amber-400 font-mono font-semibold bg-amber-950/70 border border-amber-800/80 px-1.5 py-0.5 rounded animate-pulse">
                A-B Loop
              </span>
            )}
            {effectiveDuration > 0 && (
              <span
                className="text-slate-400 font-mono bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded"
                suppressHydrationWarning
              >
                -{formatTime(Math.max(0, effectiveDuration - currentTime))}
              </span>
            )}
            <span
              className="text-blue-400 font-mono font-bold bg-blue-950/70 border border-blue-800/60 px-2 py-0.5 rounded"
              suppressHydrationWarning
            >
              {effectiveDuration > 0 ? `${progressPercent}%` : "0%"}
            </span>
          </div>
        </div>

        {/* 2. Active Speaker HUD Pill */}
        {currentActiveTurn ? (
          <div className="flex items-center justify-between bg-slate-900/90 border border-slate-800/80 rounded-lg px-2.5 py-1.5 text-[11px] font-mono transition-all gap-2">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              {isPlaying ? (
                <span className="flex items-end gap-[1.5px] h-3 shrink-0">
                  <span
                    className="w-1 rounded-full animate-[pulse_0.5s_infinite] h-2"
                    style={{ backgroundColor: currentActiveTurn.colorHex }}
                  />
                  <span
                    className="w-1 rounded-full animate-[pulse_0.7s_infinite_0.1s] h-3.5"
                    style={{ backgroundColor: currentActiveTurn.colorHex }}
                  />
                  <span
                    className="w-1 rounded-full animate-[pulse_0.4s_infinite_0.2s] h-2"
                    style={{ backgroundColor: currentActiveTurn.colorHex }}
                  />
                </span>
              ) : (
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0 shadow-xs ring-1 ring-white/20"
                  style={{ backgroundColor: currentActiveTurn.colorHex }}
                />
              )}
              <span
                className="font-bold text-slate-100 truncate shrink-0 max-w-[130px]"
                title={currentActiveTurn.displayName}
              >
                {currentActiveTurn.displayName}
              </span>
              <span className="text-slate-400 text-[10px] truncate italic hidden sm:inline">
                &ldquo;{currentActiveTurn.text.slice(0, 30)}...&rdquo;
              </span>
            </div>

            <div className="flex items-center gap-1 shrink-0">
              <button
                onClick={() =>
                  onAddMarker(
                    currentTime,
                    `Flag @ ${currentActiveTurn.displayName}`,
                    "review"
                  )
                }
                className="p-1 text-slate-400 hover:text-amber-400 rounded hover:bg-slate-800 transition-colors cursor-pointer"
                title="Bookmark speech turn"
              >
                <Bookmark className="w-3 h-3" />
              </button>
              <button
                onClick={() => onLoopTurn(currentActiveTurn)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                  isLoopingTurn &&
                  loopTurnRange?.start === currentActiveTurn.startTime
                    ? "bg-amber-500/20 text-amber-300 border border-amber-500/50 shadow-[0_0_8px_rgba(245,158,11,0.25)] animate-pulse"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`}
                title="Loop this dialogue turn repeatedly"
              >
                {isLoopingTurn &&
                loopTurnRange?.start === currentActiveTurn.startTime
                  ? "Looping"
                  : "Loop"}
              </button>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between bg-slate-900/40 border border-slate-800/40 rounded-lg px-2.5 py-1.5 text-[11px] font-mono text-slate-500">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-slate-600" />
              <span className="italic text-[10px] text-slate-400">
                Ambient pause
              </span>
            </div>
            <span className="text-[10px] text-slate-500" suppressHydrationWarning>
              {formatTime(currentTime)}
            </span>
          </div>
        )}

        {/* 3. Speech Waveform with Progress Scrubber */}
        <div className="relative group/wave select-none pt-0.5">
          {hoveredWaveTime && (
            <div
              className="absolute -top-7 -translate-x-1/2 bg-slate-900 text-white border border-slate-700 text-[10px] font-mono px-2 py-0.5 rounded-lg shadow-xl pointer-events-none z-30 whitespace-nowrap flex items-center gap-1 animate-in fade-in-50 zoom-in-95 duration-100"
              style={{ left: `${hoveredWaveTime.xPercent}%` }}
            >
              <Clock className="w-2.5 h-2.5 text-blue-400" />
              <span>{formatTime(hoveredWaveTime.time)}</span>
              {hoveredWaveTime.speakerName && (
                <span className="text-slate-400 text-[9px] max-w-[90px] truncate">
                  &bull; {hoveredWaveTime.speakerName}
                </span>
              )}
            </div>
          )}

          <div
            ref={waveformRef}
            onClick={onWaveformClick}
            onMouseMove={onWaveformMouseMove}
            onMouseLeave={onWaveformMouseLeave}
            className="h-10 flex flex-col justify-between px-1 pt-1 rounded-lg bg-slate-900/80 border border-slate-800/80 cursor-pointer relative overflow-hidden group-hover/wave:border-slate-700/80 transition-colors"
            title="Click or drag to seek in audio"
            suppressHydrationWarning
          >
            {/* Hover Guide Line */}
            {hoveredWaveTime && (
              <div
                className="absolute top-0 bottom-0 w-px bg-white/40 pointer-events-none z-20"
                style={{ left: `${hoveredWaveTime.xPercent}%` }}
              />
            )}

            {/* Glowing Active Playhead Line */}
            {effectiveDuration > 0 && (
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-blue-400 shadow-[0_0_10px_rgba(96,165,250,1)] pointer-events-none z-20 transition-all duration-75"
                style={{
                  left: `${Math.min(100, Math.max(0, progressRatio * 100))}%`,
                }}
              >
                <div className="w-2 h-2 -ml-[3px] -mt-0.5 rounded-full bg-white shadow-md border border-blue-400" />
              </div>
            )}

            {/* Waveform Bars Container */}
            <div className="flex-1 flex items-center justify-between gap-[1.5px] pb-1">
              {waveformBars.map((bar) => {
                const barRatio = bar.index / BARS_COUNT;
                const isPlayed = currentTime > 0 && barRatio <= progressRatio;
                const isCurrent =
                  Math.abs(barRatio - progressRatio) <= 1 / BARS_COUNT;

                return (
                  <div
                    key={bar.index}
                    style={{
                      height: `${bar.height}px`,
                      backgroundColor: bar.isSpeech
                        ? bar.color
                        : isPlayed
                        ? "#64748b"
                        : "#334155",
                      opacity: isPlayed ? 1 : 0.35,
                    }}
                    className={`flex-1 rounded-[1px] transition-all duration-100 hover:opacity-100 ${
                      isCurrent && isPlaying
                        ? "scale-y-115 brightness-125 shadow-[0_0_6px_rgba(59,130,246,0.8)]"
                        : ""
                    }`}
                    title={
                      bar.isSpeech
                        ? `${formatTime(bar.time)} - ${bar.speakerName}`
                        : formatTime(bar.time)
                    }
                  />
                );
              })}
            </div>

            {/* Audio Scrubber Track */}
            <div className="w-full h-1 bg-slate-800/80 rounded-b overflow-hidden relative">
              <div
                className="h-full bg-blue-500 transition-all duration-75"
                style={{
                  width: `${effectiveDuration > 0 ? progressRatio * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        </div>

        {/* 4. Transport Controls */}
        <div className="flex items-center justify-between gap-1 pt-0.5">
          <button
            onClick={() => onSeekTo(0)}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/80 transition-all active:scale-95 cursor-pointer"
            title="Jump to start (Home)"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onJumpPreviousTurn}
            className="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800/80 transition-all active:scale-95 cursor-pointer"
            title="Previous turn ([)"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => onSkipSeconds(-skipStep)}
            className="px-2 py-1 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800/80 transition-all active:scale-95 flex items-center gap-0.5 cursor-pointer"
            title={`Rewind ${skipStep}s (J / Left Arrow)`}
          >
            <span className="text-[10px] font-mono font-bold">-{skipStep}s</span>
          </button>

          {/* Master Play/Pause Button */}
          <button
            onClick={onTogglePlay}
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-150 active:scale-90 cursor-pointer ${
              isPlaying
                ? "bg-blue-600 hover:bg-blue-500 text-white ring-4 ring-blue-500/25 shadow-[0_0_14px_rgba(59,130,246,0.5)]"
                : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-950/60 ring-2 ring-blue-400/20 hover:scale-105"
            }`}
            title="Play / Pause (Space)"
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 fill-current" />
            ) : (
              <Play className="w-4 h-4 fill-current ml-0.5" />
            )}
          </button>

          <button
            onClick={() => onSkipSeconds(skipStep)}
            className="px-2 py-1 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800/80 transition-all active:scale-95 flex items-center gap-0.5 cursor-pointer"
            title={`Forward ${skipStep}s (L / Right Arrow)`}
          >
            <span className="text-[10px] font-mono font-bold">+{skipStep}s</span>
          </button>

          <button
            onClick={onJumpNextTurn}
            className="p-1.5 text-slate-300 hover:text-white rounded-lg hover:bg-slate-800/80 transition-all active:scale-95 cursor-pointer"
            title="Next turn (])"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onToggleLoopTurn}
            className={`p-1.5 rounded-lg transition-all active:scale-95 cursor-pointer ${
              isLoopingTurn
                ? "text-amber-300 bg-amber-950/60 border border-amber-500/50 ring-1 ring-amber-500/40 shadow-[0_0_8px_rgba(245,158,11,0.3)] animate-pulse"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/80"
            }`}
            title={
              isLoopingTurn
                ? "Turn loop active - click to disable"
                : "Loop current speaker turn"
            }
          >
            <Repeat className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* 5. Speed, Sync & Volume Sub-Bar */}
        <div className="pt-2 border-t border-slate-800/80 space-y-2">
          <div className="flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-0.5 bg-slate-900 p-0.5 rounded-lg border border-slate-800/80">
              {[0.75, 1.0, 1.25, 1.5, 2.0].map((spd) => (
                <button
                  key={spd}
                  onClick={() => onSetSpeed(spd)}
                  className={`px-1.5 py-0.5 rounded-md font-mono text-[10px] font-medium transition-colors cursor-pointer ${
                    playbackSpeed === spd
                      ? "bg-blue-600 text-white font-bold shadow-2xs"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {spd}x
                </button>
              ))}
            </div>

            <button
              onClick={onToggleFollow}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[10px] font-mono border transition-all cursor-pointer ${
                followPlayhead
                  ? "bg-blue-950/70 text-blue-300 border-blue-700/60 shadow-2xs font-semibold"
                  : "bg-slate-900 text-slate-500 border-slate-800 hover:text-slate-300"
              }`}
              title="Toggle auto-scrolling transcript with playback"
            >
              <Eye className="w-3 h-3" />
              <span>Auto-Scroll</span>
            </button>
          </div>

          <div className="flex items-center justify-between text-[11px] text-slate-400">
            <div className="flex items-center gap-1.5">
              <button
                onClick={onToggleMute}
                className="text-slate-400 hover:text-white transition-colors cursor-pointer"
                title={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted || volume === 0 ? (
                  <VolumeX className="w-3.5 h-3.5 text-rose-400" />
                ) : (
                  <Volume2 className="w-3.5 h-3.5 text-slate-300" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={(e) => onVolumeChange(Number(e.target.value))}
                className="w-20 h-1 bg-slate-800 rounded-lg cursor-pointer accent-blue-500"
              />
              <span className="font-mono text-[10px] text-slate-500 w-7">
                {isMuted ? "0%" : `${Math.round(volume * 100)}%`}
              </span>
            </div>

            <div className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
              <kbd className="px-1.5 py-0.5 bg-slate-900 border border-slate-800 rounded text-slate-400 text-[9px] font-semibold">
                Space
              </kbd>
              <span>Play</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
