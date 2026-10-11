"use client";

import React, { useRef, useState } from "react";
import {
  AlertCircle,
  Check,
  Film,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";
import { CustomCheckbox } from "./CustomCheckbox";

interface MuxUploadVideoModalProps {
  onClose: () => void;
  onApply: (opts: {
    file: File;
    extractAudio: boolean;
    audioLabel: string;
    audioLang: string;
  }) => Promise<void>;
  isUploading: boolean;
  error: string | null;
}

const LABEL_PRESETS = ["Hindi Audio", "Original Dialogue", "Hindi Dub", "Voice Track"];

export function MuxUploadVideoModal({
  onClose,
  onApply,
  isUploading,
  error,
}: MuxUploadVideoModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [extractAudio, setExtractAudio] = useState(true);
  const [audioLabel, setAudioLabel] = useState("Video Audio (Hindi)");
  const [audioLang, setAudioLang] = useState("hi");

  const handleApply = () => {
    if (!file) return;
    onApply({ file, extractAudio, audioLabel, audioLang });
  };

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-[60] p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-md w-full p-5 space-y-4 animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Film className="w-4 h-4 text-blue-600" />
            <h4 className="font-bold text-sm text-slate-900">Upload / Replace Video</h4>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drop zone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${
            file
              ? "border-blue-400 bg-blue-50/40"
              : "border-slate-200 hover:border-blue-300 bg-slate-50 hover:bg-blue-50/20"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mp4,.mkv,.mov,.avi,.webm,.m4v"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFile(f);
            }}
            className="hidden"
          />
          {file ? (
            <div className="flex items-center justify-between p-2 bg-white rounded-lg border border-blue-200">
              <div className="flex items-center gap-2 min-w-0">
                <Film className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="text-xs font-semibold text-slate-800 truncate">{file.name}</span>
                <span className="text-[10px] text-slate-400 font-mono shrink-0">
                  ({(file.size / (1024 * 1024)).toFixed(1)} MB)
                </span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setFile(null);
                  if (fileInputRef.current) fileInputRef.current.value = "";
                }}
                className="text-slate-400 hover:text-rose-600 p-1 cursor-pointer"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="py-2 space-y-1">
              <UploadCloud className="w-6 h-6 text-blue-500 mx-auto" />
              <p className="text-xs font-bold text-slate-800">Click to select video or drop file</p>
              <p className="text-[10px] text-slate-400">MP4, MKV, MOV, WebM</p>
            </div>
          )}
        </div>

        {/* Options */}
        <div className="space-y-2">
          <div
            onClick={() => setExtractAudio(!extractAudio)}
            className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer select-none transition-all ${
              extractAudio ? "bg-blue-50/60 border-blue-200" : "bg-slate-50 border-slate-200"
            }`}
          >
            <div>
              <span className="text-xs font-semibold text-slate-800 block">Extract Audio as Track</span>
              <span className="text-[10px] text-slate-500 block mt-0.5">
                Extract this video's audio into your track roster
              </span>
            </div>
            <CustomCheckbox checked={extractAudio} onChange={setExtractAudio} size="sm" />
          </div>

          {extractAudio && (
            <div className="space-y-2 pt-1">
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Track Label</label>
                <input
                  type="text"
                  value={audioLabel}
                  onChange={(e) => setAudioLabel(e.target.value)}
                  placeholder="e.g. Hindi Audio, Original Dialogue"
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-blue-500 font-medium"
                />
                <div className="flex items-center gap-1.5 flex-wrap mt-1">
                  {LABEL_PRESETS.map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setAudioLabel(p)}
                      className="text-[9px] px-1.5 py-0.5 rounded-full bg-slate-100 hover:bg-blue-50 text-slate-600 hover:text-blue-700 border border-slate-200 transition-colors cursor-pointer"
                    >
                      + {p}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-semibold text-slate-600 block mb-1">Language</label>
                <select
                  value={audioLang}
                  onChange={(e) => setAudioLang(e.target.value)}
                  className="w-full bg-white border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-blue-500 cursor-pointer"
                >
                  <option value="hi">Hindi (hi)</option>
                  <option value="en">English (en)</option>
                  <option value="es">Spanish (es)</option>
                  <option value="und">Other / Undetermined</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="p-2 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-xs flex items-center gap-1.5">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={handleApply}
            disabled={!file || isUploading}
            className="flex-1 py-2 px-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
          >
            {isUploading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /><span>Processing...</span></>
            ) : (
              <><Check className="w-3.5 h-3.5" /><span>Apply Video</span></>
            )}
          </button>
          <button
            type="button"
            onClick={onClose}
            className="py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-medium cursor-pointer"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
