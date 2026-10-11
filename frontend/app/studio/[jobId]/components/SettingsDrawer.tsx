"use client";

import React from "react";
import { X } from "lucide-react";
import { FontSize } from "../types";

interface SettingsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  fontSize: FontSize;
  onFontSizeChange: (size: FontSize) => void;
  playbackSpeed: number;
  onSpeedChange: (speed: number) => void;
}

export function SettingsDrawer({
  isOpen,
  onClose,
  fontSize,
  onFontSizeChange,
  playbackSpeed,
  onSpeedChange,
}: SettingsDrawerProps) {
  if (!isOpen) return null;

  return (
    <div className="absolute right-3 sm:right-6 top-16 w-64 max-w-[calc(100vw-1.5rem)] bg-white border border-slate-200 rounded-lg shadow-xl p-4 z-40 space-y-4 animate-popover">
      <div className="flex items-center justify-between pb-2 border-b border-slate-100">
        <span className="font-semibold text-xs text-slate-900">Display Settings</span>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Font Size Selector */}
      <div>
        <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
          Typography Size
        </label>
        <div className="grid grid-cols-4 gap-1 bg-slate-100 p-1 rounded-lg">
          {(["sm", "base", "lg", "xl"] as const).map((s) => (
            <button
              key={s}
              onClick={() => onFontSizeChange(s)}
              className={`py-1 text-xs rounded-lg uppercase font-mono font-medium ${
                fontSize === s
                  ? "bg-white text-slate-900 shadow-2xs font-bold"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Playback Speed Quick Control */}
      <div>
        <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1.5">
          Playback Speed
        </label>
        <div className="grid grid-cols-5 gap-1 bg-slate-100 p-1 rounded-lg">
          {[0.75, 1.0, 1.25, 1.5, 2.0].map((spd) => (
            <button
              key={spd}
              onClick={() => onSpeedChange(spd)}
              className={`py-1 text-[11px] rounded-lg font-mono ${
                playbackSpeed === spd
                  ? "bg-blue-600 text-white font-bold"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
