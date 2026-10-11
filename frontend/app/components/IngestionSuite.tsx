"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  UploadCloud,
  Link2,
  Mic,
  Square,
  Loader2,
  ChevronDown,
  Check,
  Search,
  Users,
  SlidersHorizontal,
  Globe,
  Settings,
} from "lucide-react";
import {
  MODES,
  LANGUAGES,
  TASK_OPTIONS,
  DIARIZATION_OPTIONS,
} from "../constants";
import { formatDuration } from "../utils";

interface IngestionSuiteProps {
  uploadTab: "file" | "url" | "record";
  setUploadTab: (tab: "file" | "url" | "record") => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  isUploading: boolean;
  isDragOver: boolean;
  setIsDragOver: (dragOver: boolean) => void;
  onFilesSelected: (files: FileList | null) => void;

  urlInput: string;
  setUrlInput: (val: string) => void;
  onUrlSubmit: (e: React.FormEvent) => void;

  isRecording: boolean;
  recordingSeconds: number;
  onStartRecording: () => void;
  onStopRecording: () => void;

  mode: string;
  setMode: (mode: string) => void;
  language: string;
  setLanguage: (lang: string) => void;
  task: string;
  setTask: (task: string) => void;
  diarize: boolean;
  setDiarize: (diarize: boolean) => void;
  numSpeakers: number | "";
  setNumSpeakers: (speakers: number | "") => void;
  restoreAudio: boolean;
  setRestoreAudio: (restore: boolean) => void;
  initialPrompt: string;
  setInitialPrompt: (prompt: string) => void;
  showAdvanced: boolean;
  setShowAdvanced: (show: boolean) => void;
  onOpenModelManager?: () => void;
}

export function IngestionSuite({
  uploadTab,
  setUploadTab,
  fileInputRef,
  isUploading,
  isDragOver,
  setIsDragOver,
  onFilesSelected,
  urlInput,
  setUrlInput,
  onUrlSubmit,
  isRecording,
  recordingSeconds,
  onStartRecording,
  onStopRecording,
  mode,
  setMode,
  language,
  setLanguage,
  task,
  setTask,
  diarize,
  setDiarize,
  numSpeakers,
  setNumSpeakers,
  restoreAudio,
  setRestoreAudio,
  initialPrompt,
  setInitialPrompt,
  showAdvanced,
  setShowAdvanced,
  onOpenModelManager,
}: IngestionSuiteProps) {
  // Dropdown states
  const [modeOpen, setModeOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const [taskOpen, setTaskOpen] = useState(false);
  const [diarizeOpen, setDiarizeOpen] = useState(false);
  const [langSearch, setLangSearch] = useState("");

  const modeRef = useRef<HTMLDivElement>(null);
  const langRef = useRef<HTMLDivElement>(null);
  const taskRef = useRef<HTMLDivElement>(null);
  const diarizeRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (modeRef.current && !modeRef.current.contains(event.target as Node)) {
        setModeOpen(false);
      }
      if (langRef.current && !langRef.current.contains(event.target as Node)) {
        setLangOpen(false);
      }
      if (taskRef.current && !taskRef.current.contains(event.target as Node)) {
        setTaskOpen(false);
      }
      if (diarizeRef.current && !diarizeRef.current.contains(event.target as Node)) {
        setDiarizeOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentModeObj = MODES.find((m) => m.id === mode) || MODES[0];
  const currentLangObj = LANGUAGES.find((l) => l.code === language) || LANGUAGES[0];
  const currentTaskObj = TASK_OPTIONS.find((t) => t.id === task) || TASK_OPTIONS[0];

  const currentDiarizeObj = useMemo(() => {
    if (!diarize) {
      return DIARIZATION_OPTIONS.find((d) => d.id === "off") || DIARIZATION_OPTIONS[5];
    }
    if (numSpeakers === 3) {
      return DIARIZATION_OPTIONS.find((d) => d.id === "narrator_2") || DIARIZATION_OPTIONS[1];
    }
    if (numSpeakers === 2) {
      return DIARIZATION_OPTIONS.find((d) => d.id === "2") || DIARIZATION_OPTIONS[2];
    }
    if (numSpeakers === 4) {
      return DIARIZATION_OPTIONS.find((d) => d.id === "4") || DIARIZATION_OPTIONS[3];
    }
    if (typeof numSpeakers === "number" && numSpeakers >= 5) {
      return DIARIZATION_OPTIONS.find((d) => d.id === "5") || DIARIZATION_OPTIONS[4];
    }
    return DIARIZATION_OPTIONS.find((d) => d.id === "auto") || DIARIZATION_OPTIONS[0];
  }, [diarize, numSpeakers]);

  const filteredLanguages = useMemo(() => {
    return LANGUAGES.filter((l) =>
      l.name.toLowerCase().includes(langSearch.toLowerCase())
    );
  }, [langSearch]);

  return (
    <div
      id="upload-card"
      className="bg-white border border-slate-200/90 rounded-lg shadow-xs overflow-visible scroll-mt-24"
    >
      {/* Top Segmented Pill Switcher */}
      <div className="p-3.5 pb-0 border-b border-slate-100 flex items-center justify-between">
        <div className="bg-slate-100/90 p-1 rounded-lg flex items-center gap-1">
          <button
            type="button"
            onClick={() => setUploadTab("file")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              uploadTab === "file"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <UploadCloud className="w-3.5 h-3.5" />
            <span>Upload Media</span>
          </button>

          <button
            type="button"
            onClick={() => setUploadTab("url")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              uploadTab === "url"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Link2 className="w-3.5 h-3.5" />
            <span>YouTube / URL</span>
          </button>

          <button
            type="button"
            onClick={() => setUploadTab("record")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
              uploadTab === "record"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            <Mic className="w-3.5 h-3.5" />
            <span>Dictation</span>
            <span className="bg-rose-100 text-rose-700 text-[9px] font-bold px-1 py-0.2 rounded-lg">Live</span>
          </button>
        </div>

        <span className="text-[11px] text-slate-400 hidden sm:inline font-mono">Max 10 GB</span>
      </div>

      {/* Ingestion Input Canvas */}
      <div className="p-5">
        {uploadTab === "file" && (
          <>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept="audio/*,video/*"
              className="hidden"
              onChange={(e) => onFilesSelected(e.target.files)}
            />

            {/* Interactive Dropzone */}
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragOver(false);
                onFilesSelected(e.dataTransfer.files);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`group relative border-2 border-dashed rounded-lg py-9 px-6 flex flex-col items-center justify-center cursor-pointer transition-all duration-200 ${
                isDragOver
                  ? "border-blue-500 bg-blue-50/50 scale-[0.99] shadow-inner"
                  : "border-slate-200/90 hover:border-slate-300 bg-slate-50/60 hover:bg-slate-50/90"
              }`}
            >
              {isUploading ? (
                <div className="flex flex-col items-center gap-2.5">
                  <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
                  <p className="text-xs font-semibold text-slate-800">Uploading and queuing media...</p>
                  <p className="text-[11px] text-slate-400">Processing audio extract &amp; telemetry</p>
                </div>
              ) : (
                <>
                  <div className="w-11 h-11 rounded-lg bg-white border border-slate-200/90 flex items-center justify-center shadow-xs mb-3 group-hover:-translate-y-1 group-hover:shadow-md transition-all duration-200">
                    <UploadCloud className="w-5 h-5 text-blue-600" />
                  </div>
                  <p className="text-xs font-semibold text-slate-900">
                    Drop media files here or{" "}
                    <span className="text-blue-600 underline underline-offset-2">browse files</span>
                  </p>
                  <div className="flex flex-wrap items-center justify-center gap-1.5 mt-3 text-[10px] text-slate-400 font-mono">
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">MP4</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">MOV</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">MKV</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">MP3</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">WAV</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">M4A</span>
                    <span className="bg-white px-1.5 py-0.5 rounded-lg border border-slate-200">FLAC</span>
                  </div>
                </>
              )}
            </div>
          </>
        )}

        {uploadTab === "url" && (
          <form
            onSubmit={onUrlSubmit}
            className="py-5 sm:py-6 px-3.5 sm:px-4 bg-slate-50/70 border border-slate-200 rounded-lg flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5 sm:gap-3"
          >
            <div className="flex items-center gap-2.5 flex-1 min-w-0 bg-white border border-slate-300 rounded-lg px-3 py-2 shadow-2xs focus-within:border-slate-900">
              <Link2 className="w-4 h-4 text-slate-400 shrink-0" />
              <input
                type="url"
                placeholder="Paste YouTube or video stream URL..."
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
                className="flex-1 bg-transparent text-xs text-slate-900 focus:outline-none min-w-0"
              />
            </div>
            <button
              type="submit"
              disabled={isUploading || !urlInput.trim()}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white rounded-lg text-xs font-semibold transition-all shadow-xs shrink-0 cursor-pointer active:scale-95 text-center"
            >
              {isUploading ? "Downloading..." : "Queue URL"}
            </button>
          </form>
        )}

        {uploadTab === "record" && (
          <div className="py-8 px-6 bg-slate-50/70 border border-slate-200 rounded-lg flex flex-col items-center justify-center text-center">
            <div className="relative mb-3">
              <div
                className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
                  isRecording
                    ? "bg-rose-500 text-white shadow-lg shadow-rose-200 ring-4 ring-rose-100 animate-pulse"
                    : "bg-white border border-slate-200 text-slate-700 shadow-xs"
                }`}
              >
                <Mic className="w-6 h-6" />
              </div>
            </div>

            {isRecording ? (
              <div className="flex flex-col items-center gap-3">
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-600 animate-ping" />
                  <span className="font-mono text-xl font-bold text-slate-900">
                    {formatDuration(recordingSeconds)}
                  </span>
                </div>
                <p className="text-xs text-slate-500">Live microphone stream active. Speak clearly.</p>
                <button
                  type="button"
                  onClick={onStopRecording}
                  className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-lg transition-all shadow-xs cursor-pointer active:scale-95"
                >
                  <Square className="w-3.5 h-3.5 fill-current" />
                  <span>Stop &amp; Transcribe</span>
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <p className="text-xs font-semibold text-slate-800">Direct In-Browser Voice Dictation</p>
                <p className="text-[11px] text-slate-500 max-w-sm">
                  Record voice memos, meetings, or thoughts with native Web Audio. When stopped, it will be automatically uploaded and transcribed locally.
                </p>
                <button
                  type="button"
                  onClick={onStartRecording}
                  className="flex items-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold text-xs rounded-lg transition-all shadow-xs cursor-pointer active:scale-95"
                >
                  <Mic className="w-3.5 h-3.5" />
                  <span>Start Recording</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* 3. Form Controls (2x2 Grid with Uniform Custom Dropdowns) */}
        <div className="mt-5 pt-4 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
          {/* Control 1: Model Engine */}
          <div className={`relative ${modeOpen ? "z-30" : "z-10"}`} ref={modeRef}>
            <label className="block text-slate-500 font-semibold mb-1 text-[11px] uppercase tracking-wider">
              Model Engine
            </label>
            <button
              type="button"
              onClick={() => {
                setModeOpen(!modeOpen);
                setLangOpen(false);
                setTaskOpen(false);
                setDiarizeOpen(false);
              }}
              className="w-full h-10 bg-white border border-slate-200/90 hover:border-slate-300 rounded-lg px-3 flex items-center justify-between text-left transition-all shadow-2xs focus:outline-none focus:border-slate-900 cursor-pointer active:scale-[0.99]"
            >
              <div className="flex items-center gap-2 truncate">
                <currentModeObj.icon className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="font-semibold text-slate-900 truncate">{currentModeObj.name}</span>
                <span className="text-[10px] text-slate-400 font-mono">({currentModeObj.model})</span>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${modeOpen ? "rotate-180" : ""}`} />
            </button>

            {modeOpen && (
              <div className="absolute left-0 mt-1.5 w-full sm:w-72 max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1.5 z-50 animate-popover max-h-80 overflow-y-auto ring-1 ring-slate-900/10">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Select ASR Model Tier
                </div>
                {MODES.map((m) => {
                  const Icon = m.icon;
                  const isSelected = m.id === mode;
                  return (
                    <div
                      key={m.id}
                      onClick={() => {
                        setMode(m.id);
                        setModeOpen(false);
                      }}
                      className={`px-3 py-2 cursor-pointer flex items-start gap-2.5 hover:bg-slate-50 transition-colors ${
                        isSelected ? "bg-slate-50/80 font-medium" : ""
                      }`}
                    >
                      <Icon className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-900 font-semibold">{m.name}</span>
                          <span className={`text-[9px] px-1.5 py-0.2 border rounded-lg font-mono ${m.badgeColor}`}>
                            {m.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 leading-tight mt-0.5">{m.description}</p>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />}
                    </div>
                  );
                })}

                {onOpenModelManager && (
                  <div className="p-2 border-t border-slate-100 bg-slate-50/80 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => {
                        setModeOpen(false);
                        onOpenModelManager();
                      }}
                      className="w-full py-1 text-[11px] font-semibold text-blue-600 hover:text-blue-700 hover:bg-blue-50/60 rounded flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                    >
                      <Settings className="w-3 h-3" />
                      <span>Manage Speech Models &amp; Storage</span>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Control 2: Spoken Language */}
          <div className={`relative ${langOpen ? "z-30" : "z-10"}`} ref={langRef}>
            <label className="block text-slate-500 font-semibold mb-1 text-[11px] uppercase tracking-wider">
              Spoken Language
            </label>
            <button
              type="button"
              onClick={() => {
                setLangOpen(!langOpen);
                setModeOpen(false);
                setTaskOpen(false);
                setDiarizeOpen(false);
              }}
              className="w-full h-10 bg-white border border-slate-200/90 hover:border-slate-300 rounded-lg px-3 flex items-center justify-between text-left transition-all shadow-2xs focus:outline-none focus:border-slate-900 cursor-pointer active:scale-[0.99]"
            >
              <div className="flex items-center gap-2 truncate">
                {currentLangObj.code === "auto" ? (
                  <Globe className="w-4 h-4 text-slate-500 shrink-0" />
                ) : (
                  <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                    {currentLangObj.code.toUpperCase()}
                  </span>
                )}
                <span className="font-semibold text-slate-900 truncate">{currentLangObj.name}</span>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${langOpen ? "rotate-180" : ""}`} />
            </button>

            {langOpen && (
              <div className="absolute left-0 sm:left-auto sm:right-0 mt-1.5 w-full sm:w-72 max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1.5 z-50 animate-popover max-h-80 ring-1 ring-slate-900/10 flex flex-col">
                <div className="p-2 border-b border-slate-100">
                  <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1">
                    <Search className="w-3 h-3 text-slate-400 shrink-0" />
                    <input
                      type="text"
                      placeholder="Search language..."
                      value={langSearch}
                      onChange={(e) => setLangSearch(e.target.value)}
                      className="bg-transparent text-xs text-slate-900 focus:outline-none w-full"
                      autoFocus
                    />
                  </div>
                </div>
                <div className="max-h-56 overflow-y-auto divide-y divide-slate-50">
                  {filteredLanguages.map((l) => {
                    const isSelected = l.code === language;
                    return (
                      <div
                        key={l.code}
                        onClick={() => {
                          setLanguage(l.code);
                          setLangOpen(false);
                          setLangSearch("");
                        }}
                        className={`px-3 py-2 cursor-pointer flex items-center justify-between hover:bg-slate-50 transition-colors text-xs ${
                          isSelected ? "bg-slate-50 font-semibold" : ""
                        }`}
                      >
                        <span className="flex items-center gap-2 truncate">
                          {l.code === "auto" ? (
                            <Globe className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                          ) : (
                            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
                              {l.code.toUpperCase()}
                            </span>
                          )}
                          <span className="text-slate-800 truncate">{l.name}</span>
                        </span>
                        {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0" />}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Control 3: Speaker Diarization */}
          <div className="relative" ref={diarizeRef}>
            <div className="flex items-center justify-between mb-1">
              <label className="text-slate-500 font-semibold text-[11px] uppercase tracking-wider">
                Speaker Diarization
              </label>
              <button
                type="button"
                onClick={() => {
                  if (diarize) {
                    setDiarize(false);
                    setNumSpeakers("");
                  } else {
                    setDiarize(true);
                    setNumSpeakers(3); // default to Smart Auto-ID
                  }
                }}
                className={`text-[10px] font-semibold px-1.5 py-0.2 rounded-lg transition-colors ${
                  diarize ? "text-emerald-700 hover:text-emerald-800" : "text-slate-400 hover:text-slate-600"
                }`}
              >
                {diarize ? "Enabled" : "Disabled"}
              </button>
            </div>

            <button
              type="button"
              onClick={() => {
                setDiarizeOpen(!diarizeOpen);
                setModeOpen(false);
                setLangOpen(false);
                setTaskOpen(false);
              }}
              className="w-full h-10 bg-white border border-slate-200/90 hover:border-slate-300 rounded-lg px-3 flex items-center justify-between text-left transition-all shadow-2xs focus:outline-none focus:border-slate-900 cursor-pointer active:scale-[0.99]"
            >
              <div className="flex items-center gap-2 truncate">
                <Users className={`w-4 h-4 shrink-0 ${diarize ? "text-blue-600" : "text-slate-400"}`} />
                <span className="font-semibold text-slate-900 truncate">{currentDiarizeObj.label}</span>
                {currentDiarizeObj.badge && (
                  <span
                    className={`text-[9px] px-1.5 py-0.2 rounded-lg font-mono border ${
                      currentDiarizeObj.badgeColor || "bg-slate-100 text-slate-600 border-slate-200"
                    }`}
                  >
                    {currentDiarizeObj.badge}
                  </span>
                )}
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${diarizeOpen ? "rotate-180" : ""}`} />
            </button>

            {diarizeOpen && (
              <div className="absolute left-0 mt-1.5 w-full sm:w-72 max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1.5 z-50 animate-popover max-h-80 overflow-y-auto ring-1 ring-slate-900/10">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Select Diarization Preset
                </div>
                {DIARIZATION_OPTIONS.map((opt) => {
                  const isSelected =
                    opt.diarize === diarize &&
                    (opt.numSpeakers === "" ? numSpeakers === "" : numSpeakers === opt.numSpeakers);

                  return (
                    <div
                      key={opt.id}
                      onClick={() => {
                        setDiarize(opt.diarize);
                        setNumSpeakers(opt.numSpeakers);
                        setDiarizeOpen(false);
                      }}
                      className={`px-3 py-2 cursor-pointer flex items-start gap-2.5 hover:bg-slate-50 transition-colors ${
                        isSelected ? "bg-slate-50/80 font-medium" : ""
                      }`}
                    >
                      <Users className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-900 font-semibold">{opt.label}</span>
                          <span
                            className={`text-[9px] px-1.5 py-0.2 rounded-lg font-mono border ${
                              opt.badgeColor || "bg-slate-100 text-slate-600 border-slate-200"
                            }`}
                          >
                            {opt.badge}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 leading-tight mt-0.5">{opt.sublabel}</p>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Control 4: Target Task Dropdown */}
          <div className={`relative ${taskOpen ? "z-30" : "z-10"}`} ref={taskRef}>
            <label className="block text-slate-500 font-semibold mb-1 text-[11px] uppercase tracking-wider">
              Target Task
            </label>
            <button
              type="button"
              onClick={() => {
                setTaskOpen(!taskOpen);
                setModeOpen(false);
                setLangOpen(false);
                setDiarizeOpen(false);
              }}
              className="w-full h-10 bg-white border border-slate-200/90 hover:border-slate-300 rounded-lg px-3 flex items-center justify-between text-left transition-all shadow-2xs focus:outline-none focus:border-slate-900 cursor-pointer active:scale-[0.99]"
            >
              <div className="flex items-center gap-2 truncate">
                <currentTaskObj.icon className="w-4 h-4 text-blue-600 shrink-0" />
                <span className="font-semibold text-slate-900 truncate">{currentTaskObj.name}</span>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform ${taskOpen ? "rotate-180" : ""}`} />
            </button>

            {taskOpen && (
              <div className="absolute left-0 sm:left-auto sm:right-0 mt-1.5 w-full sm:w-72 max-w-[calc(100vw-2.5rem)] bg-white border border-slate-200/90 rounded-lg shadow-2xl py-1.5 z-50 animate-popover max-h-80 overflow-y-auto ring-1 ring-slate-900/10">
                <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  Select Pipeline Task
                </div>
                {TASK_OPTIONS.map((t) => {
                  const Icon = t.icon;
                  const isSelected = t.id === task;
                  return (
                    <div
                      key={t.id}
                      onClick={() => {
                        setTask(t.id);
                        setTaskOpen(false);
                      }}
                      className={`px-3 py-2 cursor-pointer flex items-start gap-2.5 hover:bg-slate-50 transition-colors ${
                        isSelected ? "bg-slate-50 font-medium" : ""
                      }`}
                    >
                      <Icon className="w-4 h-4 text-blue-600 mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-xs text-slate-900 font-semibold block">{t.name}</span>
                        <p className="text-[11px] text-slate-500 leading-tight mt-0.5">{t.description}</p>
                      </div>
                      {isSelected && <Check className="w-3.5 h-3.5 text-blue-600 shrink-0 mt-0.5" />}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* 4. Collapsible Advanced Options */}
        <div className="mt-4 pt-3 border-t border-slate-100">
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center justify-between w-full text-slate-500 hover:text-slate-800 text-xs font-semibold py-1 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-1.5">
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Advanced Audio Tuning &amp; Prompt Vocabulary</span>
            </div>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
          </button>

          {showAdvanced && (
            <div className="mt-3 p-3.5 bg-slate-50/70 border border-slate-200/90 rounded-lg space-y-3.5 animate-in fade-in duration-150">
              {/* DeepFilterNet Toggle Switch */}
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="font-semibold text-xs text-slate-800">Restore Audio (DeepFilterNet)</div>
                  <p className="text-[11px] text-slate-500 leading-relaxed mt-0.5">
                    Deep neural suppression for background HVAC hum, room reverb, and static noise.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setRestoreAudio(!restoreAudio)}
                  className={`w-10 h-6 flex items-center rounded-full p-1 transition-colors cursor-pointer shrink-0 ${
                    restoreAudio ? "bg-blue-600" : "bg-slate-300"
                  }`}
                >
                  <div
                    className={`bg-white w-4 h-4 rounded-full shadow-md transform transition-transform ${
                      restoreAudio ? "translate-x-4" : "translate-x-0"
                    }`}
                  />
                </button>
              </div>

              {/* Custom Prompt Input */}
              <div>
                <label className="block font-semibold text-xs text-slate-800 mb-1">
                  Custom Vocabulary &amp; Proper Nouns
                </label>
                <input
                  type="text"
                  placeholder="e.g. Technical terms, speaker names, acronyms, domain jargon..."
                  value={initialPrompt}
                  onChange={(e) => setInitialPrompt(e.target.value)}
                  className="w-full bg-white border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-slate-900 shadow-2xs"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
