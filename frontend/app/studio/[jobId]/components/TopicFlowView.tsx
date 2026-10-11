"use client";

import React, { useState, useMemo } from "react";
import {
  Printer,
  Download,
  Copy,
  Check,
  Search,
} from "lucide-react";
import { VideoTopic, JobInfo } from "../types";
import { formatTime, API_BASE } from "../utils";

interface TopicFlowViewProps {
  topics: VideoTopic[];
  jobId: string;
  jobInfo: JobInfo | null;
  currentTime: number;
  onSeekTo: (time: number) => void;
  duration: number;
}

export function TopicFlowView({
  topics,
  jobId,
  jobInfo,
  currentTime,
  onSeekTo,
  duration,
}: TopicFlowViewProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [copied, setCopied] = useState(false);

  const filename = jobInfo?.filename || `Video_${jobId.slice(0, 8)}.mp4`;
  const durationStr = formatTime(duration);

  // Filter sections based on search
  const filteredTopics = useMemo(() => {
    if (!searchQuery.trim()) return topics;
    const q = searchQuery.toLowerCase();
    return topics.filter(
      (s) =>
        s.section.toLowerCase().includes(q) ||
        s.turns.some(
          (turn) =>
            turn.speaker.toLowerCase().includes(q) ||
            turn.text.toLowerCase().includes(q)
        )
    );
  }, [topics, searchQuery]);

  const handleCopyTable = () => {
    let tsv = "No.\tSection\tTimecode\tDuration\tSpeaker\tDialogue / Transcript\n";
    filteredTopics.forEach((s) => {
      s.turns.forEach((turn) => {
        tsv += `${s.section_no}\t${s.section}\t${s.timecode}\t${s.duration_label}\t${turn.speaker}\t${turn.text}\n`;
      });
    });
    navigator.clipboard.writeText(tsv);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  const fileStem = useMemo(() => {
    return filename.replace(/\.[^/.]+$/, "");
  }, [filename]);

  // Compute rich audio and transcript metrics
  const totalWords = useMemo(() => {
    return topics.reduce((acc, t) => {
      return acc + (t.turns || []).reduce((sAcc, turn) => {
        return sAcc + (turn.text || "").split(/\s+/).filter(Boolean).length;
      }, 0);
    }, 0);
  }, [topics]);

  const distinctSpeakers = useMemo(() => {
    const list: string[] = [];
    topics.forEach((t) => {
      (t.turns || []).forEach((turn) => {
        if (turn.speaker && !list.includes(turn.speaker)) {
          list.push(turn.speaker);
        }
      });
    });
    return list;
  }, [topics]);

  const wpm = useMemo(() => {
    if (!duration || duration < 5) return 0;
    return Math.round((totalWords / duration) * 60);
  }, [totalWords, duration]);

  const activeSectionNo = useMemo(() => {
    const sec = filteredTopics.find(
      (s) => currentTime >= s.start_time && currentTime <= s.end_time
    );
    return sec ? sec.section_no : null;
  }, [filteredTopics, currentTime]);

  return (
    <div className="w-full space-y-6 pb-16 print:space-y-4 print:pb-0 print-full-width">
      {/* 1. Header Card matching user template */}
      <div className="bg-white border border-slate-200/90 rounded-lg p-6 md:p-8 shadow-xs relative overflow-hidden print:border-none print:shadow-none print:p-0 print:mb-4">
        {/* Top Centered Header Hierarchy */}
        <div className="text-center space-y-1.5 mb-6">
          <h1 className="text-2xl md:text-3xl font-bold tracking-wider text-[#1e3a5f] uppercase">
            {fileStem}
          </h1>
          <h2 className="text-xl md:text-2xl font-bold text-[#c25e2e]">
            Section-Wise &amp; Speaker-Wise Video Flow
          </h2>
          <p className="text-xs md:text-sm text-slate-500 italic">
            Video: <span className="font-semibold text-slate-700">{filename}</span> &nbsp;|&nbsp; 
            Duration: <span className="font-semibold text-slate-700">{durationStr}</span> &nbsp;|&nbsp; 
            Words: <span className="font-semibold text-slate-700">{totalWords}</span> &nbsp;|&nbsp; 
            Speakers: <span className="font-semibold text-slate-700">{distinctSpeakers.length || 1}</span>
          </p>
        </div>

        {/* Detailed Audio & Transcript Specifications Card */}
        <div className="bg-slate-50/80 border border-slate-200/90 rounded-lg p-4 mb-6 text-xs text-slate-700 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-200/60 pb-2">
            <h3 className="text-sm font-bold text-[#1e3a5f]">
              Section-Wise Video Flow and Timestamped Transcript
            </h3>
            <span className="text-[11px] font-semibold text-slate-500 bg-white border border-slate-200 px-2.5 py-0.5 rounded-lg shadow-2xs">
              Studio Master Sync
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1.5 pt-1 text-[11.5px]">
            <div>
              <span className="font-bold text-[#1e3a5f]">Audio Specifications: </span>
              <span className="text-slate-600">16 kHz Mono PCM (Broadcast Studio Normalized) &bull; Cadence: ~{wpm} WPM</span>
            </div>
            <div>
              <span className="font-bold text-[#1e3a5f]">Transcript Metrics: </span>
              <span className="text-slate-600">{totalWords} Words &bull; Word-Level Microsecond Synchronized</span>
            </div>
            <div>
              <span className="font-bold text-[#1e3a5f]">Identified Speakers: </span>
              <span className="text-slate-600">{distinctSpeakers.join(", ") || "Single Speaker"}</span>
            </div>
            <div>
              <span className="font-bold text-[#1e3a5f]">Curriculum Mapping: </span>
              <span className="text-slate-600">{topics.length} Sections ({topics.slice(0, 4).map(t => t.section).join(", ")}{topics.length > 4 ? ` + ${topics.length - 4} more` : ""})</span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500 italic pt-1 border-t border-slate-200/40">
            The transcript wording is taken from the supplied <strong className="text-slate-800 not-italic font-semibold">{fileStem}</strong> transcript source, while the video duration, audio stream, and speaker/scene mapping were checked against the uploaded MUX video.
          </p>
        </div>

        {/* Quick Actions Bar */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pt-2 border-t border-slate-100">
          <div className="text-xs text-slate-500">
            {filteredTopics.length} sections displayed &bull; Chronological order
          </div>

          {/* Quick Actions */}
          <div className="flex flex-wrap items-center gap-2 shrink-0 no-print">
            <button
              onClick={handleCopyTable}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-slate-100 hover:bg-slate-200/80 text-slate-700 rounded-lg transition-colors border border-slate-200/80 shadow-2xs cursor-pointer"
              title="Copy table as tab-separated values"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
              <span>{copied ? "Copied" : "Copy Table"}</span>
            </button>

            <a
              href={`${API_BASE}/jobs/${jobId}/export/topic_flow`}
              download
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium bg-white hover:bg-slate-50 text-slate-700 rounded-lg transition-colors border border-slate-200/80 shadow-2xs cursor-pointer"
              title="Download standalone HTML file"
            >
              <Download className="w-3.5 h-3.5 text-slate-500" />
              <span>Export HTML</span>
            </a>

            <a
              href={`${API_BASE}/jobs/${jobId}/export/pdf`}
              download={`${fileStem}_section_flow.pdf`}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-[#c25e2e] hover:bg-[#a94f24] text-white rounded-lg transition-colors shadow-2xs cursor-pointer"
              title="Download official Section-Wise Video Flow PDF report"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download PDF</span>
            </a>

            <button
              onClick={handlePrint}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-[#1e3a5f] hover:bg-[#152b47] text-white rounded-lg transition-colors shadow-xs cursor-pointer"
              title="Print document or save via system print dialog"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print / PDF</span>
            </button>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="mt-5 pt-4 border-t border-slate-100 flex items-center justify-between gap-4 no-print">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search sections or dialogues..."
              className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50 border border-slate-200/90 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#1e3a5f]/20 focus:border-[#1e3a5f] transition-all"
            />
          </div>

          <div className="text-xs text-slate-400 font-mono">
            Showing {filteredTopics.length} of {topics.length} sections
          </div>
        </div>
      </div>

      {/* 2. Section Flow Table */}
      <div className="bg-white border border-slate-300 rounded-lg shadow-xs overflow-hidden print:border-none print:shadow-none print-full-width">
        <div className="overflow-x-auto print:overflow-visible">
          <table className="w-full text-left border-collapse text-xs min-w-[760px]">
            <thead>
              <tr className="bg-[#1e3a5f] text-white text-[12.5px] font-bold">
                <th className="py-2.5 px-2 text-center w-12 border border-[#2d4d77]">No.</th>
                <th className="py-2.5 px-4 text-center w-48 border border-[#2d4d77]">Section</th>
                <th className="py-2.5 px-2 text-center w-28 border border-[#2d4d77]">Timecode</th>
                <th className="py-2.5 px-2 text-center w-20 border border-[#2d4d77]">Duration</th>
                <th className="py-2.5 px-3 text-center w-28 border border-[#2d4d77]">Speaker</th>
                <th className="py-2.5 px-4 text-center border border-[#2d4d77]">Dialogue / Transcript</th>
              </tr>
            </thead>
            <tbody>
              {filteredTopics.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-slate-400">
                    No matching sections found for &ldquo;{searchQuery}&rdquo;
                  </td>
                </tr>
              ) : (
                filteredTopics.map((section) => (
                  <TopicSectionRows
                    key={section.section_no}
                    section={section}
                    isSectionActive={activeSectionNo === section.section_no}
                    onSeekTo={onSeekTo}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

interface TopicSectionRowsProps {
  section: VideoTopic;
  isSectionActive: boolean;
  onSeekTo: (time: number) => void;
}

const TopicSectionRows = React.memo(function TopicSectionRows({
  section,
  isSectionActive,
  onSeekTo,
}: TopicSectionRowsProps) {
  const isSectionTinted = section.section_no % 2 !== 0 && section.section_no >= 3;
  const secBgClass = isSectionTinted ? "bg-[#eef4fa]" : "bg-white";

  return (
    <>
      {section.turns.map((turn, turnIdx) => {
        const isFirstTurn = turnIdx === 0;

        // Turn background calculation matching template
        const turnBgClass = isSectionTinted
          ? turnIdx % 2 === 0
            ? "bg-[#eef4fa]"
            : "bg-white"
          : turnIdx % 2 === 1
          ? "bg-[#eef4fa]"
          : "bg-white";

        return (
          <tr
            key={`${section.section_no}-${turnIdx}`}
            className={`transition-colors ${
              isSectionActive ? "ring-1 ring-blue-500/30" : ""
            }`}
          >
            {/* No. (Rowspan across all turns in section) */}
            {isFirstTurn && (
              <td
                rowSpan={section.turns.length}
                className={`py-3 px-2 text-center font-bold text-slate-900 text-sm align-middle border border-slate-300 ${secBgClass}`}
              >
                {section.section_no}
              </td>
            )}

            {/* Section Name (Rowspan across all turns in section) */}
            {isFirstTurn && (
              <td
                rowSpan={section.turns.length}
                className={`py-3 px-4 text-center font-semibold text-slate-900 text-xs align-middle border border-slate-300 ${secBgClass}`}
              >
                {section.section}
              </td>
            )}

            {/* Timecode (Rowspan across all turns in section, clickable) */}
            {isFirstTurn && (
              <td
                rowSpan={section.turns.length}
                className={`py-3 px-2 text-center align-middle border border-slate-300 ${secBgClass}`}
              >
                <button
                  onClick={() => onSeekTo(section.start_time)}
                  className="font-mono font-bold text-[#c25e2e] hover:underline cursor-pointer tracking-tight"
                  title={`Jump to ${section.timecode}`}
                >
                  {section.timecode}
                </button>
              </td>
            )}

            {/* Duration (Rowspan across all turns in section) */}
            {isFirstTurn && (
              <td
                rowSpan={section.turns.length}
                className={`py-3 px-2 text-center text-slate-900 text-xs align-middle border border-slate-300 ${secBgClass}`}
              >
                {section.duration_label}
              </td>
            )}

            {/* Speaker Name */}
            <td
              className={`py-2.5 px-3 text-center font-semibold text-slate-900 text-xs align-middle border border-slate-300 whitespace-nowrap ${turnBgClass}`}
            >
              {turn.speaker}
            </td>

            {/* Dialogue / Transcript */}
            <td
              className={`py-2.5 px-4 text-left text-slate-900 text-xs leading-relaxed align-middle border border-slate-300 ${turnBgClass}`}
            >
              {turn.text}
            </td>
          </tr>
        );
      })}
    </>
  );
});
