"use client";

import React, { useState, useEffect, useMemo } from "react";
import {
  Sparkles,
  Play,
  Pause,
  Download,
  Copy,
  Check,
  RefreshCw,
  Clock,
  ListTodo,
  BookOpen,
  HelpCircle,
  TrendingUp,
  FileText,
  User,
  CheckCircle2,
  ExternalLink,
  ChevronRight,
  Filter,
  Layers,
} from "lucide-react";
import {
  ExecutiveIntelligence,
  ActionItem,
  ShowNoteChapter,
} from "../../../types";
import { Speaker, SpeakerStat } from "../types";
import {
  fetchJobIntelligence,
  generateJobIntelligence,
  exportJobIntelligence,
} from "../../../lib/api";
import { formatTime } from "../utils";
import { CustomCheckbox } from "./CustomCheckbox";

interface ExecutiveIntelligenceViewProps {
  jobId: string;
  filename?: string;
  duration: number;
  currentTime: number;
  isPlaying: boolean;
  onSeekTo: (time: number) => void;
  onTogglePlay: () => void;
  speakers?: Speaker[];
  speakerStats?: SpeakerStat[];
  wordCount?: number;
  detectedLanguage?: string;
}

type TabFilter = "all" | "summary" | "chapters" | "actions" | "qa";

export function ExecutiveIntelligenceView({
  jobId,
  filename,
  duration,
  currentTime,
  isPlaying,
  onSeekTo,
  onTogglePlay,
  speakers = [],
  speakerStats = [],
  wordCount = 0,
  detectedLanguage = "en",
}: ExecutiveIntelligenceViewProps) {
  const [intelligence, setIntelligence] = useState<ExecutiveIntelligence | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedReport, setCopiedReport] = useState<boolean>(false);
  const [copiedTldr, setCopiedTldr] = useState<boolean>(false);
  const [copiedChapters, setCopiedChapters] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<TabFilter>("all");
  const [actionFilter, setActionFilter] = useState<"all" | "pending" | "done">("all");
  const [completedActions, setCompletedActions] = useState<Record<number, boolean>>({});

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);

    fetchJobIntelligence(jobId)
      .then((data) => {
        if (isMounted) {
          setIntelligence(data);
          setIsLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err?.message || "Failed to load intelligence report.");
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [jobId]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    setError(null);
    try {
      const fresh = await generateJobIntelligence(jobId);
      setIntelligence(fresh);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Failed to regenerate intelligence report.");
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleCopyReport = async () => {
    try {
      const res = await exportJobIntelligence(jobId, "markdown");
      await navigator.clipboard.writeText(res.content);
      setCopiedReport(true);
      setTimeout(() => setCopiedReport(false), 2500);
    } catch {
      if (intelligence) {
        const text = `# Executive Briefing\n${intelligence.tldr}\n\n${intelligence.executive_summary}`;
        await navigator.clipboard.writeText(text);
        setCopiedReport(true);
        setTimeout(() => setCopiedReport(false), 2500);
      }
    }
  };

  const handleCopyTldr = async () => {
    if (!intelligence?.tldr) return;
    await navigator.clipboard.writeText(intelligence.tldr);
    setCopiedTldr(true);
    setTimeout(() => setCopiedTldr(false), 2000);
  };

  const handleCopyChaptersFormatted = async () => {
    if (!intelligence?.chapters?.length) return;
    const formatted = intelligence.chapters
      .map((ch) => `${ch.start_timestamp} ${ch.title}`)
      .join("\n");
    await navigator.clipboard.writeText(formatted);
    setCopiedChapters(true);
    setTimeout(() => setCopiedChapters(false), 2000);
  };

  const handleDownloadMarkdown = async () => {
    try {
      const res = await exportJobIntelligence(jobId, "markdown");
      const blob = new Blob([res.content], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${filename ? filename.replace(/\.[^/.]+$/, "") : "session"}_briefing.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // Ignored
    }
  };

  const toggleActionItem = (idx: number) => {
    setCompletedActions((prev) => ({
      ...prev,
      [idx]: !prev[idx],
    }));
  };

  // Find currently active chapter based on playhead
  const currentChapterIndex = useMemo(() => {
    if (!intelligence?.chapters?.length) return -1;
    const chs = intelligence.chapters;
    for (let i = chs.length - 1; i >= 0; i--) {
      if (currentTime >= chs[i].start_time) {
        return i;
      }
    }
    return 0;
  }, [intelligence?.chapters, currentTime]);

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200/80 p-12 text-center shadow-2xs space-y-3">
        <div className="inline-flex p-2.5 rounded-lg bg-blue-50 text-blue-600 ring-4 ring-blue-50/50">
          <Sparkles className="w-5 h-5 animate-spin" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-slate-900">Synthesizing Executive Intelligence</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto leading-relaxed">
            Distilling discourse, evaluating speaker roles, mapping key milestones, and constructing timestamped chapters...
          </p>
        </div>
      </div>
    );
  }

  if (error || !intelligence) {
    return (
      <div className="bg-white rounded-lg border border-rose-200/80 p-8 text-center shadow-2xs max-w-md mx-auto space-y-3">
        <div className="w-8 h-8 rounded-full bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
          <HelpCircle className="w-4 h-4" />
        </div>
        <div>
          <h3 className="text-xs font-bold text-slate-900">Unable to Load Intelligence Report</h3>
          <p className="text-xs text-rose-600 mt-0.5">{error || "No report data found."}</p>
        </div>
        <button
          onClick={handleRefresh}
          className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-xs font-semibold cursor-pointer shadow-2xs inline-flex items-center gap-1.5 transition-all"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Generate Briefing</span>
        </button>
      </div>
    );
  }

  const {
    tldr,
    executive_summary,
    key_takeaways = [],
    action_items = [],
    chapters = [],
    key_questions = [],
    sentiment_and_tone,
    generated_by,
  } = intelligence;

  // Filtered action items
  const filteredActionItems = action_items.filter((_, idx) => {
    const isDone = !!completedActions[idx];
    if (actionFilter === "pending") return !isDone;
    if (actionFilter === "done") return isDone;
    return true;
  });

  const pendingActionsCount = action_items.filter((_, idx) => !completedActions[idx]).length;
  const completedActionsCount = action_items.length - pendingActionsCount;

  // Speaker name map for speaker coloring
  const speakerColorMap = new Map<string, string>();
  speakers.forEach((s) => {
    speakerColorMap.set(s.display_name.toLowerCase(), s.color_hex);
    speakerColorMap.set(s.speaker_label.toLowerCase(), s.color_hex);
  });

  const estimatedWpm = duration > 0 ? Math.round((wordCount / duration) * 60) : 180;

  return (
    <div className="space-y-4">
      {/* =========================================================================
          STAGE SUB-HEADER BAR (UNIFIED WITH SCRIPT & TOPICS MODES)
          ========================================================================= */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200/80 bg-white/60 p-3 rounded-lg border border-slate-200/60 backdrop-blur-xs">
        <div className="flex items-center gap-2 flex-wrap text-xs text-slate-600">
          <span className="font-semibold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200 font-mono text-[11px] inline-flex items-center gap-1.5">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Executive Briefing
          </span>

          {sentiment_and_tone && (
            <>
              <span>&bull;</span>
              <span className="text-slate-700 font-medium">{sentiment_and_tone}</span>
            </>
          )}

          <span>&bull;</span>
          <span className="font-mono text-slate-500">{chapters.length} chapters</span>

          <span>&bull;</span>
          <span className="font-mono text-slate-500">{action_items.length} deliverables</span>

          {generated_by && (
            <>
              <span>&bull;</span>
              <span className="text-[10px] font-mono text-slate-400">via {generated_by}</span>
            </>
          )}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer active:scale-95 disabled:opacity-50"
            title="Regenerate with active AI key"
          >
            <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin text-amber-600" : "text-slate-400"}`} />
            <span>{isRefreshing ? "Synthesizing..." : "Regenerate"}</span>
          </button>

          <button
            onClick={handleCopyReport}
            className="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer active:scale-95"
            title="Copy markdown report to clipboard"
          >
            {copiedReport ? (
              <Check className="w-3 h-3 text-emerald-600" />
            ) : (
              <Copy className="w-3 h-3 text-slate-400" />
            )}
            <span>{copiedReport ? "Copied!" : "Copy Report"}</span>
          </button>

          <button
            onClick={handleDownloadMarkdown}
            className="px-2.5 py-1 rounded-md bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-all cursor-pointer active:scale-95"
            title="Download formatted markdown briefing"
          >
            <Download className="w-3 h-3 text-slate-300" />
            <span>Export .md</span>
          </button>
        </div>
      </div>

      {/* =========================================================================
          FILTER TAB NAVIGATION (UNIFIED WITH STUDIO INSPECTOR & HEADER PILLS)
          ========================================================================= */}
      <div className="flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
        <div className="flex items-center gap-0.5 bg-slate-100/80 p-0.5 rounded-lg border border-slate-200/70">
          {[
            { id: "all" as const, label: "All Briefing" },
            { id: "summary" as const, label: "Executive Summary" },
            { id: "chapters" as const, label: `Chapters (${chapters.length})` },
            { id: "actions" as const, label: `Deliverables (${action_items.length})` },
            ...(key_questions.length ? [{ id: "qa" as const, label: `Q&A (${key_questions.length})` }] : []),
          ].map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1 rounded-md text-xs transition-all cursor-pointer whitespace-nowrap ${
                  isActive
                    ? "bg-white text-slate-900 shadow-2xs font-bold"
                    : "text-slate-600 hover:text-slate-900 font-medium"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="text-[11px] font-mono text-slate-400 hidden sm:block">
          {wordCount.toLocaleString()} words &bull; ~{estimatedWpm} WPM
        </div>
      </div>

      {/* =========================================================================
          TWO-COLUMN WORKSPACE: LEFT STAGE (SUMMARY) & RIGHT RAIL (ACTIONS & CHAPTERS)
          ========================================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* ── LEFT STAGE (EXECUTIVE SUMMARY & STRATEGIC TAKEAWAYS) ── */}
        <div
          className={`${
            activeTab === "chapters" || activeTab === "actions"
              ? "hidden"
              : activeTab === "summary"
              ? "lg:col-span-12"
              : "lg:col-span-7 xl:col-span-8"
          } space-y-4`}
        >
          {/* Executive Narrative Summary Card */}
          {(activeTab === "all" || activeTab === "summary") && (
            <div className="bg-white rounded-lg border border-slate-200/80 p-4 sm:p-5 shadow-2xs space-y-4">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-slate-100 text-slate-700">
                    <BookOpen className="w-3.5 h-3.5" />
                  </div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Executive Narrative Summary
                  </h2>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  ~{Math.max(1, Math.round(executive_summary.split(/\s+/).length / 180))} min read
                </span>
              </div>

              {/* TL;DR Highlight Inset Callout */}
              {tldr && (
                <div className="p-3.5 rounded-lg bg-amber-50/50 border border-amber-200/70 space-y-1 relative">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-amber-900 text-[10px] font-bold uppercase tracking-wider font-mono">
                      <Sparkles className="w-3 h-3 text-amber-600" />
                      <span>Executive TL;DR</span>
                    </div>

                    <button
                      onClick={handleCopyTldr}
                      className="p-1 rounded text-slate-400 hover:text-amber-800 hover:bg-amber-100/50 transition-colors cursor-pointer"
                      title="Copy TL;DR"
                    >
                      {copiedTldr ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    </button>
                  </div>
                  <p className="text-xs sm:text-sm font-semibold text-slate-900 leading-relaxed">
                    &ldquo;{tldr}&rdquo;
                  </p>
                </div>
              )}

              {/* Formatted Paragraphs */}
              <div className="text-xs sm:text-sm text-slate-700 leading-relaxed space-y-3">
                {executive_summary.split("\n\n").map((para, idx) => (
                  <p key={idx} className="leading-relaxed">
                    {para}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Strategic Takeaways Card */}
          {(activeTab === "all" || activeTab === "summary") && key_takeaways.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200/80 p-4 sm:p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-slate-100 text-slate-700">
                    <TrendingUp className="w-3.5 h-3.5" />
                  </div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Key Strategic Takeaways
                  </h2>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  {key_takeaways.length} points
                </span>
              </div>

              <div className="space-y-2">
                {key_takeaways.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-slate-50/60 border border-slate-200/70 hover:bg-slate-50 transition-colors flex items-start gap-2.5"
                  >
                    <span className="flex items-center justify-center w-5 h-5 rounded-md bg-white border border-slate-200 text-slate-700 font-bold text-[10px] font-mono shrink-0 shadow-2xs mt-0.5">
                      {idx + 1}
                    </span>
                    <p className="text-xs sm:text-sm text-slate-800 leading-relaxed font-medium">
                      {item}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Q&A Inquiries Card */}
          {(activeTab === "all" || activeTab === "qa") && key_questions.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200/80 p-4 sm:p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-slate-100 text-slate-700">
                    <HelpCircle className="w-3.5 h-3.5" />
                  </div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                    Discourse Inquiries &amp; Resolutions
                  </h2>
                </div>
                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  {key_questions.length} questions
                </span>
              </div>

              <div className="space-y-2.5">
                {key_questions.map((q, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-slate-50/60 border border-slate-200/70 space-y-1.5">
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <span className="text-xs font-bold text-slate-900">
                        Q: {q.question}
                      </span>
                      {q.timestamp && (
                        <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-600">
                          [{q.timestamp}]
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-700 leading-relaxed bg-white p-2.5 rounded-md border border-slate-200/60">
                      <strong className="text-slate-900 font-semibold">Resolution: </strong>
                      {q.answer}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ── RIGHT RAIL (ACTION DELIVERABLES & TIMELINE CHAPTERS) ── */}
        <div
          className={`${
            activeTab === "summary"
              ? "hidden"
              : activeTab === "chapters" || activeTab === "actions"
              ? "lg:col-span-12"
              : "lg:col-span-5 xl:col-span-4"
          } space-y-4`}
        >
          {/* Action Deliverables Matrix Rail */}
          {(activeTab === "all" || activeTab === "actions") && (
            <div className="bg-white rounded-lg border border-slate-200/80 p-4 sm:p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-slate-100 text-slate-700">
                    <ListTodo className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      Action Deliverables
                    </h2>
                    <p className="text-[10px] text-slate-400 font-mono">
                      {pendingActionsCount} pending &bull; {completedActionsCount} completed
                    </p>
                  </div>
                </div>

                {/* Filter pills */}
                <div className="flex items-center bg-slate-100 p-0.5 rounded-md text-[10px] font-semibold">
                  {(["all", "pending", "done"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setActionFilter(f)}
                      className={`px-2 py-0.5 rounded capitalize transition-all cursor-pointer ${
                        actionFilter === f ? "bg-white text-slate-900 shadow-2xs font-bold" : "text-slate-500"
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>

              {filteredActionItems.length === 0 ? (
                <div className="text-center py-5 text-slate-400 text-xs">
                  <CheckCircle2 className="w-5 h-5 mx-auto mb-1 text-slate-300" />
                  <span>No {actionFilter !== "all" ? actionFilter : ""} deliverables.</span>
                </div>
              ) : (
                <div className="space-y-2">
                  {action_items.map((act: ActionItem, idx: number) => {
                    const isDone = !!completedActions[idx];
                    if (actionFilter === "pending" && isDone) return null;
                    if (actionFilter === "done" && !isDone) return null;

                    const prio = (act.priority || "medium").toLowerCase();
                    const prioBadge =
                      prio === "high"
                        ? "bg-rose-50 text-rose-700 border-rose-200"
                        : prio === "low"
                        ? "bg-slate-50 text-slate-600 border-slate-200"
                        : "bg-amber-50 text-amber-700 border-amber-200";

                    const assigneeColor =
                      speakerColorMap.get(act.assignee?.toLowerCase() || "") || "#2563eb";

                    return (
                      <div
                        key={idx}
                        className={`p-2.5 rounded-lg border transition-all ${
                          isDone
                            ? "bg-slate-50/40 border-slate-200/60 opacity-60"
                            : "bg-slate-50/70 border-slate-200/80 hover:bg-slate-100/60"
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          <div className="pt-0.5">
                            <CustomCheckbox
                              checked={isDone}
                              onChange={() => toggleActionItem(idx)}
                              size="sm"
                              ariaLabel={`Mark deliverable ${idx + 1} as done`}
                            />
                          </div>

                          <div className="min-w-0 flex-1 space-y-1">
                            <p
                              className={`text-xs font-semibold text-slate-900 leading-snug ${
                                isDone ? "line-through text-slate-400" : ""
                              }`}
                            >
                              {act.task}
                            </p>

                            <div className="flex items-center justify-between gap-1.5 flex-wrap">
                              <div className="flex items-center gap-1.5">
                                <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase border ${prioBadge}`}>
                                  {prio}
                                </span>

                                <span className="inline-flex items-center gap-1 text-[10px] font-medium text-slate-600">
                                  <span
                                    className="w-1.5 h-1.5 rounded-full"
                                    style={{ backgroundColor: assigneeColor }}
                                  />
                                  <span>{act.assignee || "Participant"}</span>
                                </span>
                              </div>

                              {act.time_seconds !== undefined && (
                                <button
                                  onClick={() => onSeekTo(act.time_seconds)}
                                  className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-white hover:bg-blue-50 hover:text-blue-600 text-slate-600 text-[10px] font-mono font-semibold border border-slate-200 transition-colors cursor-pointer shadow-2xs"
                                  title={`Seek audio to ${act.timestamp}`}
                                >
                                  <Clock className="w-2.5 h-2.5" />
                                  <span>{act.timestamp}</span>
                                </button>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Timeline Show Notes & Chapters Rail */}
          {(activeTab === "all" || activeTab === "chapters") && chapters.length > 0 && (
            <div className="bg-white rounded-lg border border-slate-200/80 p-4 sm:p-5 shadow-2xs space-y-3">
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <div className="p-1 rounded-md bg-slate-100 text-slate-700">
                    <Clock className="w-3.5 h-3.5" />
                  </div>
                  <div>
                    <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      Show Notes &amp; Chapters
                    </h2>
                    <p className="text-[10px] text-slate-400 font-mono">{chapters.length} timed milestones</p>
                  </div>
                </div>

                <button
                  onClick={handleCopyChaptersFormatted}
                  className="px-2 py-0.5 rounded border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 text-[10px] font-semibold flex items-center gap-1 transition-all cursor-pointer shadow-2xs"
                  title="Copy formatted YouTube/Podcast timestamps"
                >
                  {copiedChapters ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedChapters ? "Copied" : "Copy All"}</span>
                </button>
              </div>

              {/* Scrubber Chapters List */}
              <div className="space-y-2">
                {chapters.map((ch: ShowNoteChapter, idx: number) => {
                  const isCurrent = idx === currentChapterIndex;
                  const nextChapterTime =
                    idx < chapters.length - 1 ? chapters[idx + 1].start_time : duration;
                  const chapterDurSec = Math.max(1, Math.round(nextChapterTime - ch.start_time));
                  const durLabel = chapterDurSec < 60 ? `${chapterDurSec}s` : `${Math.round(chapterDurSec / 60)}m`;

                  return (
                    <div
                      key={idx}
                      className={`p-2.5 rounded-lg border transition-all cursor-pointer ${
                        isCurrent
                          ? "border-blue-400 bg-blue-50/25 shadow-xs ring-1 ring-blue-500/15"
                          : "bg-slate-50/60 border-slate-200/80 hover:bg-slate-100/60 hover:border-slate-300"
                      }`}
                      onClick={() => onSeekTo(ch.start_time)}
                    >

                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-0.5 min-w-0 flex-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-mono text-[10px] text-slate-400 font-semibold tracking-tight">
                              #{String(idx + 1).padStart(2, "0")}
                            </span>
                            <span className="text-xs font-bold text-slate-900 truncate">
                              {ch.title}
                            </span>
                            {isCurrent && (
                              <span className="px-1 py-0.2 rounded text-[8px] font-bold uppercase bg-blue-600 text-white tracking-wider">
                                Playing
                              </span>
                            )}
                          </div>

                          {ch.description && (
                            <p className="text-[11px] text-slate-500 leading-normal line-clamp-2">
                              {ch.description}
                            </p>
                          )}
                        </div>

                        {/* Seek button */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            if (isCurrent && isPlaying) {
                              onTogglePlay();
                            } else {
                              onSeekTo(ch.start_time);
                              if (!isPlaying) onTogglePlay();
                            }
                          }}
                          className={`shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono font-semibold transition-all shadow-2xs cursor-pointer ${
                            isCurrent && isPlaying
                              ? "bg-blue-600 text-white"
                              : "bg-white hover:bg-blue-50 hover:text-blue-600 text-slate-700 border border-slate-200"
                          }`}
                          title={`Jump to ${ch.start_timestamp}`}
                        >
                          {isCurrent && isPlaying ? (
                            <Pause className="w-2.5 h-2.5" />
                          ) : (
                            <Play className="w-2.5 h-2.5 fill-current" />
                          )}
                          <span>{ch.start_timestamp}</span>
                          <span className="text-[9px] font-normal text-slate-400">({durLabel})</span>
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
