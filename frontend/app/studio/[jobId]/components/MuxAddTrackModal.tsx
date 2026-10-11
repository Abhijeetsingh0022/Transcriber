"use client";

import React, { useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Check,
  ChevronDown,
  ChevronUp,
  Loader2,
  Music,
  UploadCloud,
  X,
} from "lucide-react";
import { CustomDropdown, DropdownOption } from "./CustomDropdown";
import { LANGUAGE_PRESETS } from "../muxConstants";

const LABEL_PRESETS = ["English Dub", "Hindi Audio", "Original Dialogue", "Commentary", "Background Music"];
const QUICK_LANGS = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
];
const CODEC_OPTIONS: DropdownOption[] = [
  { value: "copy", label: "Copy (Lossless Passthrough)" },
  { value: "aac", label: "AAC (Universal Streaming)" },
  { value: "libopus", label: "Opus (High Efficiency)" },
  { value: "libmp3lame", label: "MP3 (Legacy Audio)" },
  { value: "flac", label: "FLAC (Lossless Master)" },
];

interface MuxAddTrackModalProps {
  onClose: () => void;
  onAdd: (opts: {
    file: File;
    label: string;
    language: string;
    codec: string;
    disposition: string;
    isDefault: boolean;
  }) => Promise<void>;
  isUploading: boolean;
  error: string | null;
}

export function MuxAddTrackModal({
  onClose,
  onAdd,
  isUploading,
  error,
}: MuxAddTrackModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [label, setLabel] = useState("");
  const [language, setLanguage] = useState("en");
  const [codec, setCodec] = useState("copy");
  const [disposition, setDisposition] = useState("none");
  const [isDefault, setIsDefault] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const languageOptions: DropdownOption[] = useMemo(
    () => LANGUAGE_PRESETS.map((l) => ({ value: l.code, label: `${l.label} (${l.code})` })),
    []
  );

  const pickFile = (f: File) => {
    setFile(f);
    if (!label) setLabel(f.name.replace(/\.[^.]+$/, ""));
  };

  const handleAdd = () => {
    if (!file || !label.trim()) return;
    onAdd({ file, label: label.trim(), language, codec, disposition, isDefault });
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
            <Music className="w-4 h-4 text-emerald-600" />
            <h4 className="font-bold text-sm text-slate-900">Add Audio Track</h4>
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
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            const f = e.dataTransfer.files?.[0];
            if (f) pickFile(f);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-all ${
            isDragging
              ? "border-emerald-500 bg-emerald-50/70"
              : file
              ? "border-emerald-300 bg-emerald-50/30"
              : "border-slate-200 hover:border-emerald-300 bg-slate-50 hover:bg-emerald-50/20"
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.wav,.mp3,.aac,.m4a,.opus,.flac"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) pickFile(f);
            }}
            className="hidden"
          />
          {file ? (
            <div className="flex items-center justify-between p-2 bg-white rounded-lg border border-emerald-200">
              <div className="flex items-center gap-2 min-w-0">
                <Music className="w-4 h-4 text-emerald-600 shrink-0" />
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
              <UploadCloud className="w-6 h-6 text-emerald-600 mx-auto" />
              <p className="text-xs font-bold text-slate-800">Drop audio track here or click to browse</p>
              <p className="text-[10px] text-slate-400">WAV, MP3, AAC, M4A, FLAC, Opus</p>
            </div>
          )}
        </div>

        {/* Label & Language */}
        <div className="space-y-3">
          {/* Label */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-[11px] font-semibold text-slate-700">Track Label</label>
              <span className="text-[9px] text-slate-400 font-mono">Custom title</span>
            </div>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. English Dub, Hindi Commentary"
              className="w-full bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-900 focus:outline-none focus:border-emerald-600 font-medium"
            />
            <div className="flex items-center gap-1.5 flex-wrap mt-1.5">
              {LABEL_PRESETS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setLabel(p)}
                  className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 hover:bg-emerald-50 text-slate-600 hover:text-emerald-700 border border-slate-200 transition-colors cursor-pointer"
                >
                  + {p}
                </button>
              ))}
            </div>
          </div>

          {/* Language quick picks */}
          <div className="space-y-1.5">
            <label className="text-[11px] font-semibold text-slate-700 block">Language</label>
            <div className="flex items-center gap-1.5 flex-wrap">
              {QUICK_LANGS.map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLanguage(lang.code)}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-medium border transition-colors cursor-pointer ${
                    language === lang.code
                      ? "bg-emerald-600 text-white border-emerald-600"
                      : "bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200"
                  }`}
                >
                  {lang.label}
                </button>
              ))}
            </div>
            <CustomDropdown
              label="Or select other language:"
              value={language}
              onChange={setLanguage}
              options={languageOptions}
              searchable
              direction="auto"
            />
          </div>

          {/* Advanced */}
          <div className="pt-0.5">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-[11px] text-slate-500 hover:text-slate-800 font-medium flex items-center gap-1 cursor-pointer"
            >
              {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {showAdvanced ? "Hide Advanced Settings" : "Advanced Stream Settings"}
            </button>
            {showAdvanced && (
              <div className="mt-2 p-2.5 bg-slate-50 rounded-lg border border-slate-200 space-y-2 animate-in fade-in duration-100">
                <CustomDropdown
                  label="Audio Codec"
                  value={codec}
                  onChange={setCodec}
                  options={CODEC_OPTIONS}
                  direction="up"
                />
              </div>
            )}
          </div>
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
            onClick={handleAdd}
            disabled={!file || !label.trim() || isUploading}
            className="flex-1 py-2 px-3 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer"
          >
            {isUploading ? (
              <><Loader2 className="w-3.5 h-3.5 animate-spin" /><span>Uploading...</span></>
            ) : (
              <><Check className="w-3.5 h-3.5" /><span>Add Audio Track</span></>
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
