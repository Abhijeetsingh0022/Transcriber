"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { QueueStats } from "./types";
import { apiPost, apiPostForm, apiDelete, searchTranscripts } from "./lib/api";
import { useJobs } from "./lib/hooks/useJobs";
import { useTelemetry } from "./lib/hooks/useTelemetry";
import { useModal } from "./lib/hooks/useModal";
import { DashboardNav } from "./components/DashboardNav";
import { TelemetryDeck } from "./components/TelemetryDeck";
import { IngestionSuite } from "./components/IngestionSuite";
import { QueueSection } from "./components/QueueSection";
import { BulkExportModal } from "./components/BulkExportModal";
import { ConfirmModal, AlertModal } from "./components/Modal";
import { PreferencesModal } from "./components/PreferencesModal";

export default function Dashboard() {
  // ── Data ─────────────────────────────────────────────────────
  const { jobs, setJobs, refetch: refetchJobs } = useJobs();
  const { telemetry } = useTelemetry();
  const { modal, confirm, alert, close: closeModal } = useModal();

  // ── Preferences / Engine Settings ─────────────────────────────
  const [showPreferencesModal, setShowPreferencesModal] = useState(false);
  const [preferencesInitialTab, setPreferencesInitialTab] = useState<"keys" | "models">("keys");

  // ── Upload / Ingestion state ──────────────────────────────────
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadTab, setUploadTab] = useState<"file" | "url" | "record">("file");
  const [urlInput, setUrlInput] = useState("");

  const [mode, setMode] = useState("whale");
  const [language, setLanguage] = useState("auto");
  const [task, setTask] = useState("transcribe");
  const [diarize, setDiarize] = useState(true);
  const [numSpeakers, setNumSpeakers] = useState<number | "">("");
  const [restoreAudio, setRestoreAudio] = useState(false);
  const [initialPrompt, setInitialPrompt] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // ── Queue UI state ────────────────────────────────────────────
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [ftsMatchedJobIds, setFtsMatchedJobIds] = useState<Set<string>>(new Set());
  const [selectedJobIds, setSelectedJobIds] = useState<string[]>([]);
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [activeExportMenu, setActiveExportMenu] = useState<string | null>(null);
  const [copiedSnippetId, setCopiedSnippetId] = useState<string | null>(null);
  const [isBulkExporting, setIsBulkExporting] = useState(false);
  const [showBulkExportModal, setShowBulkExportModal] = useState(false);
  const [bulkExportFormats, setBulkExportFormats] = useState<string[]>(["pdf", "docx", "srt", "txt"]);

  // Debounced Full-Text Search via SQLite FTS5 for deep transcript matching
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (!trimmed || trimmed.length < 2) {
      setFtsMatchedJobIds(new Set());
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await searchTranscripts(trimmed, undefined, 50);
        if (res?.results) {
          const ids = new Set(res.results.map((r) => r.job_id));
          setFtsMatchedJobIds(ids);
        }
      } catch {
        // Fall back gracefully to local text filtering
      }
    }, 200);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  // ── Recording ─────────────────────────────────────────────────
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Close export menu on outside click / Escape
  useEffect(() => {
    const onClickOut = (e: MouseEvent) => {
      if (!(e.target as HTMLElement)?.closest("[data-export-menu]")) {
        setActiveExportMenu(null);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setActiveExportMenu(null);
    };
    document.addEventListener("mousedown", onClickOut);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onClickOut);
      document.removeEventListener("keydown", onKeyDown);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.stop();
        } catch {}
      }
    };
  }, []);

  // ── Upload handlers ───────────────────────────────────────────
  const ingestionParams = useCallback(
    () => ({
      mode,
      language,
      task,
      diarize: diarize ? "true" : "false",
      ...(numSpeakers !== "" && { num_speakers: String(numSpeakers) }),
      restore_audio: restoreAudio ? "true" : "false",
      ...(initialPrompt && { initial_prompt: initialPrompt }),
    }),
    [mode, language, task, diarize, numSpeakers, restoreAudio, initialPrompt]
  );

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files?.length) return;
      setIsUploading(true);
      const form = new FormData();
      Array.from(files).forEach((f) => form.append("files", f));
      Object.entries(ingestionParams()).forEach(([k, v]) => form.append(k, v));
      try {
        await apiPostForm("/jobs/upload", form);
        await refetchJobs();
      } catch {
        alert("Upload Failed", "Could not upload files to the backend. Check your connection and try again.");
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [ingestionParams, refetchJobs, alert]
  );

  const handleUrlSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!urlInput.trim()) return;
      setIsUploading(true);
      try {
        await apiPost("/jobs/url", {
          url: urlInput.trim(),
          mode,
          language,
          task,
          diarize,
          num_speakers: numSpeakers === "" ? null : Number(numSpeakers),
          restore_audio: restoreAudio,
          initial_prompt: initialPrompt || null,
        });
        setUrlInput("");
        await refetchJobs();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        alert("URL Queue Failed", msg);
      } finally {
        setIsUploading(false);
      }
    },
    [urlInput, mode, language, task, diarize, numSpeakers, restoreAudio, initialPrompt, refetchJobs, alert]
  );

  // ── Recording ─────────────────────────────────────────────────
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data?.size > 0) audioChunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(11, 19);
        const file = new File([blob], `mic_${ts}.webm`, { type: "audio/webm" });
        const dt = new DataTransfer();
        dt.items.add(file);
        handleFiles(dt.files);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecording(true);
      setRecordingSeconds(0);
      recordTimerRef.current = setInterval(() => setRecordingSeconds((s) => s + 1), 1000);
    } catch {
      alert("Microphone Unavailable", "Permission denied or no audio input device detected.", "warning");
    }
  }, [handleFiles, alert]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (recordTimerRef.current) clearInterval(recordTimerRef.current);
    }
  }, [isRecording]);

  // ── Job actions ───────────────────────────────────────────────
  const handleRetry = useCallback(async (jobId: string) => {
    try {
      await apiPost(`/jobs/${jobId}/retry`, {});
      refetchJobs();
    } catch {}
  }, [refetchJobs]);

  const handleDelete = useCallback(
    (jobId: string) => {
      confirm("Delete Job", "This will permanently delete the job and all its transcripts.", async () => {
        closeModal();
        try {
          await apiDelete(`/jobs/${jobId}`);
          setJobs((p) => p.filter((j) => j.id !== jobId));
          setSelectedJobIds((p) => p.filter((id) => id !== jobId));
        } catch {}
      });
    },
    [confirm, closeModal, setJobs]
  );

  // ── Bulk ops ──────────────────────────────────────────────────
  const filteredJobs = useMemo(() => {
    const processing = ["preprocessing", "transcribing", "aligning", "diarizing"];
    return jobs.filter((job) => {
      if (statusFilter === "completed"  && job.status !== "completed") return false;
      if (statusFilter === "processing" && !processing.includes(job.status)) return false;
      if (statusFilter === "queued"     && job.status !== "queued") return false;
      if (statusFilter === "failed"     && job.status !== "failed") return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          ftsMatchedJobIds.has(job.id) ||
          job.filename.toLowerCase().includes(q) ||
          (job.snippet_text ?? "").toLowerCase().includes(q) ||
          (job.detected_language ?? "").toLowerCase().includes(q) ||
          job.mode.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [jobs, statusFilter, searchQuery, ftsMatchedJobIds]);

  const stats: QueueStats = useMemo(() => {
    const processing = ["preprocessing", "transcribing", "aligning", "diarizing"];
    return {
      total:      jobs.length,
      completed:  jobs.filter((j) => j.status === "completed").length,
      processing: jobs.filter((j) => processing.includes(j.status)).length,
      queued:     jobs.filter((j) => j.status === "queued").length,
      failed:     jobs.filter((j) => j.status === "failed").length,
      totalWords: jobs.reduce((a, j) => a + (j.word_count ?? 0), 0),
      totalSec:   jobs.reduce((a, j) => a + (j.duration_seconds ?? 0), 0),
    };
  }, [jobs]);

  const handleSelectAll = useCallback(() => {
    setSelectedJobIds((prev) =>
      prev.length === filteredJobs.length ? [] : filteredJobs.map((j) => j.id)
    );
  }, [filteredJobs]);

  const handleToggleSelect = useCallback(
    (id: string) => setSelectedJobIds((p) => p.includes(id) ? p.filter((x) => x !== id) : [...p, id]),
    []
  );

  const handleBulkDelete = useCallback(() => {
    if (!selectedJobIds.length) return;
    const count = selectedJobIds.length;
    confirm(
      `Delete ${count} Job${count > 1 ? "s" : ""}`,
      `This will permanently delete ${count} selected job${count > 1 ? "s" : ""} and all associated assets.`,
      async () => {
        closeModal();
        try {
          await apiPost("/jobs/delete/bulk", { job_ids: selectedJobIds });
        } catch {
          await Promise.all(selectedJobIds.map((id) => apiDelete(`/jobs/${id}`)));
        }
        setJobs((p) => p.filter((j) => !selectedJobIds.includes(j.id)));
        setSelectedJobIds([]);
      }
    );
  }, [selectedJobIds, confirm, closeModal, setJobs]);

  const handleClearCompleted = useCallback(() => {
    const ids = jobs.filter((j) => j.status === "completed").map((j) => j.id);
    if (!ids.length) return;
    confirm(
      `Clear ${ids.length} Completed Job${ids.length > 1 ? "s" : ""}`,
      "All completed jobs and their transcripts will be removed.",
      async () => {
        closeModal();
        try {
          await apiPost("/jobs/delete/bulk", { job_ids: ids });
          setJobs((p) => p.filter((j) => !ids.includes(j.id)));
          setSelectedJobIds((p) => p.filter((id) => !ids.includes(id)));
        } catch {}
      },
      "warning"
    );
  }, [jobs, confirm, closeModal, setJobs]);

  const handleExecuteBulkExport = useCallback(async () => {
    if (!selectedJobIds.length) return;
    setIsBulkExporting(true);
    try {
      const res = await fetch(`${(await import("./lib/api")).API_BASE}/jobs/export/bulk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_ids: selectedJobIds, formats: bulkExportFormats }),
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: `transcripts_${new Date().toISOString().slice(0, 10)}.zip` });
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setShowBulkExportModal(false);
    } catch {
      alert("Export Failed", "Could not generate the bulk export package. Please try again.");
    } finally {
      setIsBulkExporting(false);
    }
  }, [selectedJobIds, bulkExportFormats, alert]);

  const copySnippet = useCallback((id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippetId(id);
    setTimeout(() => setCopiedSnippetId(null), 2000);
  }, []);

  // ── Render ────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-gray-50 text-slate-900 selection:bg-blue-100 selection:text-blue-900">
      <DashboardNav
        telemetry={telemetry}
        totalJobsCount={stats.total}
        onOpenSettings={() => {
          setPreferencesInitialTab("keys");
          setShowPreferencesModal(true);
        }}
      />

      <main className="flex-1 max-w-[1720px] w-full mx-auto px-4 sm:px-6 lg:px-8 pt-5 pb-12">
        <TelemetryDeck stats={stats} telemetry={telemetry} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-7 items-start">
          <div className="lg:col-span-5 flex flex-col gap-5">
            <IngestionSuite
              uploadTab={uploadTab}
              setUploadTab={setUploadTab}
              fileInputRef={fileInputRef}
              isUploading={isUploading}
              isDragOver={isDragOver}
              setIsDragOver={setIsDragOver}
              onFilesSelected={handleFiles}
              urlInput={urlInput}
              setUrlInput={setUrlInput}
              onUrlSubmit={handleUrlSubmit}
              isRecording={isRecording}
              recordingSeconds={recordingSeconds}
              onStartRecording={startRecording}
              onStopRecording={stopRecording}
              mode={mode}
              setMode={setMode}
              language={language}
              setLanguage={setLanguage}
              task={task}
              setTask={setTask}
              diarize={diarize}
              setDiarize={setDiarize}
              numSpeakers={numSpeakers}
              setNumSpeakers={setNumSpeakers}
              restoreAudio={restoreAudio}
              setRestoreAudio={setRestoreAudio}
              initialPrompt={initialPrompt}
              setInitialPrompt={setInitialPrompt}
              showAdvanced={showAdvanced}
              setShowAdvanced={setShowAdvanced}
              onOpenModelManager={() => {
                setPreferencesInitialTab("models");
                setShowPreferencesModal(true);
              }}
            />
          </div>

          <div className="lg:col-span-7 flex flex-col gap-5">
            <QueueSection
              filteredJobs={filteredJobs}
              allJobsCount={jobs.length}
              stats={stats}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              selectedJobIds={selectedJobIds}
              onSelectAll={handleSelectAll}
              onToggleSelect={handleToggleSelect}
              onClearCompleted={handleClearCompleted}
              onRefresh={refetchJobs}
              onOpenBulkExport={() => setShowBulkExportModal(true)}
              onBulkDelete={handleBulkDelete}
              expandedJobId={expandedJobId}
              setExpandedJobId={setExpandedJobId}
              activeExportMenu={activeExportMenu}
              setActiveExportMenu={setActiveExportMenu}
              exportMenuRef={exportMenuRef}
              copiedSnippetId={copiedSnippetId}
              onCopySnippet={copySnippet}
              onRetry={handleRetry}
              onDelete={handleDelete}
            />
          </div>
        </div>
      </main>

      <BulkExportModal
        isOpen={showBulkExportModal}
        onClose={() => setShowBulkExportModal(false)}
        selectedCount={selectedJobIds.length}
        bulkExportFormats={bulkExportFormats}
        setBulkExportFormats={setBulkExportFormats}
        isBulkExporting={isBulkExporting}
        onExecuteBulkExport={handleExecuteBulkExport}
      />

      {modal?.type === "confirm" && (
        <ConfirmModal
          open
          title={modal.title}
          message={modal.message}
          variant={modal.variant}
          onConfirm={modal.onConfirm}
          onCancel={closeModal}
        />
      )}
      {modal?.type === "alert" && (
        <AlertModal
          open
          title={modal.title}
          message={modal.message}
          variant={modal.variant}
          onClose={closeModal}
        />
      )}

      <PreferencesModal
        isOpen={showPreferencesModal}
        onClose={() => setShowPreferencesModal(false)}
        initialTab={preferencesInitialTab}
      />
    </div>
  );
}
