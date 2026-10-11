"use client";

import React, { memo, useState, useEffect } from "react";
import {
  Check,
  ChevronDown,
  ChevronUp,
  Pause,
  Play,
  Pencil,
  Star,
  Trash2,
  Globe,
  X,
} from "lucide-react";
import { MuxTrack } from "../types";
import { DISPOSITION_LABELS, LANGUAGE_PRESETS } from "../muxConstants";

interface MuxTrackCardProps {
  track: MuxTrack;
  index: number;
  isFirst: boolean;
  isLast: boolean;
  isPlaying: boolean;
  gain: number;
  isMuted: boolean;
  isSoloed: boolean;
  onTogglePreview: (track: MuxTrack) => void;
  onGainChange: (trackId: string, gain: number) => void;
  onToggleMute: (trackId: string) => void;
  onToggleSolo: (trackId: string) => void;
  onSetDefault: (trackId: string) => void;
  onMove: (trackId: string, direction: "up" | "down") => void;
  onDelete: (trackId: string) => void;
  onUpdateLabel?: (trackId: string, label: string) => void;
  onUpdateLanguage?: (trackId: string, language: string) => void;
  compact?: boolean;
}

export const MuxTrackCard = memo(function MuxTrackCard({
  track,
  index,
  isFirst,
  isLast,
  isPlaying,
  gain,
  isMuted,
  isSoloed,
  onTogglePreview,
  onGainChange,
  onToggleMute,
  onToggleSolo,
  onSetDefault,
  onMove,
  onDelete,
  onUpdateLabel,
  onUpdateLanguage,
  compact = false,
}: MuxTrackCardProps) {
  const [isEditingLabel, setIsEditingLabel] = useState(false);
  const [editedLabel, setEditedLabel] = useState(track.label);
  const [isLangDropdownOpen, setIsLangDropdownOpen] = useState(false);

  useEffect(() => {
    if (!isEditingLabel) setEditedLabel(track.label);
  }, [track.label, isEditingLabel]);

  const langMeta = LANGUAGE_PRESETS.find((l) => l.code === track.language);
  const langLabel = langMeta ? langMeta.label : track.language.toUpperCase();
  const dispositionLabel = DISPOSITION_LABELS[track.disposition] || track.disposition;
  const channelText = track.channels === 2 ? "Stereo" : track.channels === 1 ? "Mono" : `${track.channels}ch`;
  const rateText = track.sample_rate ? `${(track.sample_rate / 1000).toFixed(1)}kHz` : "44.1kHz";
  const bitrateText = track.bitrate ? `${Math.round(track.bitrate / 1000)}kbps` : "Lossless";
  const gainPct = Math.round(gain * 100);
  const gainDb = gain === 0 ? "-∞ dB" : gain === 1 ? "0.0 dB" : `${(20 * Math.log10(gain)).toFixed(1)} dB`;

  const handleSaveLabel = () => {
    const trimmed = editedLabel.trim();
    if (trimmed && trimmed !== track.label) onUpdateLabel?.(track.id, trimmed);
    setIsEditingLabel(false);
  };

  return (
    <div
      className={`rounded-lg border transition-all duration-200 ${
        isPlaying
          ? "bg-emerald-50 border-emerald-200 ring-2 ring-emerald-500/15 shadow-sm"
          : isSoloed
          ? "bg-amber-50 border-amber-200 ring-1 ring-amber-400/20"
          : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-sm"
      } ${compact ? "p-3 space-y-2" : "p-4 space-y-3"}`}
    >
      {/* Top Row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          {/* Track number / equalizer badge */}
          <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 text-xs font-bold ${
            isPlaying ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600 border border-slate-200"
          }`}>
            {isPlaying ? (
              <div className="flex items-end gap-0.5 h-3 w-4">
                <span className="w-0.5 bg-white rounded-full animate-bounce h-full" style={{ animationDelay: "0ms" }} />
                <span className="w-0.5 bg-white rounded-full animate-bounce h-2/3" style={{ animationDelay: "100ms" }} />
                <span className="w-0.5 bg-white rounded-full animate-bounce h-4/5" style={{ animationDelay: "200ms" }} />
                <span className="w-0.5 bg-white rounded-full animate-bounce h-1/2" style={{ animationDelay: "50ms" }} />
              </div>
            ) : (
              index + 1
            )}
          </div>

          {/* Preview button */}
          <button
            type="button"
            onClick={() => onTogglePreview(track)}
            className={`w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-150 active:scale-95 shrink-0 cursor-pointer ${
              isPlaying
                ? "bg-emerald-600 text-white shadow-sm"
                : "bg-slate-100 hover:bg-emerald-50 text-slate-600 hover:text-emerald-600 border border-slate-200 hover:border-emerald-200"
            }`}
            title={isPlaying ? "Pause stem preview" : "Preview stem audio"}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5 fill-current" /> : <Play className="w-3.5 h-3.5 fill-current ml-0.5" />}
          </button>

          {/* Label + specs */}
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              {isEditingLabel ? (
                <div className="flex items-center gap-1.5 py-0.5">
                  <input
                    type="text"
                    value={editedLabel}
                    onChange={(e) => setEditedLabel(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleSaveLabel();
                      else if (e.key === "Escape") { setEditedLabel(track.label); setIsEditingLabel(false); }
                    }}
                    autoFocus
                    placeholder="Track name..."
                    className="bg-white border-2 border-emerald-500 rounded-lg px-2 py-0.5 text-xs font-semibold text-slate-900 focus:outline-none shadow-sm min-w-[130px] max-w-[200px]"
                  />
                  <button type="button" onClick={handleSaveLabel} className="p-1 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer">
                    <Check className="w-3 h-3" />
                  </button>
                  <button type="button" onClick={() => { setEditedLabel(track.label); setIsEditingLabel(false); }} className="p-1 rounded-lg bg-slate-100 text-slate-500 hover:bg-slate-200 cursor-pointer">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 group/label">
                  <span
                    onClick={() => { setEditedLabel(track.label); setIsEditingLabel(true); }}
                    className="font-semibold text-slate-900 text-sm truncate cursor-pointer hover:text-emerald-700 transition-colors"
                    title="Click to rename"
                  >
                    {track.label}
                  </span>
                  <button
                    type="button"
                    onClick={() => { setEditedLabel(track.label); setIsEditingLabel(true); }}
                    className="opacity-0 group-hover/label:opacity-100 p-0.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-all cursor-pointer shrink-0"
                  >
                    <Pencil className="w-2.5 h-2.5" />
                  </button>
                </div>
              )}

              {track.is_default && (
                <span className="inline-flex items-center gap-1 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 shrink-0">
                  <Star className="w-2.5 h-2.5 fill-amber-500 text-amber-500" />
                  Default
                </span>
              )}
              {dispositionLabel !== "None" && dispositionLabel !== "Default" && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  {dispositionLabel}
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-400 flex items-center gap-1.5 flex-wrap font-mono mt-0.5">
              <span>{channelText}</span>
              <span className="text-slate-300">·</span>
              <span>{rateText}</span>
              <span className="text-slate-300">·</span>
              <span>{bitrateText}</span>
              <span className="text-slate-300">·</span>
              <span className="uppercase">{track.codec}</span>
            </div>
          </div>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-1 shrink-0">
          {/* Language */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsLangDropdownOpen((p) => !p)}
              className="text-[11px] font-medium px-2 py-1 rounded-lg bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 inline-flex items-center gap-1 cursor-pointer transition-colors"
            >
              <Globe className="w-2.5 h-2.5 text-slate-400" />
              <span>{langLabel}</span>
              <ChevronDown className="w-2.5 h-2.5 text-slate-400" />
            </button>
            {isLangDropdownOpen && (
              <div className="absolute right-0 top-full mt-1 z-30 bg-white border border-slate-200 rounded-lg shadow-lg py-1 w-40 max-h-48 overflow-y-auto">
                {LANGUAGE_PRESETS.map((lang) => (
                  <button
                    key={lang.code}
                    type="button"
                    onClick={() => { onUpdateLanguage?.(track.id, lang.code); setIsLangDropdownOpen(false); }}
                    className={`w-full text-left px-3 py-1.5 text-[11px] flex items-center justify-between hover:bg-slate-50 cursor-pointer ${
                      track.language === lang.code ? "font-semibold text-emerald-700 bg-emerald-50/50" : "text-slate-700"
                    }`}
                  >
                    <span>{lang.label}</span>
                    <span className="text-[9px] font-mono uppercase text-slate-400">{lang.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Move up/down */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-white overflow-hidden">
            <button type="button" onClick={() => onMove(track.id, "up")} disabled={isFirst} className="p-1 hover:bg-slate-50 text-slate-400 hover:text-slate-700 disabled:opacity-25 transition-colors cursor-pointer">
              <ChevronUp className="w-3.5 h-3.5" />
            </button>
            <div className="w-px h-4 bg-slate-200" />
            <button type="button" onClick={() => onMove(track.id, "down")} disabled={isLast} className="p-1 hover:bg-slate-50 text-slate-400 hover:text-slate-700 disabled:opacity-25 transition-colors cursor-pointer">
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Set default */}
          <button
            type="button"
            onClick={() => onSetDefault(track.id)}
            className={`p-1.5 rounded-lg border transition-all active:scale-95 cursor-pointer ${
              track.is_default ? "bg-amber-50 text-amber-600 border-amber-200" : "bg-white text-slate-400 hover:text-amber-500 border-slate-200 hover:bg-slate-50"
            }`}
            title={track.is_default ? "Default track" : "Set as default"}
          >
            <Star className={`w-3.5 h-3.5 ${track.is_default ? "fill-amber-500 text-amber-500" : ""}`} />
          </button>

          {/* Delete */}
          <button type="button" onClick={() => onDelete(track.id)} className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 rounded-lg transition-all active:scale-95 cursor-pointer">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Fader strip */}
      <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between gap-3">
        <div className="flex-1 flex items-center gap-2.5 min-w-0">
          <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-400 shrink-0 w-8">Gain</span>
          <div className="relative flex-1">
            <input
              type="range"
              min={0}
              max={1.5}
              step={0.01}
              value={gain}
              disabled={isMuted}
              onChange={(e) => onGainChange(track.id, parseFloat(e.target.value))}
              className="w-full h-1.5 rounded-full appearance-none cursor-pointer disabled:opacity-40"
              style={{
                background: isMuted
                  ? "#e2e8f0"
                  : `linear-gradient(to right, #10b981 0%, #10b981 ${(gain / 1.5) * 100}%, #e2e8f0 ${(gain / 1.5) * 100}%, #e2e8f0 100%)`,
              }}
            />
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <span className={`font-mono text-xs font-semibold px-2 py-0.5 rounded-lg min-w-[52px] text-center border ${
              isMuted ? "bg-rose-50 text-rose-600 border-rose-200" : "bg-slate-50 text-slate-700 border-slate-200"
            }`}>
              {isMuted ? "MUTED" : `${gainPct}%`}
            </span>
            <span className="font-mono text-[10px] text-slate-400 min-w-[44px] text-right hidden sm:inline-block">
              {isMuted ? "-∞" : gainDb}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={() => onToggleMute(track.id)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold transition-all active:scale-95 cursor-pointer border ${
              isMuted ? "bg-rose-600 text-white border-rose-600" : "bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200"
            }`}
          >M</button>
          <button
            type="button"
            onClick={() => onToggleSolo(track.id)}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-bold transition-all active:scale-95 cursor-pointer border ${
              isSoloed ? "bg-amber-500 text-white border-amber-500" : "bg-slate-50 hover:bg-slate-100 text-slate-600 border-slate-200"
            }`}
          >S</button>
        </div>
      </div>
    </div>
  );
});
