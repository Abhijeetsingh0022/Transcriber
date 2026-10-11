"use client";

import React from "react";
import { Layers, Volume2, FileText, Sparkles } from "lucide-react";
import { SystemTelemetry, QueueStats } from "../types";
import { formatDuration } from "../utils";

interface TelemetryDeckProps {
  stats: QueueStats;
  telemetry: SystemTelemetry | null;
}

const CARDS = [
  {
    label: "Active Queue",
    icon: Layers,
    // Blue accent — secondary brand color
    iconBg: "bg-blue-50 border-blue-100",
    iconColor: "text-blue-600",
    render: (s: QueueStats) => ({
      value: s.total.toString(),
      unit: "files",
      sub: (
        <div className="flex items-center gap-2 text-[11px] font-medium">
          <span className="inline-flex items-center gap-1 text-emerald-600">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {s.completed} ready
          </span>
          <span className="text-gray-300">•</span>
          <span className="inline-flex items-center gap-1 text-blue-600">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
            {s.processing} active
          </span>
        </div>
      ),
    }),
  },
  {
    label: "Audio Processed",
    icon: Volume2,
    iconBg: "bg-emerald-50 border-emerald-100",
    iconColor: "text-emerald-600",
    render: (s: QueueStats) => ({
      value: formatDuration(s.totalSec),
      unit: "recorded",
      sub: (
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-500 truncate">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          16kHz Mono Acoustic Stream
        </span>
      ),
    }),
  },
  {
    label: "Words Transcribed",
    icon: FileText,
    // Sky blue variant for differentiation
    iconBg: "bg-sky-50 border-sky-100",
    iconColor: "text-sky-600",
    render: (s: QueueStats) => ({
      value: s.totalWords.toLocaleString(),
      unit: "words",
      sub: (
        <span className="inline-flex items-center gap-1.5 text-[11px] font-medium text-slate-500 truncate">
          <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
          Diarized & Timestamps Aligned
        </span>
      ),
    }),
  },
  {
    label: "AI Acceleration",
    icon: Sparkles,
    iconBg: "bg-amber-50 border-amber-100",
    iconColor: "text-amber-600",
    render: (_s: QueueStats, t: SystemTelemetry | null) => ({
      value: t?.platform || "Local Neural",
      unit: "",
      sub: (
        <div className="flex items-center justify-between w-full text-[11px] font-medium text-slate-500">
          <span>Whisper Large-v3</span>
          {t && <span className="font-mono text-[10px] text-slate-400">{t.system_ram_available_gb.toFixed(1)} GB Free</span>}
        </div>
      ),
    }),
  },
] as const;

export function TelemetryDeck({ stats, telemetry }: TelemetryDeckProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-4 mb-6">
      {CARDS.map(({ label, icon: Icon, iconBg, iconColor, render }) => {
        const { value, unit, sub } = render(stats, telemetry);
        return (
          <div
            key={label}
            className="bg-white border border-gray-200/80 hover:border-blue-200/60 rounded-lg p-3 sm:p-4 shadow-sm hover:shadow-md transition-all duration-200 group cursor-default min-w-0 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-1.5 sm:mb-2 gap-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider truncate">{label}</span>
                <div
                  className={`w-6 h-6 sm:w-7 sm:h-7 rounded-lg ${iconBg} border flex items-center justify-center ${iconColor} group-hover:scale-110 transition-transform duration-200 shrink-0`}
                >
                  <Icon className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
                </div>
              </div>
              <div className="flex items-baseline gap-1.5 sm:gap-2 min-w-0">
                <span className="text-lg sm:text-2xl font-bold text-slate-900 font-mono tracking-tight truncate">{value}</span>
                {unit && <span className="text-[11px] sm:text-xs text-slate-500 font-medium shrink-0">{unit}</span>}
              </div>
            </div>
            <div className="mt-2 min-w-0">{sub}</div>
          </div>
        );
      })}
    </div>
  );
}
