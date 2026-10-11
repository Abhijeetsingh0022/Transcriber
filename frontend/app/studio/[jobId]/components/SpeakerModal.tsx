"use client";

import React from "react";
import { X, Sparkles, Loader2, Users } from "lucide-react";
import { SpeakerStat } from "../types";

interface SpeakerModalProps {
  isOpen: boolean;
  onClose: () => void;
  speakerStats: SpeakerStat[];
  speakerNames: Record<string, string>;
  onChangeSpeakerName: (speakerLabel: string, name: string) => void;
  onApply: () => void;
  onIdentifySpeakers?: () => void;
  isIdentifyingSpeakers?: boolean;
}

export function SpeakerModal({
  isOpen,
  onClose,
  speakerStats,
  speakerNames,
  onChangeSpeakerName,
  onApply,
  onIdentifySpeakers,
  isIdentifyingSpeakers,
}: SpeakerModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-in fade-in duration-150">
      <div className="bg-white border border-slate-200 rounded-lg shadow-2xl p-4 sm:p-5 max-w-[calc(100vw-2rem)] sm:max-w-lg w-full text-slate-900 max-h-[92dvh] flex flex-col">
        <div className="flex items-center justify-between mb-3.5 shrink-0">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 shrink-0">
              <Users className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <h3 className="font-semibold text-slate-900 text-sm truncate">Speaker Roster &amp; Identification</h3>
              <p className="text-[11px] text-slate-500 truncate">
                Manage speaker roles, character names, and conversational metrics.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Smart AI Auto-Identification Banner */}
        {onIdentifySpeakers && (
          <div className="mb-3.5 p-3 bg-gradient-to-r from-amber-50 via-amber-50/80 to-orange-50/60 border border-amber-200/90 rounded-lg flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5 sm:gap-3 shadow-2xs shrink-0">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-900">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                <span>Smart Auto-Identification</span>
              </div>
              <p className="text-[11px] text-amber-700 leading-snug mt-0.5">
                Automatically distinguishes dialogue and speech turns into clean roles.
              </p>
            </div>
            <button
              type="button"
              onClick={onIdentifySpeakers}
              disabled={isIdentifyingSpeakers}
              className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-semibold text-xs shadow-xs transition-all active:scale-95 shrink-0 disabled:opacity-50 flex items-center justify-center gap-1.5 cursor-pointer text-center"
            >
              {isIdentifyingSpeakers ? (
                <>
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Detecting...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3 h-3" />
                  <span>Auto-Detect</span>
                </>
              )}
            </button>
          </div>
        )}

        <div className="space-y-2.5 mb-4 overflow-y-auto flex-1 min-h-0 pr-1">
          {speakerStats.map((spk) => (
            <div key={spk.id} className="p-2.5 sm:p-3 border border-slate-200 rounded-lg bg-slate-50/70 space-y-1.5">
              <div className="flex items-center gap-2 sm:gap-3 text-xs">
                <span
                  className="w-3 h-3 sm:w-3.5 sm:h-3.5 rounded-full shrink-0 ring-2 ring-white shadow-2xs"
                  style={{ backgroundColor: spk.color_hex }}
                />
                <span className="w-16 sm:w-24 font-mono text-slate-500 font-semibold truncate shrink-0">{spk.speaker_label}:</span>
                <input
                  type="text"
                  value={speakerNames[spk.speaker_label] || ""}
                  onChange={(e) => onChangeSpeakerName(spk.speaker_label, e.target.value)}
                  placeholder="e.g. Speaker 1, Speaker 2"
                  className="flex-1 bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-slate-900 focus:outline-none focus:border-blue-600 text-xs shadow-2xs font-medium min-w-0"
                />
              </div>

              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center text-[10px] sm:text-[11px] text-slate-500 font-mono px-1 sm:px-6 gap-0.5">
                <span>
                  Talk time: {spk.talkTime}s ({spk.percentage}%)
                </span>
                <span>
                  {spk.turnsCount} turns &bull; {spk.wordCount} words ({spk.avgWpm} WPM)
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end gap-2 text-xs border-t border-slate-100 pt-3">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 border border-slate-200 rounded-lg text-slate-600 hover:bg-slate-50 font-medium transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            onClick={onApply}
            className="px-3.5 py-1.5 bg-slate-900 text-white rounded-lg hover:bg-slate-800 font-semibold transition-colors cursor-pointer shadow-xs"
          >
            Apply Names
          </button>
        </div>
      </div>
    </div>
  );
}
