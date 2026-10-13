"use client";

import React, { useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Film,
  Headphones,
  Layers,
  Loader2,
  Play,
  RotateCw,
  Sliders,
  Terminal,
  VolumeX,
} from "lucide-react";
import { MuxJob } from "../types";
import { API_BASE } from "../utils";
import { OUTPUT_FORMAT_OPTIONS } from "../muxConstants";
import { CustomCheckbox } from "./CustomCheckbox";

interface MuxExportPanelProps {
  jobId: string;
  trackCount: number;
  customVideoName?: string | null;
  muxJob: MuxJob | null;
  isMuxing: boolean;
  outputFormat: "mp4" | "mkv" | "mov";
  muxMode: "tracks" | "blend";
  muteAllAudio: boolean;
  playerMode: "source" | "output";
  onOutputFormatChange: (f: "mp4" | "mkv" | "mov") => void;
  onMuxModeChange: (m: "tracks" | "blend") => void;
  onMuteAllAudioChange: (v: boolean) => void;
  onStartMux: () => void;
  onWatchOutput: () => void;
}

export function MuxExportPanel({
  jobId,
  trackCount,
  customVideoName,
  muxJob,
  isMuxing,
  outputFormat,
  muxMode,
  muteAllAudio,
  playerMode,
  onOutputFormatChange,
  onMuxModeChange,
  onMuteAllAudioChange,
  onStartMux,
  onWatchOutput,
}: MuxExportPanelProps) {
  const [showLogs, setShowLogs] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const exportBtnLabel = isMuxing
    ? "Multiplexing..."
    : muteAllAudio
    ? `Export Silent Video (${outputFormat.toUpperCase()})`
    : muxMode === "blend"
    ? `Export Blended Mix (${trackCount} Tracks)`
    : `Export Multi-Track Video (${trackCount} Tracks)`;

  return (
    <div className="lg:col-span-5 flex flex-col min-h-0 bg-white">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-slate-200 flex items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-emerald-600" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Export Settings</span>
        </div>
        <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
          Lossless Remux
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 min-h-0 p-5 overflow-y-auto space-y-5">

        {/* Audio Layout Mode */}
        {trackCount <= 1 ? (
          <div className="space-y-1.5">
            <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
              Audio Layout
            </label>
            <div className="p-3 rounded-lg border border-slate-200 bg-slate-50/70 text-left">
              <div className="flex items-center gap-1.5 mb-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-xs font-bold text-slate-900">
                  {trackCount === 1 ? "Standard Single Audio Stream" : "No Audio Track"}
                </span>
              </div>
              <span className="block text-[10px] text-slate-500 leading-tight">
                {trackCount === 1
                  ? "Exports video with your selected audio stream. 100% compatible with all devices, browsers, and social platforms."
                  : "Add an audio stem or click Import Original to mux audio onto your video."}
              </span>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
                Audio Layout Mode
              </label>
              <span className="text-[10px] text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
                {trackCount} Stems Active
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2">
              {([
                {
                  id: "blend" as const,
                  icon: Sliders,
                  label: "Blended Mix",
                  desc: "Mixes all tracks into 1 universal soundtrack. Plays everywhere (phones, YouTube, web).",
                },
                {
                  id: "tracks" as const,
                  icon: Headphones,
                  label: "Multi-Track",
                  desc: "Keeps language streams separate (switchable in VLC & media players).",
                },
              ]).map(({ id, icon: Icon, label, desc }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => onMuxModeChange(id)}
                  className={`p-3 rounded-lg border text-left transition-all active:scale-95 cursor-pointer ${
                    muxMode === id
                      ? "border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500/20"
                      : "border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-emerald-600" />
                      <span className="text-xs font-bold text-slate-900">{label}</span>
                    </div>
                    {muxMode === id && (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    )}
                  </div>
                  <span className="block text-[10px] text-slate-500 leading-tight">{desc}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Mute All */}
        <div
          onClick={() => onMuteAllAudioChange(!muteAllAudio)}
          className={`flex items-center justify-between p-3 border rounded-lg cursor-pointer text-xs transition-all select-none ${
            muteAllAudio
              ? "bg-rose-50 border-rose-200 ring-1 ring-rose-500/15"
              : "bg-slate-50 border-slate-200 hover:bg-slate-100"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <div
              className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                muteAllAudio ? "bg-rose-600 text-white" : "bg-rose-50 border border-rose-100 text-rose-500"
              }`}
            >
              <VolumeX className="w-3.5 h-3.5" />
            </div>
            <div>
              <span className="font-semibold text-slate-900 block">Mute All Audio (Silent Output)</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">
                Export video without any audio streams (-an flag)
              </span>
            </div>
          </div>
          <CustomCheckbox checked={muteAllAudio} onChange={onMuteAllAudioChange} size="sm" />
        </div>

        {/* Container Format */}
        <div className="space-y-2">
          <label className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            Container Format
          </label>
          <div className="grid grid-cols-3 gap-2">
            {OUTPUT_FORMAT_OPTIONS.map((fmt) => {
              const isSelected = outputFormat === fmt.id;
              return (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => onOutputFormatChange(fmt.id as "mp4" | "mkv" | "mov")}
                  className={`p-2.5 rounded-lg border text-center transition-all active:scale-95 cursor-pointer ${
                    isSelected
                      ? "border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500/20 text-emerald-900"
                      : "border-slate-200 hover:border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <span className="block text-xs font-bold">{fmt.label.split(" ")[0]}</span>
                  <span className="block text-[9px] text-slate-400 mt-0.5">{fmt.id.toUpperCase()}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Summary */}
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-2">
          <div className="flex items-center justify-between text-[11px] font-bold text-slate-700">
            <span>Multiplexing Summary</span>
            <span className="font-mono text-[10px] text-slate-500">
              {muteAllAudio
                ? "0 Audio (Silent)"
                : trackCount <= 1
                ? "1 Standard Track"
                : muxMode === "blend"
                ? "1 Blended Audio Mix"
                : `${trackCount} Audio Tracks`}
            </span>
          </div>
          <div className="space-y-1 text-[11px] text-slate-600">
            <div className="flex items-center justify-between">
              <span>Visual:</span>
              <span className="font-semibold text-slate-800 truncate max-w-[180px]">
                {customVideoName || "Source Video"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span>Audio:</span>
              <span className="font-semibold text-slate-800">
                {muteAllAudio
                  ? "Muted (-an)"
                  : trackCount <= 1
                  ? "1 active audio stream"
                  : muxMode === "blend"
                  ? `Blended mix (${trackCount} stems combined)`
                  : `${trackCount} discrete language stream(s)`}
              </span>
            </div>
          </div>
        </div>

        {/* Export CTA */}
        <button
          type="button"
          onClick={onStartMux}
          disabled={(!muteAllAudio && trackCount === 0) || isMuxing}
          className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 disabled:opacity-50 text-white rounded-lg font-bold text-sm shadow-sm hover:shadow-md transition-all active:scale-[0.98] flex items-center justify-center gap-2 cursor-pointer"
        >
          {isMuxing ? (
            <><Loader2 className="w-4 h-4 animate-spin" /><span>Multiplexing...</span></>
          ) : muteAllAudio ? (
            <><VolumeX className="w-4 h-4" /><span>Export Silent Video ({outputFormat.toUpperCase()})</span></>
          ) : trackCount === 0 ? (
            <><AlertCircle className="w-4 h-4" /><span>Add Audio Track to Export</span></>
          ) : trackCount === 1 ? (
            <><Layers className="w-4 h-4" /><span>Export Video with Audio ({outputFormat.toUpperCase()})</span></>
          ) : muxMode === "blend" ? (
            <><Sliders className="w-4 h-4" /><span>Export Blended Mix ({trackCount} Tracks)</span></>
          ) : (
            <><Headphones className="w-4 h-4" /><span>Export Multi-Track Video ({trackCount} Tracks)</span></>
          )}
        </button>

        {/* Status card */}
        {muxJob && muxJob.status !== "not_started" && (
          <div
            className={`p-3.5 rounded-lg border text-xs space-y-2.5 ${
              muxJob.status === "completed"
                ? "bg-emerald-50 border-emerald-200 text-emerald-950"
                : muxJob.status === "failed"
                ? "bg-rose-50 border-rose-200 text-rose-950"
                : "bg-blue-50 border-blue-200 text-blue-950"
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold">
                {muxJob.status === "completed" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : muxJob.status === "failed" ? (
                  <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                ) : (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin shrink-0" />
                )}
                <span className="capitalize">
                  {muxJob.status === "processing" ? "Processing…" : `Status: ${muxJob.status}`}
                </span>
              </div>
              {muxJob.status === "processing" && (
                <span className="font-mono text-[10px] font-bold text-blue-700 bg-blue-100 px-1.5 py-0.5 rounded-lg">
                  {Math.round(muxJob.progress || 0)}%
                </span>
              )}
            </div>

            {muxJob.status === "processing" && (
              <div className="space-y-1">
                <div className="w-full bg-blue-200/60 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${Math.max(5, Math.min(100, muxJob.progress || 0))}%` }}
                  />
                </div>
                <span className="text-[10px] text-blue-900 block truncate">
                  {muxJob.stage || "Multiplexing audio & video streams…"}
                </span>
              </div>
            )}

            {muxJob.status === "completed" && (
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={onWatchOutput}
                  className={`flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg font-bold text-xs transition-all active:scale-95 cursor-pointer ${
                    playerMode === "output"
                      ? "bg-emerald-700 text-white ring-2 ring-emerald-400/40"
                      : "bg-slate-900 hover:bg-slate-800 text-emerald-400 border border-emerald-500/30"
                  }`}
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  {playerMode === "output" ? "Watching" : "Watch Output"}
                </button>
                <a
                  href={`${API_BASE}/jobs/${jobId}/mux/download`}
                  download
                  className="flex items-center justify-center gap-1.5 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs transition-all active:scale-95 cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </a>
              </div>
            )}

            {muxJob.status === "failed" && muxJob.error_message && (
              <div className="space-y-2">
                <p className="text-[11px] text-rose-800 font-mono bg-white/70 p-2 rounded-lg border border-rose-200 break-words">
                  {muxJob.error_message}
                </p>
                <button
                  type="button"
                  onClick={onStartMux}
                  className="w-full flex items-center justify-center gap-1.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg font-semibold text-xs transition-all cursor-pointer"
                >
                  <RotateCw className="w-3 h-3" />
                  Retry
                </button>
              </div>
            )}

            {muxJob.logs && muxJob.logs.length > 0 && (
              <div className="pt-0.5">
                <button
                  type="button"
                  onClick={() => setShowLogs(!showLogs)}
                  className="text-[10px] text-slate-500 hover:text-slate-700 underline flex items-center gap-1 cursor-pointer"
                >
                  <Terminal className="w-3 h-3" />
                  {showLogs ? "Hide pipeline logs" : "View pipeline logs"}
                </button>
                {showLogs && (
                  <div className="mt-1.5 p-2 rounded-lg bg-slate-900 text-slate-200 font-mono text-[9px] leading-relaxed max-h-28 overflow-y-auto">
                    {muxJob.logs.map((line, i) => (
                      <div key={i} className="truncate">{line}</div>
                    ))}
                    <div ref={logsEndRef} />
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
