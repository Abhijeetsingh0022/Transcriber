"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  X,
  RotateCw,
  Archive,
  Trash2,
  Layers,
  FileVideo,
  FileAudio,
  Eye,
  ChevronUp,
  Users,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ExternalLink,
  Download,
  ChevronDown,
  FileText,
  Volume2,
  FileCode,
  FileSpreadsheet,
  Check,
  Copy,
  Film,
} from "lucide-react";
import { Job, QueueStats } from "../types";
import { formatDuration, formatFileSize } from "../utils";
import { API_BASE } from "../constants";

function parseStageTelemetry(stage?: string) {
  if (!stage) return { label: "Processing...", progress: null, eta: null };
  const match = stage.match(/\((\d+)s\s*\/\s*(\d+)s\)/);
  if (match) {
    const elapsed = parseInt(match[1], 10);
    const total = parseInt(match[2], 10);
    const remaining = Math.max(0, total - elapsed);
    const label = stage.replace(/\s*\(\d+s\s*\/\s*\d+s\)/, "").trim();
    return {
      label: label || "Transcribing",
      progress: `${elapsed}s / ${total}s`,
      eta: remaining > 0 ? `~${remaining}s left` : null,
    };
  }
  return { label: stage, progress: null, eta: null };
}

interface QueueSectionProps {
  filteredJobs: Job[];
  allJobsCount: number;
  stats: QueueStats;
  statusFilter: string;
  setStatusFilter: (status: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  selectedJobIds: string[];
  onSelectAll: () => void;
  onToggleSelect: (id: string) => void;
  onClearCompleted: () => void;
  onRefresh: () => void;
  onOpenBulkExport: () => void;
  onBulkDelete: () => void;

  expandedJobId: string | null;
  setExpandedJobId: (id: string | null) => void;
  activeExportMenu: string | null;
  setActiveExportMenu: (id: string | null) => void;
  exportMenuRef: React.RefObject<HTMLDivElement | null>;
  copiedSnippetId: string | null;
  onCopySnippet: (id: string, text: string) => void;
  onRetry: (id: string) => void;
  onDelete: (id: string) => void;
}

export function QueueSection({
  filteredJobs,
  allJobsCount,
  stats,
  statusFilter,
  setStatusFilter,
  searchQuery,
  setSearchQuery,
  selectedJobIds,
  onSelectAll,
  onToggleSelect,
  onClearCompleted,
  onRefresh,
  onOpenBulkExport,
  onBulkDelete,
  expandedJobId,
  setExpandedJobId,
  activeExportMenu,
  setActiveExportMenu,
  exportMenuRef,
  copiedSnippetId,
  onCopySnippet,
  onRetry,
  onDelete,
}: QueueSectionProps) {
  const [menuCoords, setMenuCoords] = useState<{
    top: number;
    right: number;
    openUpwards: boolean;
  } | null>(null);

  // Close fixed export menu on window scroll/resize to prevent misaligned floating
  useEffect(() => {
    if (!activeExportMenu) return;
    const handleScrollOrResize = () => {
      setActiveExportMenu(null);
      setMenuCoords(null);
    };
    window.addEventListener("scroll", handleScrollOrResize, true);
    window.addEventListener("resize", handleScrollOrResize);
    return () => {
      window.removeEventListener("scroll", handleScrollOrResize, true);
      window.removeEventListener("resize", handleScrollOrResize);
    };
  }, [activeExportMenu, setActiveExportMenu]);

  const toggleExportMenu = (jobId: string, buttonEl: HTMLElement) => {
    if (activeExportMenu === jobId) {
      setActiveExportMenu(null);
      setMenuCoords(null);
    } else {
      const rect = buttonEl.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const openUpwards = spaceBelow < 420 && rect.top > 320;
      setMenuCoords({
        top: openUpwards ? rect.top - 6 : rect.bottom + 6,
        right: Math.max(12, window.innerWidth - rect.right),
        openUpwards,
      });
      setActiveExportMenu(jobId);
    }
  };

  return (
    <div
      id="queue-section"
      className="bg-white border border-slate-200/90 rounded-lg shadow-xs overflow-visible scroll-mt-24"
    >
      {/* Queue Top Bar: Status Tabs, Search, and Action Controls */}
      <div className="px-3.5 sm:px-5 py-3 sm:py-3.5 border-b border-slate-100 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-white">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1 bg-slate-100/90 p-1 rounded-lg overflow-x-auto no-scrollbar max-w-full shrink-0">
          <button
            onClick={() => setStatusFilter("all")}
            className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
              statusFilter === "all"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            All ({stats.total})
          </button>
          <button
            onClick={() => setStatusFilter("completed")}
            className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
              statusFilter === "completed"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Completed ({stats.completed})
          </button>
          <button
            onClick={() => setStatusFilter("processing")}
            className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
              statusFilter === "processing"
                ? "bg-white text-slate-900 shadow-xs"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            Active ({stats.processing})
          </button>
          {stats.queued > 0 && (
            <button
              onClick={() => setStatusFilter("queued")}
              className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
                statusFilter === "queued"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Queued ({stats.queued})
            </button>
          )}
          {stats.failed > 0 && (
            <button
              onClick={() => setStatusFilter("failed")}
              className={`px-2.5 sm:px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap shrink-0 ${
                statusFilter === "failed"
                  ? "bg-rose-700 text-white shadow-xs"
                  : "text-rose-600 hover:text-rose-700"
              }`}
            >
              Failed ({stats.failed})
            </button>
          )}
        </div>

        {/* Search Box & Queue Controls */}
        <div className="flex items-center gap-2 flex-1 md:flex-initial justify-between md:justify-end">
          <div className="relative flex-1 sm:flex-initial">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter media or text..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full sm:w-44 sm:focus:w-56 bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-slate-900 focus:bg-white transition-all shadow-2xs"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            {stats.completed > 0 && (
              <button
                onClick={onClearCompleted}
                title="Clear all completed jobs"
                className="flex items-center gap-1 text-xs text-slate-600 hover:text-slate-900 px-2.5 py-1.5 rounded-lg border border-slate-200/90 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer active:scale-95"
              >
                <span>Clear Done</span>
              </button>
            )}

            <button
              onClick={onRefresh}
              className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg border border-slate-200/90 hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer active:scale-95"
            >
              <RotateCw className="w-3 h-3" />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Floating Multi-Select Action Banner */}
      {selectedJobIds.length > 0 && (
        <div className="px-5 py-2.5 bg-slate-900 text-white flex items-center justify-between text-xs animate-in slide-in-from-top-1 duration-150">
          <div className="flex items-center gap-3">
            <span className="font-semibold">{selectedJobIds.length} item(s) selected</span>
            <span className="text-slate-400">|</span>
            <button
              onClick={onSelectAll}
              className="text-slate-300 hover:text-white underline underline-offset-2 cursor-pointer"
            >
              Deselect all
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onOpenBulkExport}
              className="flex items-center gap-1.5 px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition-all cursor-pointer shadow-xs active:scale-95"
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Bulk Export (.ZIP)</span>
            </button>
            <button
              onClick={onBulkDelete}
              className="flex items-center gap-1.5 px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white font-semibold rounded-lg transition-all cursor-pointer shadow-xs active:scale-95"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete Selected</span>
            </button>
          </div>
        </div>
      )}

      {/* Main Queue Table */}
      {filteredJobs.length === 0 ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400 bg-white">
          <div className="w-14 h-14 rounded-lg bg-slate-50 border border-slate-200/90 flex items-center justify-center mb-3.5 shadow-xs">
            <Layers className="w-7 h-7 text-slate-400 stroke-[1.5]" />
          </div>
          <p className="text-sm font-semibold text-slate-800">No jobs match your filter</p>
          <p className="text-xs text-slate-400 mt-1 max-w-sm text-center">
            {allJobsCount === 0
              ? "Drop media files in the workstation on the left to start transcribing locally with zero cloud limits."
              : "Try clearing your search query or switching status filter tabs."}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto min-h-[300px]">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50/80 border-b border-slate-100 text-slate-500 font-semibold uppercase tracking-wider text-[10px]">
              <tr>
                <th className="py-3 px-3.5 w-9 text-center">
                  <input
                    type="checkbox"
                    checked={selectedJobIds.length > 0 && selectedJobIds.length === filteredJobs.length}
                    onChange={onSelectAll}
                    className="rounded-lg border-slate-300 text-slate-900 focus:ring-0 cursor-pointer"
                  />
                </th>
                <th className="py-3 px-3">Media File</th>
                <th className="py-3 px-3">Audio &amp; Language</th>
                <th className="py-3 px-3">Engine &amp; Speakers</th>
                <th className="py-3 px-3 min-w-[200px]">Progress &amp; Status</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredJobs.map((job) => {
                const isCompleted = job.status === "completed";
                const isProcessing = ["preprocessing", "transcribing", "aligning", "diarizing"].includes(job.status);
                const isFailed = job.status === "failed";
                const isQueued = job.status === "queued";
                const isSelected = selectedJobIds.includes(job.id);
                const isExpanded = expandedJobId === job.id;
                const isVideo = job.filename.match(/\.(mp4|mov|mkv|webm|avi)$/i);

                return (
                  <React.Fragment key={job.id}>
                    <tr
                      className={`hover:bg-slate-50/70 transition-colors ${
                        isSelected ? "bg-blue-50/40" : ""
                      }`}
                    >
                      {/* Checkbox */}
                      <td className="py-3.5 px-3.5 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => onToggleSelect(job.id)}
                          className="rounded-lg border-slate-300 text-slate-900 focus:ring-0 cursor-pointer"
                        />
                      </td>

                      {/* Media File Name & Metadata */}
                      <td className="py-3.5 px-3">
                        <div className="flex items-center gap-2.5">
                          {isVideo ? (
                            <div className="w-8 h-8 rounded-lg bg-cyan-50 border border-cyan-200/80 flex items-center justify-center shrink-0">
                              <FileVideo className="w-4 h-4 text-cyan-600" />
                            </div>
                          ) : (
                            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/80 flex items-center justify-center shrink-0">
                              <FileAudio className="w-4 h-4 text-blue-600" />
                            </div>
                          )}
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-slate-900 truncate max-w-[210px]" title={job.filename}>
                                {job.filename}
                              </span>
                              {isCompleted && job.snippet_text && (
                                <button
                                  type="button"
                                  onClick={() => setExpandedJobId(isExpanded ? null : job.id)}
                                  title="Toggle Transcript Snippet Preview"
                                  className="p-0.5 text-slate-400 hover:text-slate-700 rounded-lg cursor-pointer"
                                >
                                  {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                </button>
                              )}
                            </div>
                            <span className="text-[10px] text-slate-400 font-mono block">
                              {new Date(job.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {formatFileSize(job.file_size_bytes)}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Audio Duration & Detected Language */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-col gap-0.5">
                          <span className="font-mono text-slate-700 font-semibold">
                            {job.duration_seconds > 0 ? formatDuration(job.duration_seconds) : "--:--"}
                          </span>
                          <div className="flex items-center gap-1.5 text-[10px]">
                            <span className="bg-slate-100 text-slate-700 px-1.5 py-0.2 rounded-lg font-mono uppercase font-semibold border border-slate-200/80">
                              {job.detected_language || job.language || "EN"}
                            </span>
                            {job.word_count ? (
                              <span className="text-slate-400 font-mono">
                                {job.word_count} w
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </td>

                      {/* Engine Tier & Diarization Mode */}
                      <td className="py-3.5 px-3">
                        <div className="flex flex-col gap-1 items-start">
                          <span className="bg-slate-100 text-slate-800 px-1.5 py-0.5 rounded-lg font-mono text-[10px] font-semibold border border-slate-200 capitalize">
                            {job.mode.replace("_", " ")}
                          </span>
                          {job.diarize ? (
                            <span className="text-[10px] text-slate-500 flex items-center gap-1 font-medium">
                              <Users className="w-3 h-3 text-slate-400" />
                              <span>
                                {job.num_speakers === 3
                                  ? "Narrator + 2 Spk"
                                  : job.num_speakers
                                  ? `${job.num_speakers} speakers`
                                  : "Diarized"}
                              </span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-400">Single audio</span>
                          )}
                        </div>
                      </td>

                      {/* Progress & Current Stage */}
                      <td className="py-3.5 px-3 min-w-[200px] max-w-[260px]">
                        <div className="flex flex-col gap-1.5">
                          {/* Header: Stage status pill & exact numeric percent */}
                          <div className="flex items-center justify-between text-[11px] leading-tight select-none">
                            <span className="flex items-center gap-1.5 font-semibold">
                              {isProcessing && (
                                <>
                                  {job.status === "transcribing" ? (
                                    /* Active Sound Wave Equalizer */
                                    <span className="flex items-end gap-0.5 h-3.5 w-3.5 px-0.5 pb-0.5 shrink-0" title="Neural Whisper Transcription Active">
                                      <span className="w-0.5 bg-blue-600 rounded-full animate-wave-1" />
                                      <span className="w-0.5 bg-cyan-600 rounded-full animate-wave-2" />
                                      <span className="w-0.5 bg-blue-500 rounded-full animate-wave-3" />
                                    </span>
                                  ) : job.status === "diarizing" ? (
                                    /* Diarization & Role ID Icon */
                                    <span className="relative flex h-2.5 w-2.5 shrink-0">
                                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                                      <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                                    </span>
                                  ) : (
                                    /* Extraction / Ingestion Spinner */
                                    <Loader2 className="w-3 h-3 text-blue-600 animate-spin shrink-0" />
                                  )}
                                </>
                              )}
                              {isCompleted && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />}
                              {isFailed && <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />}
                              {isQueued && <Clock className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                              
                              <span
                                className={`capitalize text-xs font-semibold ${
                                  isCompleted
                                    ? "text-emerald-700"
                                    : isFailed
                                    ? "text-rose-700"
                                    : isProcessing
                                    ? "text-blue-700"
                                    : "text-slate-600"
                                }`}
                              >
                                {job.status}
                              </span>
                            </span>

                            {/* Percentage Badge */}
                            <span
                              className={`font-mono text-[11px] font-bold tabular-nums px-1.5 py-0.2 rounded-lg ${
                                isCompleted
                                  ? "text-emerald-700 bg-emerald-50/80 border border-emerald-200/60"
                                  : isFailed
                                  ? "text-rose-700 bg-rose-50 border border-rose-200/60"
                                  : isProcessing
                                  ? "text-blue-700 bg-blue-50/80 border border-blue-200/60"
                                  : "text-slate-500 bg-slate-100 border border-slate-200/60"
                              }`}
                            >
                              {Math.round(job.progress)}%
                            </span>
                          </div>

                          {/* Premium Progress Bar Track */}
                          <div className="w-full h-2 bg-slate-100/90 rounded-full overflow-hidden relative border border-slate-200/60 shadow-inner">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ease-out relative overflow-hidden ${
                                isCompleted
                                  ? "bg-gradient-to-r from-emerald-500 to-teal-500 shadow-2xs"
                                  : isFailed
                                  ? "bg-rose-500"
                                  : isQueued
                                  ? "bg-slate-300 w-0"
                                  : "bg-gradient-to-r from-blue-600 via-cyan-500 to-blue-500 progress-glow"
                              }`}
                              style={{ width: `${Math.max(isProcessing ? 4 : 0, Math.min(100, Math.round(job.progress)))}%` }}
                            >
                              {/* Internal Shimmer Sweep (Only when processing, does not displace width) */}
                              {isProcessing && (
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer-sweep pointer-events-none" />
                              )}
                              {/* Leading Edge Luminous Bead */}
                              {isProcessing && job.progress > 4 && job.progress < 99 && (
                                <div className="absolute right-0 top-0 bottom-0 w-1 bg-white/90 rounded-full shadow-[0_0_8px_#ffffff]" />
                              )}
                            </div>
                          </div>

                          {/* Stage Description & Timing Telemetry */}
                          {(() => {
                            const telemetry = parseStageTelemetry(job.current_stage);
                            return (
                              <div className="flex items-center justify-between text-[10px] text-slate-500 gap-1 leading-none">
                                <span
                                  className="truncate max-w-[150px]"
                                  title={job.error_message ? `Error: ${job.error_message}` : job.current_stage}
                                >
                                  {job.error_message
                                    ? `Error: ${job.error_message}`
                                    : telemetry.progress
                                    ? `${telemetry.label} (${telemetry.progress})`
                                    : telemetry.label}
                                </span>
                                {telemetry.eta && isProcessing && (
                                  <span className="font-mono text-[9px] text-blue-600 font-medium shrink-0 bg-blue-50/60 px-1 py-0.5 rounded-lg">
                                    {telemetry.eta}
                                  </span>
                                )}
                              </div>
                            );
                          })()}
                        </div>
                      </td>

                      {/* Actions: Studio, Export Dropdown, Delete */}
                      <td className="py-3.5 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5 relative">
                          {isCompleted && (
                            <>
                              <Link
                                href={`/studio?jobId=${job.id}`}
                                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-semibold text-xs transition-all shadow-xs hover:shadow-sm active:scale-95 cursor-pointer"
                              >
                                <ExternalLink className="w-3 h-3" />
                                <span>Studio</span>
                              </Link>                              {/* Optimized 6-Format Export Dropdown */}
                              <div className="relative" data-export-menu="true">
                                <button
                                  type="button"
                                  onClick={(e) => toggleExportMenu(job.id, e.currentTarget)}
                                  aria-expanded={activeExportMenu === job.id}
                                  aria-haspopup="true"
                                  className={`flex items-center gap-1 p-1.5 rounded-lg border transition-all cursor-pointer active:scale-95 ${
                                    activeExportMenu === job.id
                                      ? "bg-slate-900 text-white border-slate-900 shadow-xs"
                                      : "text-slate-600 hover:text-slate-900 border-slate-200/90 hover:bg-slate-50 shadow-2xs"
                                  }`}
                                >
                                  <Download className="w-3.5 h-3.5" />
                                  <ChevronDown
                                    className={`w-2.5 h-2.5 transition-transform duration-200 ${
                                      activeExportMenu === job.id ? "rotate-180 text-white" : "text-slate-400"
                                    }`}
                                  />
                                </button>

                                {activeExportMenu === job.id && menuCoords && (() => {
                                  const fileStem = job.filename ? job.filename.replace(/\.[^/.]+$/, "") : "transcript";
                                  const closeMenu = () => {
                                    setActiveExportMenu(null);
                                    setMenuCoords(null);
                                  };
                                  return (
                                    <>
                                      {/* Viewport Backdrop to safely close menu on click outside */}
                                      <div
                                        className="fixed inset-0 z-[95]"
                                        onClick={closeMenu}
                                      />
                                      <div
                                        ref={exportMenuRef as React.RefObject<HTMLDivElement>}
                                        data-export-menu="true"
                                        className="fixed w-72 bg-white/98 backdrop-blur-xl border border-slate-200/90 rounded-lg shadow-2xl p-2 z-[100] animate-in fade-in-50 zoom-in-95 duration-150 ring-1 ring-slate-950/5 text-left select-none max-h-[85vh] overflow-y-auto"
                                        style={{
                                          top: menuCoords.openUpwards ? undefined : `${menuCoords.top}px`,
                                          bottom: menuCoords.openUpwards ? `${window.innerHeight - menuCoords.top}px` : undefined,
                                          right: `${menuCoords.right}px`,
                                        }}
                                        role="menu"
                                      >
                                        {/* Header info */}
                                        <div className="px-2.5 py-1.5 mb-1 border-b border-slate-100 flex items-center justify-between text-[10px] text-slate-400 font-bold uppercase tracking-wider">
                                          <div className="flex items-center gap-1.5">
                                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                            <span>Export Format</span>
                                          </div>
                                          <span className="font-mono text-[9px] text-slate-500 max-w-[120px] truncate" title={job.filename}>
                                            {job.filename}
                                          </span>
                                        </div>

                                        {/* Section 1: Documents */}
                                        <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                          Documents
                                        </div>
                                        <div className="space-y-0.5">
                                          {/* Executive PDF */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/pdf`}
                                            download={`${fileStem}_transcript.pdf`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-rose-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-rose-50 border border-rose-100 text-rose-600 group-hover/item:scale-105 group-hover/item:bg-rose-100/70 transition-all shrink-0">
                                                <FileText className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">Executive PDF</span>
                                                <span className="text-[10px] text-slate-400 truncate">Formatted report with colors</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-rose-100/90 text-rose-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              PDF
                                            </span>
                                          </a>

                                          {/* Word Document */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/docx`}
                                            download={`${fileStem}_transcript.docx`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-blue-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-blue-50 border border-blue-100 text-blue-600 group-hover/item:scale-105 group-hover/item:bg-blue-100/70 transition-all shrink-0">
                                                <FileText className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">Word Document</span>
                                                <span className="text-[10px] text-slate-400 truncate">Editable rich text (.docx)</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-blue-100/90 text-blue-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              DOCX
                                            </span>
                                          </a>

                                          {/* Plain Text Transcript */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/txt`}
                                            download={`${fileStem}_transcript.txt`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-slate-100/70 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-slate-100 border border-slate-200 text-slate-700 group-hover/item:scale-105 group-hover/item:bg-slate-200/70 transition-all shrink-0">
                                                <FileText className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">Plain Transcript</span>
                                                <span className="text-[10px] text-slate-400 truncate">Clean timestamped text</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              TXT
                                            </span>
                                          </a>
                                        </div>

                                        {/* Separator */}
                                        <div className="border-t border-slate-100 my-1.5 mx-1" />

                                        {/* Section 2: Captions & Data */}
                                        <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                          Captions &amp; Data
                                        </div>
                                        <div className="space-y-0.5">
                                          {/* SubRip Subtitles */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/srt`}
                                            download={`${fileStem}_transcript.srt`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-amber-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-amber-50 border border-amber-100 text-amber-600 group-hover/item:scale-105 group-hover/item:bg-amber-100/70 transition-all shrink-0">
                                                <Film className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">SubRip Subtitles</span>
                                                <span className="text-[10px] text-slate-400 truncate">Premiere &amp; YouTube captions</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-amber-100/90 text-amber-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              SRT
                                            </span>
                                          </a>

                                          {/* WebVTT Captions */}
                                          {/* WebVTT Captions */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/vtt`}
                                            download={`${fileStem}_transcript.vtt`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-cyan-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-cyan-50 border border-cyan-100 text-cyan-600 group-hover/item:scale-105 group-hover/item:bg-cyan-100/70 transition-all shrink-0">
                                                <FileText className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">WebVTT Captions</span>
                                                <span className="text-[10px] text-slate-400 truncate">HTML5 web video subtitles</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-cyan-100/90 text-cyan-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              VTT
                                            </span>
                                          </a>

                                          {/* Tabular CSV */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/csv`}
                                            download={`${fileStem}_transcript.csv`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-emerald-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-emerald-50 border border-emerald-100 text-emerald-600 group-hover/item:scale-105 group-hover/item:bg-emerald-100/70 transition-all shrink-0">
                                                <FileSpreadsheet className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">Spreadsheet (CSV)</span>
                                                <span className="text-[10px] text-slate-400 truncate">Table for Excel &amp; Sheets</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-emerald-100/90 text-emerald-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              CSV
                                            </span>
                                          </a>
                                        </div>

                                        {/* Separator */}
                                        <div className="border-t border-slate-100 my-1.5 mx-1" />

                                        {/* Section 3: Audio Media */}
                                        <div className="px-2.5 py-1 text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                                          Audio Media
                                        </div>
                                        <div className="space-y-0.5">
                                          {/* MP3 Audio Export */}
                                          <a
                                            href={`${API_BASE}/jobs/${job.id}/export/mp3`}
                                            download={`${fileStem}.mp3`}
                                            onClick={closeMenu}
                                            className="flex items-center justify-between p-1.5 rounded-lg hover:bg-sky-50/60 active:scale-[0.99] transition-all group/item cursor-pointer"
                                          >
                                            <div className="flex items-center gap-2 min-w-0">
                                              <span className="p-1.5 rounded-lg bg-sky-50 border border-sky-100 text-sky-600 group-hover/item:scale-105 group-hover/item:bg-sky-100/70 transition-all shrink-0">
                                                <FileAudio className="w-3.5 h-3.5" />
                                              </span>
                                              <div className="flex flex-col text-left min-w-0">
                                                <span className="text-slate-900 font-semibold text-xs leading-snug">MP3 Audio</span>
                                                <span className="text-[10px] text-slate-400 truncate">192kbps extracted audio</span>
                                              </div>
                                            </div>
                                            <span className="text-[9px] bg-sky-100/90 text-sky-800 px-1.5 py-0.5 rounded-lg font-mono font-bold shrink-0 ml-1.5">
                                              MP3
                                            </span>
                                          </a>
                                        </div>
                                      </div>
                                    </>
                                  );
                                })()}
                              </div>
                            </>
                          )}

                          {isFailed && (
                            <button
                              onClick={() => onRetry(job.id)}
                              title="Retry Job"
                              className="p-1.5 text-slate-600 hover:text-slate-900 border border-slate-200/90 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs cursor-pointer active:scale-95"
                            >
                              <RotateCw className="w-3.5 h-3.5" />
                            </button>
                          )}

                          <button
                            onClick={() => onDelete(job.id)}
                            title="Delete Job"
                            className="p-1.5 text-slate-400 hover:text-rose-600 border border-transparent hover:border-slate-200 rounded-lg hover:bg-slate-50 transition-colors cursor-pointer active:scale-95"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>

                    {/* Inline Expandable Drawer (Transcript Snippet Preview) */}
                    {isExpanded && job.snippet_text && (
                      <tr className="bg-slate-50/70 border-b border-slate-100">
                        <td colSpan={6} className="px-5 py-3">
                          <div className="bg-white border border-slate-200/90 rounded-lg p-3.5 text-xs shadow-2xs">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2 text-slate-500">
                                <FileText className="w-3.5 h-3.5 text-blue-600" />
                                <span className="font-semibold text-slate-900">Transcript Preview Snippet</span>
                                <span>•</span>
                                <span>{job.segment_count || 0} segments recorded</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => onCopySnippet(job.id, job.snippet_text || "")}
                                  className="flex items-center gap-1.5 text-[11px] text-slate-700 hover:text-slate-900 border border-slate-200/90 px-2.5 py-1 rounded-lg cursor-pointer hover:bg-slate-50 shadow-2xs transition-all active:scale-95"
                                >
                                  {copiedSnippetId === job.id ? (
                                    <>
                                      <Check className="w-3 h-3 text-emerald-600" />
                                      <span className="text-emerald-600 font-semibold">Copied!</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy className="w-3 h-3" />
                                      <span>Copy Text</span>
                                    </>
                                  )}
                                </button>
                                <Link
                                  href={`/studio?jobId=${job.id}`}
                                  className="text-[11px] text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1"
                                >
                                  <span>Open full transcript in Studio &rarr;</span>
                                </Link>
                              </div>
                            </div>
                            <p className="text-slate-700 italic leading-relaxed bg-slate-50/60 p-3 rounded-lg border border-slate-100">
                              &ldquo;{job.snippet_text}...&rdquo;
                            </p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
