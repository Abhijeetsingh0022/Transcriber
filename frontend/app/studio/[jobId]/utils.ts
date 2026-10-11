import {
  DialogueTurn,
  Segment,
  Speaker,
  SpeakerStat,
  Transcript,
  AudioAnalytics,
  TemplateStyle,
  TimestampStyle,
  SpeakerCase,
  FontSize,
} from "./types";

export { API_BASE } from "../../lib/api";

export const fontClassMap: Record<FontSize, string> = {
  sm: "text-[12px] leading-relaxed",
  base: "text-[14px] leading-relaxed",
  lg: "text-[16px] leading-relaxed",
  xl: "text-[18px] leading-relaxed",
};

// Time formatting helpers
export function formatTime(sec: number, precision: number = 1): string {
  if (isNaN(sec) || sec < 0) sec = 0;
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const frac = (sec % 1).toFixed(precision).slice(2);
  const mm = m < 10 ? `0${m}` : `${m}`;
  const ss = s < 10 ? `0${s}` : `${s}`;
  if (h > 0) {
    return `${h}:${mm}:${ss}.${frac}`;
  }
  return `${mm}:${ss}.${frac}`;
}

export function formatTimePrecise(sec: number, decimals: number = 3): string {
  return formatTime(sec, decimals);
}

export function formatAccurateTimestamp(
  start: number,
  end?: number,
  decimals: number = 3
): string {
  const startStr = formatTime(start, decimals);
  if (end !== undefined && end > start) {
    const endStr = formatTime(end, decimals);
    const durSec = end - start;
    const durStr = durSec < 1.0 ? `${Math.round(durSec * 1000)}ms` : `${durSec.toFixed(2)}s`;
    return `${startStr} – ${endStr} (${durStr})`;
  }
  return startStr;
}

export function formatTimeMinutesOnly(sec: number): string {
  if (isNaN(sec) || sec < 0) sec = 0;
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}`;
}

export function formatTimestampStr(start: number, end: number, style: TimestampStyle): string {
  if (style === "none") return "";
  if (style === "short") return `[${formatTimeMinutesOnly(start)}]`;
  if (style === "short_range") return `[${formatTimeMinutesOnly(start)} - ${formatTimeMinutesOnly(end)}]`;
  if (style === "single") {
    const h = Math.floor(start / 3600);
    const m = Math.floor((start % 3600) / 60);
    const s = Math.floor(start % 60);
    return `[${h > 0 ? `${h}:` : ""}${m < 10 ? "0" : ""}${m}:${s < 10 ? "0" : ""}${s}]`;
  }
  if (style === "ms") {
    return `[${formatTime(start)} - ${formatTime(end)}]`;
  }
  const h1 = Math.floor(start / 3600);
  const m1 = Math.floor((start % 3600) / 60);
  const s1 = Math.floor(start % 60);
  const t1 = `${h1 > 0 ? `${h1}:` : ""}${m1 < 10 ? "0" : ""}${m1}:${s1 < 10 ? "0" : ""}${s1}`;

  const h2 = Math.floor(end / 3600);
  const m2 = Math.floor((end % 3600) / 60);
  const s2 = Math.floor(end % 60);
  const t2 = `${h2 > 0 ? `${h2}:` : ""}${m2 < 10 ? "0" : ""}${m2}:${s2 < 10 ? "0" : ""}${s2}`;

  return `[${t1} - ${t2}]`;
}

export function formatSpeakerDisplayName(rawName?: string, speakerLabel?: string): string {
  const name = rawName?.trim();
  if (name && !/^SPEAKER_\d+$/i.test(name)) {
    return name;
  }
  const label = speakerLabel || name || "SPEAKER_00";
  const match = label.match(/SPEAKER_(\d+)/i);
  if (match) {
    const num = parseInt(match[1], 10) + 1;
    return `Speaker ${num}`;
  }
  return name || "Speaker 1";
}

// Aggregates raw segments into cohesive conversational dialogue turns
export function buildDialogueTurns(
  segments: Segment[] | undefined,
  speakers: Speaker[] | undefined,
  speakerNames: Record<string, string>,
  options?: { maxPause?: number; separateSteps?: boolean }
): DialogueTurn[] {
  if (!segments) return [];
  const turns: DialogueTurn[] = [];
  let current: DialogueTurn | null = null;
  const maxPause = options?.maxPause ?? 2.2;
  const separateSteps = options?.separateSteps ?? true;

  for (const seg of segments) {
    const spkLabel = seg.speaker_label || "SPEAKER_00";
    const spk = speakers?.find((s) => s.speaker_label === spkLabel);
    const rawDisplayName = speakerNames[spkLabel] || spk?.display_name || spkLabel;
    const displayName = formatSpeakerDisplayName(rawDisplayName, spkLabel);
    const colorHex = spk?.color_hex || "#2563eb";
    const text = (seg.text || "").trim();
    if (!text) continue;

    const sStart = typeof seg.start_time === "number" && !isNaN(seg.start_time) ? seg.start_time : 0;
    const sEnd = typeof seg.end_time === "number" && !isNaN(seg.end_time) ? Math.max(seg.end_time, sStart) : sStart + 0.1;

    // Detect explicit procedural step or topic boundary
    const isStepBoundary = separateSteps && /^(in step \d+|step \d+|now let'?s build)/i.test(text);

    // Should merge if same speaker, small pause, not a step boundary, and not exceeding 30s
    const shouldMerge =
      current &&
      current.speakerLabel === spkLabel &&
      sStart - current.endTime <= maxPause &&
      !isStepBoundary &&
      current.duration + (sEnd - sStart) < 32;

    if (shouldMerge && current) {
      current.endTime = sEnd;
      current.duration = Number((current.endTime - current.startTime).toFixed(2));
      current.text += " " + text;
      const wordsList = current.text.split(" ").filter(Boolean);
      current.wordCount = wordsList.length;
      const durMin = Math.max(current.duration / 60.0, 0.01);
      current.wpm = Math.round(current.wordCount / durMin);
      current.words = [...current.words, ...(seg.words || [])];
      current.segmentIds.push(seg.id);
      if (!current.addressedTo && seg.addressed_to) {
        current.addressedTo = seg.addressed_to;
      }
      if (!current.intent && seg.turn_intent) {
        current.intent = seg.turn_intent;
      }
      if (current.segments) current.segments.push(seg);
    } else {
      if (current) turns.push(current);
      const dur = Number(Math.max(0.01, sEnd - sStart).toFixed(2));
      const wordsList = text.split(" ").filter(Boolean);
      const durMin = Math.max(dur / 60.0, 0.01);
      current = {
        turnIndex: turns.length + 1,
        speakerLabel: spkLabel,
        displayName,
        colorHex,
        addressedTo: seg.addressed_to,
        intent: seg.turn_intent,
        startTime: sStart,
        endTime: sEnd,
        duration: dur,
        wordCount: wordsList.length,
        wpm: Math.round(wordsList.length / durMin),
        text,
        words: seg.words ? [...seg.words] : [],
        segmentIds: [seg.id],
        segments: [seg],
      };
    }
  }
  if (current) turns.push(current);
  return turns;
}

// Computes speaker talk time, turn distribution, and WPM pace
export function calculateSpeakerStats(
  speakers: Speaker[] | undefined,
  dialogueTurns: DialogueTurn[]
): SpeakerStat[] {
  if (!speakers || !dialogueTurns.length) return [];
  const totalDuration = dialogueTurns.reduce((acc, t) => acc + t.duration, 0) || 1;

  return speakers.map((spk) => {
    const spkTurns = dialogueTurns.filter((t) => t.speakerLabel === spk.speaker_label);
    const talkTime = spkTurns.reduce((acc, t) => acc + t.duration, 0);
    const wordCount = spkTurns.reduce((acc, t) => acc + t.wordCount, 0);
    const percentage = Math.round((talkTime / totalDuration) * 100);
    const durMin = Math.max(talkTime / 60.0, 0.01);
    const avgWpm = Math.round(wordCount / durMin);

    return {
      ...spk,
      talkTime: talkTime.toFixed(1),
      percentage,
      turnsCount: spkTurns.length,
      wordCount,
      avgWpm,
    };
  });
}

// Computes audio pacing and speech activity analytics
export function calculateAudioAnalytics(
  segments: Segment[] | undefined,
  effectiveDuration: number,
  dialogueTurns: DialogueTurn[]
): AudioAnalytics {
  if (!segments || effectiveDuration <= 0) {
    return { speechTime: "0.0", pauseTime: "0.0", speechPct: 0, pausePct: 0, avgTurnDuration: "0" };
  }
  const speechTime = segments.reduce((acc, s) => {
    const sStart = typeof s.start_time === "number" && !isNaN(s.start_time) ? s.start_time : 0;
    const sEnd = typeof s.end_time === "number" && !isNaN(s.end_time) ? Math.max(s.end_time, sStart) : sStart;
    return acc + Math.max(0, sEnd - sStart);
  }, 0);
  const pauseTime = Math.max(0, effectiveDuration - speechTime);
  const speechPct = Math.min(100, Math.round((speechTime / effectiveDuration) * 100));
  const pausePct = Math.max(0, 100 - speechPct);
  const avgTurnDuration = dialogueTurns.length > 0 ? (effectiveDuration / dialogueTurns.length).toFixed(1) : "0";

  return {
    speechTime: speechTime.toFixed(1),
    pauseTime: pauseTime.toFixed(1),
    speechPct,
    pausePct,
    avgTurnDuration,
  };
}

// Extracts prominent keywords excluding conversational stop words
export function extractTopKeywords(segments: Segment[] | undefined): { word: string; count: number }[] {
  if (!segments) return [];
  const stopWords = new Set([
    "the", "and", "a", "an", "is", "it", "in", "to", "of", "for", "with", "on", "at", "by", "this", "that", "i", "you", "he", "she", "we", "they", "was", "are", "be", "have", "has", "had", "do", "does", "did", "so", "but", "not", "what", "all", "were", "when", "there", "can", "if", "my", "your", "as", "or", "from", "just", "like", "about", "up", "out", "me", "him", "her", "us", "them", "then", "now", "see", "get", "go", "one", "no", "yes", "oh", "um", "uh", "okay", "yeah", "been", "would", "could", "should", "some", "which", "their", "more"
  ]);
  const wordCounts: Record<string, number> = {};
  for (const seg of segments) {
    const text = seg.text || "";
    const words = text.toLowerCase().replace(/[^a-z0-9\s]/g, "").split(/\s+/);
    for (const w of words) {
      if (w.length > 3 && !stopWords.has(w)) {
        wordCounts[w] = (wordCounts[w] || 0) + 1;
      }
    }
  }
  return Object.entries(wordCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([word, count]) => ({ word, count }));
}

// Generates formatted scripts across Broadcast, Screenplay, Legal, Podcast, and Dialogue templates
export function renderScriptTemplate({
  dialogueTurns,
  transcript,
  templateStyle,
  timestampStyle,
  speakerCase,
  includeStats,
  duration,
  jobId,
}: {
  dialogueTurns: DialogueTurn[];
  transcript: Transcript | null;
  templateStyle: TemplateStyle;
  timestampStyle: TimestampStyle;
  speakerCase: SpeakerCase;
  includeStats: boolean;
  duration: number;
  jobId: string;
}): string {
  if (!dialogueTurns.length) return "";
  const totalWords = transcript?.word_count || dialogueTurns.reduce((acc, t) => acc + t.wordCount, 0);
  const language = transcript?.detected_language?.toUpperCase() || "EN";
  const durationStr = formatTime(duration);
  const speakersList = transcript?.speakers?.map((s) => s.display_name).join(", ") || "Speaker 1";

  if (templateStyle === "screenplay") {
    const lines = [
      "=".repeat(70),
      `SCENE: TRANSCRIPT OF JOB ${jobId.slice(0, 8).toUpperCase()}`,
      `RECORDED DURATION: ${durationStr}  |  LANGUAGE: ${language}  |  TOTAL WORDS: ${totalWords}`,
      "=".repeat(70),
      "",
      "INT. RECORDING STUDIO - DAY",
      "",
      `Audio transcription log. A conversation between ${speakersList}.`,
      "",
    ];

    dialogueTurns.forEach((t) => {
      const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;
      const tc =
        timestampStyle === "none"
          ? ""
          : `(${formatTimeMinutesOnly(t.startTime)} - ${formatTimeMinutesOnly(t.endTime)}${
              includeStats ? `, ${t.duration.toFixed(1)}s` : ""
            })`;
      lines.push(`                              ${name}`);
      if (tc) lines.push(`                   ${tc}`);
      lines.push(`          ${t.text}`);
      lines.push("");
    });

    lines.push("                                                       FADE OUT.");
    return lines.join("\n");
  }

  if (templateStyle === "legal") {
    const lines = [
      "  " + "=".repeat(68),
      "  PROCEEDING: OFFICIAL RECORDING TRANSCRIPTION",
      `  MATTER:     JOB ${jobId.slice(0, 8).toUpperCase()}`,
      `  RECORDED:   ${durationStr} (${totalWords} WORDS, ${dialogueTurns.length} TURNS)`,
      `  LANGUAGE:   ${language}`,
      "  APPEARANCES:",
      ...((transcript?.speakers || []).map((s) => `    - ${s.display_name}`)),
      "  " + "=".repeat(68),
      "",
    ];

    let lineNo = 1;
    dialogueTurns.forEach((t) => {
      const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;
      const tcStr = timestampStyle === "none" ? "" : ` [${formatTime(t.startTime)}]`;
      lines.push(`  ${String(lineNo++).padStart(3, " ")}  ${tcStr}  ${name}:`);
      lines.push(`  ${String(lineNo++).padStart(3, " ")}       ${t.text}`);
      lines.push(`  ${String(lineNo++).padStart(3, " ")}`);
    });

    lines.push("");
    lines.push("  " + "-".repeat(68));
    lines.push("  CERTIFICATE OF TRANSCRIPTION:");
    lines.push("  I certify that the above transcription represents a faithful,");
    lines.push("  verbatim record of the recording designated herein.");
    lines.push("  " + "-".repeat(68));
    return lines.join("\n");
  }

  if (templateStyle === "podcast") {
    const lines = [
      `# Job ${jobId.slice(0, 8)} - Episode Show Notes & Timestamps`,
      `Duration: ${durationStr} | Language: ${language} | Words: ${totalWords}`,
      "",
      "## Episode Chapters & Key Moments",
      "",
    ];

    dialogueTurns.forEach((t) => {
      const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;
      const firstClause = t.text.split(".")[0].split("?")[0].slice(0, 50).trim();
      const tc = timestampStyle === "none" ? "" : `**${formatTimeMinutesOnly(t.startTime)}** - `;
      lines.push(`- ${tc}${name}: ${firstClause}...`);
    });

    lines.push("");
    lines.push("---");
    lines.push("");
    lines.push("## Complete Dialogue Transcript");
    lines.push("");

    dialogueTurns.forEach((t) => {
      const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;
      const tc = timestampStyle === "none" ? "" : `**${formatTimeMinutesOnly(t.startTime)}** - `;
      const statsStr = includeStats ? ` (${t.duration.toFixed(1)}s • ${t.wpm} WPM)` : "";
      lines.push(`${tc}**${name}**${statsStr}:`);
      lines.push(`${t.text}`);
      lines.push("");
    });

    return lines.join("\n");
  }

  if (templateStyle === "topic_flow") {
    const fileStem = `Video_${jobId.slice(0, 8)}`;
    const filename = `${fileStem}.mp4`;
    const lines = [
      `# ${fileStem}`,
      "",
      "## Section-Wise & Speaker-Wise Video Flow",
      `*Video: ${filename} | Duration: ${durationStr}*`,
      "",
      "### Section-Wise Video Flow and Timestamped Transcript",
      `*The transcript wording is taken from the supplied ${fileStem} transcript source, while the video duration and speaker/scene mapping were checked against the uploaded MUX video.*`,
      "",
      "| No. | Section | Timecode | Duration | Speaker | Dialogue / Transcript |",
      "| :---: | :---: | :---: | :---: | :---: | :--- |",
    ];

    let currentSec = "Introduction";
    let currentRank = 0;
    let secNo = 1;
    const totalTurns = dialogueTurns.length || 1;

    dialogueTurns.forEach((t, idx) => {
      const lower = t.text.toLowerCase();
      const relPos = idx / totalTurns;

      // Monotonic forward discourse phase progression (Rank 0 -> 5)
      let phaseRank = currentRank;
      let phaseTitle = currentSec;

      if (relPos >= 0.88 || lower.match(/\b(in conclusion|to summarize|in summary|to wrap up|that wraps up|key takeaways?|thank you)\b/)) {
        phaseRank = 5;
        phaseTitle = "Conclusion & Summary";
      } else if (lower.match(/\b(when we (use|combine|put together)|connects concepts|in practice|putting it all together|multidisciplinary)\b/)) {
        phaseRank = 4;
        phaseTitle = "Synthesis & Real-World Solution";
      } else if (lower.match(/\b(step\s+\d+|benchmark|how to (build|setup|create)|pins)\b/)) {
        phaseRank = 3;
        phaseTitle = "Hands-on Demonstration & Procedure";
      } else if (lower.match(/\b(this is called|stands for|integrated circuit|stem)\b/) || (currentRank < 2 && relPos >= 0.25)) {
        phaseRank = 2;
        phaseTitle = "Core Concept & Foundation";
      } else if (lower.match(/\b(the problem is|the challenge|identifying the problem|what happened|how can we|our goal|what is the issue)\b/)) {
        phaseRank = 1;
        phaseTitle = "Problem Statement";
      } else if (idx === 0 || lower.match(/\b(welcome|hello|good (morning|afternoon|evening)|today we|in this (video|session|presentation|meeting|talk|lecture))\b/)) {
        phaseRank = 0;
        phaseTitle = "Introduction";
      }

      // Strictly forward-moving section numbering
      if (phaseRank > currentRank) {
        currentRank = phaseRank;
        currentSec = phaseTitle;
        secNo++;
      }

      const tc = `${formatTimeMinutesOnly(t.startTime)} - ${formatTimeMinutesOnly(t.endTime)}`;
      const durLabel = `${Math.max(1, Math.round(t.duration))} sec`;
      const cleanText = t.text.replace(/\|/g, "\\|").replace(/\n/g, " ");
      lines.push(`| ${secNo} | **${currentSec}** | \`${tc}\` | ${durLabel} | ${t.displayName} | ${cleanText} |`);
    });

    return lines.join("\n");
  }

  if (templateStyle === "dialogue") {
    const lines: string[] = [];
    dialogueTurns.forEach((t) => {
      const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;
      lines.push(`${name}:`);
      lines.push(`${t.text}`);
      lines.push("");
    });
    return lines.join("\n");
  }

  // Default: Broadcast Script
  const lines = [
    "=".repeat(72),
    `BROADCAST TRANSCRIPTION SCRIPT: Job ${jobId.slice(0, 8)}`,
    `Recorded Duration: ${durationStr} | Language: ${language} | Total Words: ${totalWords}`,
    `Speakers (${transcript?.speakers?.length || 1}): ${speakersList}`,
    "=".repeat(72),
    "",
  ];

  dialogueTurns.forEach((t) => {
    const tc = formatTimestampStr(t.startTime, t.endTime, timestampStyle);
    const statsStr = includeStats ? `(${t.duration.toFixed(1)}s • ${t.wpm} WPM)` : "";
    const name = speakerCase === "upper" ? t.displayName.toUpperCase() : t.displayName;

    const header = [tc, statsStr, `${name}:`].filter(Boolean).join("  ");
    lines.push(header);
    lines.push(`  ${t.text}`);
    lines.push("");
  });

  return lines.join("\n");
}
