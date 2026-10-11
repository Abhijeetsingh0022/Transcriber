"use client";

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { Sparkles, Copy, Check, PanelRightOpen, PanelLeftOpen, FileText, Layers, Tv, Compass } from "lucide-react";

import {
  Transcript,
  JobInfo,
  DialogueTurn,
  AudioMarker,
  ABLoopState,
  ViewMode,
  FontSize,
  SidebarTab,
  TemplateStyle,
  TimestampStyle,
  SpeakerCase,
  WaveformBar,
  VideoTopic,
} from "./types";

import {
  API_BASE,
  fontClassMap,
  formatTime,
  formatTimeMinutesOnly,
  buildDialogueTurns,
  formatSpeakerDisplayName,
  calculateSpeakerStats,
  calculateAudioAnalytics,
  extractTopKeywords,
  renderScriptTemplate,
} from "./utils";

import { StudioHeader } from "./components/StudioHeader";
import { SettingsDrawer } from "./components/SettingsDrawer";
import { WorkstationDock } from "./components/WorkstationDock";
import { StudioInspector, InspectorTab } from "./components/StudioInspector";
import { FindReplaceBar } from "./components/FindReplaceBar";
import { DialogueTurnCard } from "./components/DialogueTurnCard";
import { SegmentCard } from "./components/SegmentCard";
import { TemplateModal } from "./components/TemplateModal";
import { SpeakerModal } from "./components/SpeakerModal";
import { MuxModal } from "./components/MuxModal";
import { TopicFlowView } from "./components/TopicFlowView";
import { ExecutiveIntelligenceView } from "./components/ExecutiveIntelligenceView";
import { PreferencesModal } from "../../components/PreferencesModal";

function StudioContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const routeJobId = (params?.jobId as string) || "";
  const jobId = (routeJobId && routeJobId !== "export") ? routeJobId : (searchParams?.get("jobId") || searchParams?.get("id") || "");

  // Core Data State
  const [isMounted, setIsMounted] = useState<boolean>(false);
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState<boolean>(true);
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [jobInfo, setJobInfo] = useState<JobInfo | null>(null);
  const [topics, setTopics] = useState<VideoTopic[]>([]);
  const [speakerNames, setSpeakerNames] = useState<Record<string, string>>({});
  const [saveStatus, setSaveStatus] = useState<string>("All changes saved");

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsMounted(true);
      if (typeof window !== "undefined") {
        if (window.innerWidth < 1024) {
          setIsLeftSidebarOpen(false);
          setIsRightSidebarOpen(false);
        } else if (window.innerWidth >= 1536) {
          setIsLeftSidebarOpen(true);
          setIsRightSidebarOpen(true);
        } else {
          setIsLeftSidebarOpen(true);
          setIsRightSidebarOpen(false);
        }
      }
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  // Audio Playback State
  const [currentTime, setCurrentTime] = useState<number>(0);
  const currentTimeRef = useRef<number>(0);
  useEffect(() => {
    currentTimeRef.current = currentTime;
  }, [currentTime]);
  const [duration, setDuration] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1.0);
  const [volume, setVolume] = useState<number>(1.0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [isLoopingTurn, setIsLoopingTurn] = useState<boolean>(false);
  const [loopTurnRange, setLoopTurnRange] = useState<{ start: number; end: number } | null>(null);

  // View & Customization Modes
  const [viewMode, setViewMode] = useState<ViewMode>("script");
  const [fontSize, setFontSize] = useState<FontSize>("base");
  const [followPlayhead, setFollowPlayhead] = useState<boolean>(true);
  const [showConfidence, setShowConfidence] = useState<boolean>(false);
  const [selectedSpeakerFilter, setSelectedSpeakerFilter] = useState<string | null>(null);

  // Search & Replace State
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [replaceQuery, setReplaceQuery] = useState<string>("");

  // Modals & Drawers
  const [isSpeakerModalOpen, setIsSpeakerModalOpen] = useState<boolean>(false);
  const [isTemplateModalOpen, setIsTemplateModalOpen] = useState<boolean>(false);
  const [isMuxModalOpen, setIsMuxModalOpen] = useState<boolean>(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isPreferencesOpen, setIsPreferencesOpen] = useState<boolean>(false);
  const [isIdentifyingSpeakers, setIsIdentifyingSpeakers] = useState<boolean>(false);

  // Script Template Modal Configuration
  const [templateStyle, setTemplateStyle] = useState<TemplateStyle>("broadcast");
  const [timestampStyle, setTimestampStyle] = useState<TimestampStyle>("range");
  const [speakerCase, setSpeakerCase] = useState<SpeakerCase>("upper");
  const [includeStats, setIncludeStats] = useState<boolean>(true);
  const [copiedTemplate, setCopiedTemplate] = useState<boolean>(false);

  // Inline Dialogue Turn Editing & Clipboard State
  const [editingTurnIndex, setEditingTurnIndex] = useState<number | null>(null);
  const [editingTurnText, setEditingTurnText] = useState<string>("");
  const [copiedTurnIndex, setCopiedTurnIndex] = useState<number | null>(null);
  const [copiedScript, setCopiedScript] = useState<boolean>(false);

  // Workstation Dock State
  const [sidebarTab, setSidebarTab] = useState<SidebarTab>("speakers");
  const [inlineRenameLabel, setInlineRenameLabel] = useState<string | null>(null);
  const [inlineRenameVal, setInlineRenameVal] = useState<string>("");
  const [colorPickerLabel, setColorPickerLabel] = useState<string | null>(null);
  const [mergeSourceLabel, setMergeSourceLabel] = useState<string | null>(null);
  const [mergeTargetLabel, setMergeTargetLabel] = useState<string>("");
  const [skipStep, setSkipStep] = useState<number>(5);
  const [markers, setMarkers] = useState<AudioMarker[]>([]);
  const [newMarkerText, setNewMarkerText] = useState<string>("");
  const [newMarkerTag, setNewMarkerTag] = useState<"note" | "review" | "highlight">("note");
  const [abLoop, setAbLoop] = useState<ABLoopState>({ a: null, b: null, active: false });
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("tools");
  const [waveformPeaks, setWaveformPeaks] = useState<number[]>([]);
  const [history, setHistory] = useState<Transcript[]>([]);
  const [future, setFuture] = useState<Transcript[]>([]);

  // Push transcript snapshot before mutations
  const pushHistory = useCallback((current: Transcript | null) => {
    if (!current) return;
    setHistory((prev) => [...prev.slice(-19), current]);
    setFuture([]);
  }, []);

  // DOM Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeTurnRef = useRef<HTMLDivElement | null>(null);
  const waveformRef = useRef<HTMLDivElement | null>(null);
  const [hoveredWaveTime, setHoveredWaveTime] = useState<{
    time: number;
    xPercent: number;
    speakerName?: string;
  } | null>(null);

  // 1. Fetch transcript & job metadata
  useEffect(() => {
    if (!jobId) return;
    const loadData = async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}/transcript`);
        if (res.ok) {
          const data: Transcript = await res.json();
          setTranscript(data);

          const nameMap: Record<string, string> = {};
          data.speakers.forEach((s) => {
            nameMap[s.speaker_label] = formatSpeakerDisplayName(s.display_name, s.speaker_label);
          });
          setSpeakerNames(nameMap);

          if (data.segments?.length) {
            const lastEnd = data.segments[data.segments.length - 1].end_time;
            if (lastEnd > 0) {
              setDuration((prev) => (prev > 0 ? prev : lastEnd));
            }
          }
        }
      } catch {}

      try {
        const resJob = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (resJob.ok) {
          const jobData = await resJob.json();
          setJobInfo(jobData);
          if (jobData.duration_seconds && jobData.duration_seconds > 0) {
            setDuration((prev) => (prev > 0 ? prev : jobData.duration_seconds));
          }
        }
      } catch {}

      try {
        const resTopics = await fetch(`${API_BASE}/jobs/${jobId}/topics`);
        if (resTopics.ok) {
          const topicData = await resTopics.json();
          setTopics(topicData.topics || []);
        }
      } catch {}

      try {
        const resWave = await fetch(`${API_BASE}/jobs/${jobId}/waveform`);
        if (resWave.ok) {
          const waveData = await resWave.json();
          if (Array.isArray(waveData.peaks) && waveData.peaks.length > 0) {
            setWaveformPeaks(waveData.peaks);
          }
        }
      } catch {}

      try {
        const resMarkers = await fetch(`${API_BASE}/jobs/${jobId}/markers`);
        if (resMarkers.ok) {
          const markerData = await resMarkers.json();
          if (Array.isArray(markerData)) {
            setMarkers(markerData.sort((a: AudioMarker, b: AudioMarker) => a.time - b.time));
          }
        }
      } catch {}
    };
    loadData();
  }, [jobId]);

  // Robust Effective Duration from Audio Element, Job Info, or Segment Timestamps
  const effectiveDuration = useMemo(() => {
    if (duration > 0) return duration;
    if (jobInfo?.duration_seconds && jobInfo.duration_seconds > 0) return jobInfo.duration_seconds;
    if (transcript?.segments && transcript.segments.length > 0) {
      return transcript.segments[transcript.segments.length - 1].end_time;
    }
    return 0;
  }, [duration, jobInfo, transcript]);

  // Source media filename stem for downloads
  const mediaStem = useMemo(() => {
    return jobInfo?.filename ? jobInfo.filename.replace(/\.[^/.]+$/, "") : `transcript_${jobId.slice(0, 8)}`;
  }, [jobInfo, jobId]);

  // 2. Aggregate segments into coherent dialogue turns
  const dialogueTurns = useMemo<DialogueTurn[]>(() => {
    return buildDialogueTurns(transcript?.segments, transcript?.speakers, speakerNames);
  }, [transcript, speakerNames]);

  // 3. Filtered turns based on active speaker filter & search
  const visibleTurns = useMemo(() => {
    return dialogueTurns.filter((turn) => {
      if (selectedSpeakerFilter && turn.speakerLabel !== selectedSpeakerFilter) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        return (
          (turn.text || "").toLowerCase().includes(q) ||
          (turn.displayName || "").toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [dialogueTurns, selectedSpeakerFilter, searchQuery]);

  // Search match statistics
  const searchMatchesCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const q = searchQuery.toLowerCase();
    let count = 0;
    dialogueTurns.forEach((t) => {
      const matches = (t.text || "").toLowerCase().split(q).length - 1;
      count += matches;
    });
    return count;
  }, [dialogueTurns, searchQuery]);

  // 4. Compute speaker talk time & stats
  const speakerStats = useMemo(() => {
    return calculateSpeakerStats(transcript?.speakers, dialogueTurns);
  }, [transcript, dialogueTurns]);

  // 5. Audio & Pacing Analytics
  const audioAnalytics = useMemo(() => {
    return calculateAudioAnalytics(transcript?.segments, effectiveDuration, dialogueTurns);
  }, [transcript, effectiveDuration, dialogueTurns]);

  // 6. Top Keywords Extraction
  const topKeywords = useMemo(() => {
    return extractTopKeywords(transcript?.segments);
  }, [transcript]);

  // 7. Multi-Speaker Speech Density Waveform (52 bars)
  const BARS_COUNT = 52;
  const waveformBars = useMemo<WaveformBar[]>(() => {
    if (effectiveDuration <= 0) {
      return Array.from({ length: BARS_COUNT }).map((_, i) => ({
        index: i,
        time: 0,
        height: 6,
        color: "#475569",
        isSpeech: false,
        speakerName: "Silence",
      }));
    }

    const sliceDur = effectiveDuration / BARS_COUNT;

    return Array.from({ length: BARS_COUNT }).map((_, i) => {
      const barTimeStart = i * sliceDur;
      const barTimeEnd = (i + 1) * sliceDur;
      const barMidTime = (barTimeStart + barTimeEnd) / 2;

      const turn = dialogueTurns.find(
        (t) => Math.max(t.startTime, barTimeStart) < Math.min(t.endTime, barTimeEnd)
      );

      let peakAmp = 0;
      if (waveformPeaks.length > 0) {
        const peakIdx = Math.min(
          waveformPeaks.length - 1,
          Math.floor((i / BARS_COUNT) * waveformPeaks.length)
        );
        peakAmp = waveformPeaks[peakIdx] || 0;
      }

      if (turn) {
        const amp = peakAmp > 0 ? peakAmp : (Math.sin(i * 1.6 + 0.3) * 0.35 + 0.65);
        const baseH = 8 + Math.round(amp * 20);
        return {
          index: i,
          time: barMidTime,
          height: Math.min(28, Math.max(8, baseH)),
          color: turn.colorHex || "#3b82f6",
          isSpeech: true,
          speakerName: turn.displayName || turn.speakerLabel,
        };
      } else {
        const baseH = peakAmp > 0.05 ? Math.min(10, Math.round(peakAmp * 12)) : 5;
        return {
          index: i,
          time: barMidTime,
          height: baseH,
          color: "#334155",
          isSpeech: false,
          speakerName: "Silence",
        };
      }
    });
  }, [effectiveDuration, dialogueTurns, waveformPeaks]);

  // Active dialogue turn at current playhead position
  const currentActiveTurn = useMemo(() => {
    if (!dialogueTurns.length) return null;
    return (
      dialogueTurns.find(
        (t) => currentTime >= t.startTime && currentTime <= t.endTime
      ) || null
    );
  }, [dialogueTurns, currentTime]);

  // Script Template Preview Content
  const renderedTemplateContent = useMemo(() => {
    return renderScriptTemplate({
      dialogueTurns,
      transcript,
      templateStyle,
      timestampStyle,
      speakerCase,
      includeStats,
      duration,
      jobId,
    });
  }, [dialogueTurns, transcript, templateStyle, timestampStyle, speakerCase, includeStats, duration, jobId]);

  // Audio Playback Engine Callbacks
  const togglePlay = useCallback(() => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const skipSeconds = useCallback((sec: number) => {
    if (!audioRef.current) return;
    const maxDur = effectiveDuration > 0 ? effectiveDuration : (duration > 0 ? duration : 999999);
    const newTime = Math.max(0, Math.min(audioRef.current.currentTime + sec, maxDur));
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  }, [effectiveDuration, duration]);

  const seekTo = useCallback((time: number) => {
    if (!audioRef.current) return;
    const maxDur = effectiveDuration > 0 ? effectiveDuration : (duration > 0 ? duration : 999999);
    const targetTime = Math.max(0, Math.min(time, maxDur));
    audioRef.current.currentTime = targetTime;
    setCurrentTime(targetTime);
    if (!isPlaying) {
      audioRef.current.play();
      setIsPlaying(true);
    }
  }, [effectiveDuration, duration, isPlaying]);

  const jumpToPreviousTurn = useCallback(() => {
    if (!dialogueTurns.length) return;
    const cur = currentTimeRef.current;
    const prevTurn = [...dialogueTurns].reverse().find((t) => t.startTime < cur - 0.75);
    if (prevTurn) {
      seekTo(prevTurn.startTime);
    } else {
      seekTo(0);
    }
  }, [dialogueTurns, seekTo]);

  const jumpToNextTurn = useCallback(() => {
    if (!dialogueTurns.length) return;
    const cur = currentTimeRef.current;
    const nextTurn = dialogueTurns.find((t) => t.startTime > cur + 0.25);
    if (nextTurn) {
      seekTo(nextTurn.startTime);
    }
  }, [dialogueTurns, seekTo]);

  const loopTurn = useCallback((turn: DialogueTurn) => {
    if (isLoopingTurn && loopTurnRange?.start === turn.startTime) {
      setIsLoopingTurn(false);
      setLoopTurnRange(null);
    } else {
      setIsLoopingTurn(true);
      setLoopTurnRange({ start: turn.startTime, end: turn.endTime });
      seekTo(turn.startTime);
    }
  }, [isLoopingTurn, loopTurnRange, seekTo]);

  const toggleLoopCurrentTurn = useCallback(() => {
    if (isLoopingTurn) {
      setIsLoopingTurn(false);
      setLoopTurnRange(null);
    } else if (currentActiveTurn) {
      loopTurn(currentActiveTurn);
    } else if (dialogueTurns.length > 0) {
      const cur = currentTimeRef.current;
      const closest = dialogueTurns.find((t) => cur <= t.endTime) || dialogueTurns[0];
      if (closest) loopTurn(closest);
    }
  }, [isLoopingTurn, currentActiveTurn, dialogueTurns, loopTurn]);

  const setSpeed = (spd: number) => {
    setPlaybackSpeed(spd);
    if (audioRef.current) {
      audioRef.current.playbackRate = spd;
    }
  };

  const handleVolumeChange = (newVol: number) => {
    setVolume(newVol);
    setIsMuted(newVol === 0);
    if (audioRef.current) {
      audioRef.current.volume = newVol;
      audioRef.current.muted = newVol === 0;
    }
  };

  const toggleMute = () => {
    if (!audioRef.current) return;
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    audioRef.current.muted = nextMuted;
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const time = audioRef.current.currentTime;
    currentTimeRef.current = time;
    setCurrentTime(time);

    if (abLoop.active && abLoop.a !== null && abLoop.b !== null) {
      if (time >= abLoop.b) {
        audioRef.current.currentTime = abLoop.a;
        return;
      }
    }

    if (isLoopingTurn && loopTurnRange) {
      if (time >= loopTurnRange.end) {
        audioRef.current.currentTime = loopTurnRange.start;
      }
    }
  };

  const handleWaveformClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!waveformRef.current || effectiveDuration <= 0) return;
    const rect = waveformRef.current.getBoundingClientRect();
    const clickX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const ratio = clickX / rect.width;
    seekTo(ratio * effectiveDuration);
  };

  const handleWaveformMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!waveformRef.current || effectiveDuration <= 0) return;
    const rect = waveformRef.current.getBoundingClientRect();
    const mouseX = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const ratio = mouseX / rect.width;
    const targetTime = ratio * effectiveDuration;
    const sliceDur = effectiveDuration / BARS_COUNT;
    const bar = waveformBars.find((b) => Math.abs(b.time - targetTime) <= sliceDur);
    setHoveredWaveTime({
      time: targetTime,
      xPercent: ratio * 100,
      speakerName: bar?.isSpeech ? bar.speakerName : undefined,
    });
  };

  // Markers operations
  const handleAddMarker = useCallback(
    async (customTime?: number, customLabel?: string, customTag?: "note" | "review" | "highlight") => {
      const t = customTime !== undefined ? customTime : currentTimeRef.current;
      const label = customLabel || newMarkerText.trim() || `Bookmark @ ${formatTime(t)}`;
      const m: AudioMarker = {
        id: `m_${Date.now()}`,
        time: t,
        label,
        tag: customTag || newMarkerTag,
      };
      setMarkers((prev) => [...prev, m].sort((a, b) => a.time - b.time));
      setNewMarkerText("");
      setSaveStatus("Marker saved");
      setTimeout(() => setSaveStatus("All changes saved"), 1500);

      try {
        await fetch(`${API_BASE}/jobs/${jobId}/markers`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(m),
        });
      } catch (err) {
        console.error("Failed to persist marker:", err);
      }
    },
    [jobId, newMarkerText, newMarkerTag]
  );

  const handleDeleteMarker = useCallback(
    async (id: string) => {
      setMarkers((prev) => prev.filter((m) => m.id !== id));
      try {
        await fetch(`${API_BASE}/jobs/${jobId}/markers/${id}`, {
          method: "DELETE",
        });
      } catch (err) {
        console.error("Failed to delete marker:", err);
      }
    },
    [jobId]
  );

  // Undo / Redo Actions
  const handleUndo = useCallback(async () => {
    if (history.length === 0 || !transcript) return;
    const previous = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    setFuture((prev) => [transcript, ...prev.slice(0, 19)]);
    setTranscript(previous);
    setSaveStatus("Undone");

    try {
      await Promise.all(
        previous.segments.map((seg) =>
          fetch(`${API_BASE}/jobs/${jobId}/segments/${seg.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: seg.text }),
          })
        )
      );
      setTimeout(() => setSaveStatus("All changes saved"), 1500);
    } catch {
      setSaveStatus("Undo sync failed");
    }
  }, [history, transcript, jobId]);

  const handleRedo = useCallback(async () => {
    if (future.length === 0 || !transcript) return;
    const next = future[0];
    setFuture((prev) => prev.slice(1));
    setHistory((prev) => [...prev, transcript]);
    setTranscript(next);
    setSaveStatus("Redone");

    try {
      await Promise.all(
        next.segments.map((seg) =>
          fetch(`${API_BASE}/jobs/${jobId}/segments/${seg.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: seg.text }),
          })
        )
      );
      setTimeout(() => setSaveStatus("All changes saved"), 1500);
    } catch {
      setSaveStatus("Redo sync failed");
    }
  }, [future, transcript, jobId]);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || "").toLowerCase();
      if (activeTag === "input" || activeTag === "textarea") return;

      if (e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        skipSeconds(-skipStep);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        skipSeconds(skipStep);
      } else if (e.code === "KeyJ") {
        skipSeconds(-skipStep);
      } else if (e.code === "KeyL") {
        skipSeconds(skipStep);
      } else if (e.code === "BracketLeft") {
        e.preventDefault();
        jumpToPreviousTurn();
      } else if (e.code === "BracketRight") {
        e.preventDefault();
        jumpToNextTurn();
      } else if (e.code === "KeyK") {
        togglePlay();
      } else if (e.code === "KeyM" && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        handleAddMarker();
      } else if ((e.ctrlKey || e.metaKey) && e.code === "KeyZ") {
        e.preventDefault();
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.code === "KeyY") {
        e.preventDefault();
        handleRedo();
      } else if ((e.ctrlKey || e.metaKey) && e.code === "KeyF") {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      } else if (e.code === "Escape") {
        setIsSearchOpen(false);
        setIsTemplateModalOpen(false);
        setIsSpeakerModalOpen(false);
        setEditingTurnIndex(null);
        setInlineRenameLabel(null);
        setColorPickerLabel(null);
        setMergeSourceLabel(null);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [togglePlay, skipSeconds, jumpToPreviousTurn, jumpToNextTurn, skipStep, handleAddMarker, handleUndo, handleRedo]);

  // Auto-scroll Follow Playhead: trigger only when the speaker turn changes
  useEffect(() => {
    if (!followPlayhead || !isPlaying) return;
    if (activeTurnRef.current) {
      activeTurnRef.current.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
    }
  }, [currentActiveTurn?.turnIndex, followPlayhead, isPlaying]);

  // Speaker Operations
  const handleQuickSpeakerRename = async (speakerLabel: string, newName: string) => {
    if (!newName.trim()) {
      setInlineRenameLabel(null);
      return;
    }
    const trimmed = newName.trim();
    setSpeakerNames((prev) => ({ ...prev, [speakerLabel]: trimmed }));
    setInlineRenameLabel(null);

    try {
      await fetch(`${API_BASE}/jobs/${jobId}/speakers`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([{ speaker_label: speakerLabel, display_name: trimmed }]),
      });

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          speakers: prev.speakers.map((s) =>
            s.speaker_label === speakerLabel ? { ...s, display_name: trimmed } : s
          ),
        };
      });
      setSaveStatus(`Renamed to ${trimmed}`);
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {}
  };

  const handleSpeakerColorChange = async (speakerLabel: string, colorHex: string) => {
    setColorPickerLabel(null);
    setTranscript((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        speakers: prev.speakers.map((s) =>
          s.speaker_label === speakerLabel ? { ...s, color_hex: colorHex } : s
        ),
      };
    });

    try {
      await fetch(`${API_BASE}/jobs/${jobId}/speakers`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify([{ speaker_label: speakerLabel, color_hex: colorHex }]),
      });
      setSaveStatus("Speaker color updated");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {}
  };

  const handleMergeSpeaker = async (sourceLabel: string, targetLabel: string) => {
    if (sourceLabel === targetLabel || !dialogueTurns.length) return;
    const turnsToMerge = dialogueTurns.filter((t) => t.speakerLabel === sourceLabel);
    const segIds = turnsToMerge.flatMap((t) => t.segmentIds);
    if (!segIds.length) return;

    try {
      await fetch(`${API_BASE}/jobs/${jobId}/segments/speaker`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          segment_ids: segIds,
          speaker_label: targetLabel,
        }),
      });

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          segments: prev.segments.map((s) =>
            segIds.includes(s.id) ? { ...s, speaker_label: targetLabel } : s
          ),
        };
      });
      setMergeSourceLabel(null);
      setSaveStatus("Speakers merged");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {}
  };

  const handleBulkSpeakerRename = async () => {
    if (!transcript) return;
    const updates = Object.entries(speakerNames).map(([speaker_label, display_name]) => ({
      speaker_label,
      display_name,
    }));

    try {
      await fetch(`${API_BASE}/jobs/${jobId}/speakers`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          speakers: prev.speakers.map((s) => ({
            ...s,
            display_name: speakerNames[s.speaker_label] || s.display_name,
          })),
        };
      });

      setIsSpeakerModalOpen(false);
      setSaveStatus("Speaker names updated");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {}
  };

  const handleSmartIdentifySpeakers = async () => {
    setIsIdentifyingSpeakers(true);
    setSaveStatus("Detecting speakers & roles...");
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/identify_speakers`, {
        method: "POST",
      });
      if (!res.ok) {
        throw new Error("Failed to auto-identify speakers");
      }
      const data = await res.json();

      // Refresh transcript data with updated speaker assignments and roles
      const txRes = await fetch(`${API_BASE}/jobs/${jobId}/transcript`);
      if (txRes.ok) {
        const txData: Transcript = await txRes.json();
        setTranscript(txData);
        if (txData.speakers) {
          const names: Record<string, string> = {};
          txData.speakers.forEach((s) => {
            names[s.speaker_label] = s.display_name;
          });
          setSpeakerNames(names);
        }
      }

      const roleSummary = [
        data.student_name ? `Student: ${data.student_name}` : null,
        data.teacher_name ? `Teacher: ${data.teacher_name}` : null,
        data.narrator_segments ? `Narrator: ${data.narrator_segments} segs` : null,
      ]
        .filter(Boolean)
        .join(" | ");

      setSaveStatus(roleSummary ? `Identified: ${roleSummary}` : "Auto-identification complete");
      setTimeout(() => setSaveStatus("All changes saved"), 3500);
    } catch (err) {
      console.error(err);
      setSaveStatus("Auto-identification failed");
      setTimeout(() => setSaveStatus("All changes saved"), 3000);
    } finally {
      setIsIdentifyingSpeakers(false);
    }
  };

  const handleReassignSpeaker = useCallback(async (segmentIds: string[], newSpeakerLabel: string) => {
    setSaveStatus("Reassigning speaker...");
    try {
      await fetch(`${API_BASE}/jobs/${jobId}/segments/speaker`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segment_ids: segmentIds, speaker_label: newSpeakerLabel }),
      });

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          segments: prev.segments.map((seg) =>
            segmentIds.includes(seg.id) ? { ...seg, speaker_label: newSpeakerLabel } : seg
          ),
        };
      });

      setSaveStatus("Speaker reassigned");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {
      setSaveStatus("Reassignment failed");
    }
  }, [jobId]);

  const handleReassignAddressee = useCallback(async (segmentIds: string[], newAddressedTo: string) => {
    setSaveStatus("Reassigning addressee...");
    try {
      await fetch(`${API_BASE}/jobs/${jobId}/segments/addressee`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ segment_ids: segmentIds, addressed_to: newAddressedTo }),
      });

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          segments: prev.segments.map((seg) =>
            segmentIds.includes(seg.id) ? { ...seg, addressed_to: newAddressedTo } : seg
          ),
        };
      });

      setSaveStatus("Addressee updated");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {
      setSaveStatus("Addressee update failed");
    }
  }, [jobId]);

  // Stable handlers for editing dialogue cards
  const handleStartEditTurn = useCallback((turn: DialogueTurn) => {
    setEditingTurnIndex(turn.turnIndex);
    setEditingTurnText(turn.text);
  }, []);

  const handleCancelEditTurn = useCallback(() => {
    setEditingTurnIndex(null);
  }, []);

  // Inline Dialogue Turn Editing
  const handleSaveTurnText = useCallback(async (turn: DialogueTurn) => {
    if (!editingTurnText.trim() || editingTurnText.trim() === turn.text.trim()) {
      setEditingTurnIndex(null);
      return;
    }

    pushHistory(transcript);
    setSaveStatus("Saving dialogue edit...");
    try {
      const firstSegId = turn.segmentIds[0];
      await fetch(`${API_BASE}/jobs/${jobId}/segments/${firstSegId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: editingTurnText.trim() }),
      });

      if (turn.segmentIds.length > 1) {
        for (let i = 1; i < turn.segmentIds.length; i++) {
          await fetch(`${API_BASE}/jobs/${jobId}/segments/${turn.segmentIds[i]}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: "" }),
          });
        }
      }

      setTranscript((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          segments: prev.segments.map((seg) => {
            if (seg.id === firstSegId) return { ...seg, text: editingTurnText.trim() };
            if (turn.segmentIds.slice(1).includes(seg.id)) return { ...seg, text: "" };
            return seg;
          }),
        };
      });

      setEditingTurnIndex(null);
      setSaveStatus("Dialogue saved");
      setTimeout(() => setSaveStatus("All changes saved"), 2000);
    } catch {
      setSaveStatus("Save failed");
    }
  }, [editingTurnText, transcript, jobId, pushHistory]);

  // Replace All in Transcript
  const handleReplaceAll = async () => {
    if (!searchQuery.trim() || !transcript) return;
    pushHistory(transcript);
    setSaveStatus("Replacing across transcript...");

    const targetRegex = new RegExp(searchQuery, "gi");
    let changedCount = 0;

    const updatedSegments = await Promise.all(
      transcript.segments.map(async (seg) => {
        if (targetRegex.test(seg.text)) {
          changedCount++;
          const newText = seg.text.replace(targetRegex, replaceQuery);
          try {
            await fetch(`${API_BASE}/jobs/${jobId}/segments/${seg.id}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ text: newText }),
            });
            return { ...seg, text: newText };
          } catch {
            return seg;
          }
        }
        return seg;
      })
    );

    setTranscript((prev) => (prev ? { ...prev, segments: updatedSegments } : null));
    setSaveStatus(`Replaced ${changedCount} occurrences`);
    setTimeout(() => setSaveStatus("All changes saved"), 2000);
  };

  // Copy & Download Helpers
  const copyScriptToClipboard = () => {
    if (!dialogueTurns.length) return;
    const header = [
      "=".repeat(70),
      `TRANSCRIPT SCRIPT: Job ${jobId.slice(0, 8)}`,
      `Duration: ${formatTime(duration)} | Language: ${transcript?.detected_language?.toUpperCase() || "AUTO"} | Words: ${transcript?.word_count || 0}`,
      "=".repeat(70),
      "",
    ].join("\n");

    const body = dialogueTurns
      .map(
        (t) =>
          `[${formatTimeMinutesOnly(t.startTime)} - ${formatTimeMinutesOnly(t.endTime)}] (${Math.round(
            t.duration
          )}s)  ${t.displayName.toUpperCase()}:\n  ${t.text}\n`
      )
      .join("\n");

    navigator.clipboard.writeText(`${header}\n${body}`);
    setCopiedScript(true);
    setTimeout(() => setCopiedScript(false), 2000);
  };

  const copyTurnToClipboard = useCallback((turn: DialogueTurn) => {
    const str = `[${formatTimeMinutesOnly(turn.startTime)} - ${formatTimeMinutesOnly(turn.endTime)}] ${turn.displayName}: ${turn.text}`;
    navigator.clipboard.writeText(str);
    setCopiedTurnIndex(turn.turnIndex);
    setTimeout(() => setCopiedTurnIndex(null), 1800);
  }, []);

  const copyTemplateContent = () => {
    navigator.clipboard.writeText(renderedTemplateContent);
    setCopiedTemplate(true);
    setTimeout(() => setCopiedTemplate(false), 2000);
  };

  const downloadTemplateContent = () => {
    const ext = templateStyle === "podcast" || templateStyle === "topic_flow" ? "md" : "txt";
    const blob = new Blob([renderedTemplateContent], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${mediaStem}_${templateStyle}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const currentFontClass = fontClassMap[fontSize];

  return (
    <div className="fixed inset-0 flex flex-col bg-slate-50 text-slate-900 overflow-hidden font-sans">
      {/* 1. TOP WORKSTATION CONTROL BAR */}
      <StudioHeader
        jobId={jobId}
        jobInfo={jobInfo}
        isMounted={isMounted}
        isPlaying={isPlaying}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        saveStatus={saveStatus}
        followPlayhead={followPlayhead}
        onToggleFollow={() => setFollowPlayhead(!followPlayhead)}
        showConfidence={showConfidence}
        onToggleConfidence={() => setShowConfidence(!showConfidence)}
        isSearchOpen={isSearchOpen}
        onToggleSearch={() => setIsSearchOpen(!isSearchOpen)}
        onUndo={handleUndo}
        onRedo={handleRedo}
        canUndo={history.length > 0}
        canRedo={future.length > 0}
        onOpenTemplateModal={() => setIsTemplateModalOpen(true)}
        onOpenSpeakerModal={() => setIsSpeakerModalOpen(true)}
        isSettingsOpen={isSettingsOpen}
        onToggleSettings={() => setIsSettingsOpen(!isSettingsOpen)}
        onOpenPreferences={() => setIsPreferencesOpen(true)}
        isLeftSidebarOpen={isLeftSidebarOpen}
        onToggleLeftSidebar={() => setIsLeftSidebarOpen((prev) => !prev)}
        isRightSidebarOpen={isRightSidebarOpen}
        onToggleRightSidebar={() => {
          setIsRightSidebarOpen((prev) => {
            if (!prev) setInspectorTab("tools");
            return !prev;
          });
        }}
        mediaStem={mediaStem}
        onIdentifySpeakers={handleSmartIdentifySpeakers}
        isIdentifyingSpeakers={isIdentifyingSpeakers}
        onOpenMux={() => setIsMuxModalOpen(true)}
      />

      {/* Settings Popover Drawer */}
      <SettingsDrawer
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        fontSize={fontSize}
        onFontSizeChange={setFontSize}
        playbackSpeed={playbackSpeed}
        onSpeedChange={setSpeed}
      />

      {/* 2. MAIN WORKSTATION SPLIT PANE */}
      <div className="flex-1 min-h-0 flex overflow-hidden p-2 sm:p-2.5 lg:p-3 gap-2 sm:gap-2.5 lg:gap-3">
        {/* LEFT DOCK: ADVANCED WORKSTATION SUITE (420px WIDE) */}
        <WorkstationDock
          jobId={jobId}
          audioRef={audioRef}
          currentTime={currentTime}
          duration={duration}
          effectiveDuration={effectiveDuration}
          isPlaying={isPlaying}
          playbackSpeed={playbackSpeed}
          volume={volume}
          isMuted={isMuted}
          isLoopingTurn={isLoopingTurn}
          loopTurnRange={loopTurnRange}
          abLoop={abLoop}
          currentActiveTurn={currentActiveTurn}
          waveformBars={waveformBars}
          hoveredWaveTime={hoveredWaveTime}
          skipStep={skipStep}
          followPlayhead={followPlayhead}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            if (audioRef.current?.duration && !isNaN(audioRef.current.duration)) {
              setDuration(audioRef.current.duration);
            }
          }}
          onDurationChange={() => {
            if (audioRef.current?.duration && !isNaN(audioRef.current.duration)) {
              setDuration(audioRef.current.duration);
            }
          }}
          onEnded={() => {
            if (isLoopingTurn && loopTurnRange && audioRef.current) {
              audioRef.current.currentTime = loopTurnRange.start;
              audioRef.current.play();
            } else if (abLoop.active && abLoop.a !== null && audioRef.current) {
              audioRef.current.currentTime = abLoop.a;
              audioRef.current.play();
            } else {
              setIsPlaying(false);
            }
          }}
          onTogglePlay={togglePlay}
          onSeekTo={seekTo}
          onSkipSeconds={skipSeconds}
          onJumpPreviousTurn={jumpToPreviousTurn}
          onJumpNextTurn={jumpToNextTurn}
          onLoopTurn={loopTurn}
          onToggleLoopTurn={toggleLoopCurrentTurn}
          onAddMarker={handleAddMarker}
          onSetSpeed={setSpeed}
          onVolumeChange={handleVolumeChange}
          onToggleMute={toggleMute}
          onToggleFollow={() => setFollowPlayhead(!followPlayhead)}
          onWaveformMouseMove={handleWaveformMouseMove}
          onWaveformMouseLeave={() => setHoveredWaveTime(null)}
          onWaveformClick={handleWaveformClick}
          waveformRef={waveformRef}

          sidebarTab={sidebarTab}
          onTabChange={setSidebarTab}
          speakerStats={speakerStats}
          selectedSpeakerFilter={selectedSpeakerFilter}
          onToggleSpeakerFilter={setSelectedSpeakerFilter}
          onOpenSpeakerModal={() => setIsSpeakerModalOpen(true)}
          inlineRenameLabel={inlineRenameLabel}
          inlineRenameVal={inlineRenameVal}
          onStartInlineRename={(label, name) => {
            setInlineRenameLabel(label);
            setInlineRenameVal(name);
          }}
          onCancelInlineRename={() => setInlineRenameLabel(null)}
          onSaveInlineRename={handleQuickSpeakerRename}
          onChangeInlineRenameVal={setInlineRenameVal}
          colorPickerLabel={colorPickerLabel}
          onToggleColorPicker={setColorPickerLabel}
          onChangeSpeakerColor={handleSpeakerColorChange}
          mergeSourceLabel={mergeSourceLabel}
          mergeTargetLabel={mergeTargetLabel}
          onStartMerge={(label) => {
            setMergeSourceLabel(label);
            setMergeTargetLabel("");
          }}
          onCancelMerge={() => setMergeSourceLabel(null)}
          onChangeMergeTarget={setMergeTargetLabel}
          onConfirmMerge={handleMergeSpeaker}
          onIdentifySpeakers={handleSmartIdentifySpeakers}
          isIdentifyingSpeakers={isIdentifyingSpeakers}

          markers={markers}
          newMarkerText={newMarkerText}
          newMarkerTag={newMarkerTag}
          onChangeMarkerText={setNewMarkerText}
          onChangeMarkerTag={setNewMarkerTag}
          onDeleteMarker={handleDeleteMarker}

          audioAnalytics={audioAnalytics}
          totalWords={transcript?.word_count || 0}
          dialogueTurnsCount={dialogueTurns.length}
          topKeywords={topKeywords}
          onSelectKeyword={(word) => {
            setSearchQuery(word);
            setIsSearchOpen(true);
          }}

          onSetAbLoopPoint={(point, time) => {
            setAbLoop((prev) => ({ ...prev, [point]: time }));
          }}
          onToggleAbLoop={() => {
            if (abLoop.a !== null && abLoop.b !== null) {
              setAbLoop((prev) => ({ ...prev, active: !prev.active }));
              if (!abLoop.active && abLoop.a !== null) seekTo(abLoop.a);
            }
          }}
          onClearAbLoop={() => setAbLoop({ a: null, b: null, active: false })}
          onChangeSkipStep={setSkipStep}

          saveStatus={saveStatus}
          isOpen={isLeftSidebarOpen}
          onClose={() => setIsLeftSidebarOpen(false)}
        />

        {/* CENTER STAGE: SYNCHRONIZED TRANSCRIPT WORKSPACE */}
        <div className="flex-1 min-w-0 h-full bg-white/70 backdrop-blur-xs rounded-lg border border-slate-200/80 flex flex-col overflow-hidden relative shadow-xs">
          {/* Edge Re-open Button when Left Dock is Collapsed */}
          {!isLeftSidebarOpen && (
            <button
              onClick={() => setIsLeftSidebarOpen(true)}
              className="absolute left-0 top-1/2 -translate-y-1/2 bg-white/95 hover:bg-white backdrop-blur-md border-r border-y border-slate-200/90 pl-1.5 pr-2 py-3 rounded-r-lg shadow-md text-slate-500 hover:text-blue-600 transition-all flex flex-col items-center gap-1.5 z-20 group hover:shadow-lg active:scale-95 cursor-pointer"
              title="Open Left Dock (Audio Deck & Speakers)"
            >
              <PanelLeftOpen className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
              <span className="text-[9px] font-bold uppercase tracking-widest [writing-mode:vertical-lr] text-slate-400 group-hover:text-slate-700">
                Audio
              </span>
            </button>
          )}

          {/* Find & Replace Drawer */}
          <FindReplaceBar
            isOpen={isSearchOpen}
            onClose={() => {
              setIsSearchOpen(false);
              setSearchQuery("");
              setReplaceQuery("");
            }}
            searchQuery={searchQuery}
            onChangeSearchQuery={setSearchQuery}
            replaceQuery={replaceQuery}
            onChangeReplaceQuery={setReplaceQuery}
            searchMatchesCount={searchMatchesCount}
            onReplaceAll={handleReplaceAll}
          />

          {/* Active Filter Banner */}
          {selectedSpeakerFilter && (
            <div className="bg-blue-50/80 border-b border-blue-200 px-6 py-2 flex items-center justify-between text-xs text-blue-900 shrink-0">
              <span className="font-medium">
                Filtering by speaker:{" "}
                <strong>{speakerNames[selectedSpeakerFilter] || selectedSpeakerFilter}</strong> (
                {visibleTurns.length} turns)
              </span>
              <button
                onClick={() => setSelectedSpeakerFilter(null)}
                className="text-xs font-semibold text-blue-700 hover:text-blue-900 underline"
              >
                Clear Filter
              </button>
            </div>
          )}

          {/* Main Scrollable Content */}
          <div className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-6 lg:p-8 max-w-5xl 2xl:max-w-6xl w-full mx-auto space-y-4 pb-16">
            {!transcript ? (
              <div className="flex flex-col items-center justify-center py-24 space-y-4 text-center">
                <div className="relative flex items-center justify-center w-12 h-12 rounded-lg bg-gradient-to-br from-blue-500/10 via-cyan-500/10 to-blue-500/5 border border-blue-200/60 shadow-xs">
                  <span className="flex items-end gap-1 h-5 px-1 pb-1">
                    <span className="w-1 bg-blue-600 rounded-full animate-wave-1" />
                    <span className="w-1 bg-cyan-600 rounded-full animate-wave-2" />
                    <span className="w-1 bg-blue-500 rounded-full animate-wave-3" />
                  </span>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-semibold text-slate-800">
                    Loading transcript & audio telemetry...
                  </p>
                  <p className="text-xs text-slate-400">
                    Aligning word-level timestamps and speaker roles
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Mobile View Mode Switcher Strip (Visible on mobile/tablet < md screens) */}
                <div className="flex md:hidden items-center justify-between bg-white border border-slate-200/90 rounded-lg p-1 shadow-2xs shrink-0 overflow-x-auto no-scrollbar gap-1 mb-1">
                  {[
                    { id: "script" as const, label: "Script", icon: FileText, color: "text-blue-600" },
                    { id: "karaoke" as const, label: "Speeches", icon: Layers, color: "text-emerald-600" },
                    { id: "reader" as const, label: "Teleprompter", icon: Tv, color: "text-cyan-600" },
                    { id: "topics" as const, label: "Topics", icon: Compass, color: "text-sky-600" },
                    { id: "intelligence" as const, label: "Briefing", icon: Sparkles, color: "text-amber-600" },
                  ].map((mode) => {
                    const Icon = mode.icon;
                    const isActive = viewMode === mode.id;
                    return (
                      <button
                        key={mode.id}
                        type="button"
                        onClick={() => setViewMode(mode.id)}
                        className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 text-xs font-semibold rounded-md transition-all cursor-pointer whitespace-nowrap ${
                          isActive
                            ? "bg-slate-100 text-slate-900 shadow-2xs font-bold"
                            : "text-slate-500 hover:text-slate-800"
                        }`}
                      >
                        <Icon className={`w-3.5 h-3.5 ${isActive ? mode.color : "text-slate-400"}`} />
                        <span>{mode.label}</span>
                      </button>
                    );
                  })}
                </div>

                {viewMode === "intelligence" ? (
                  /* Executive AI Intelligence Briefing View */
                  <ExecutiveIntelligenceView
                    jobId={jobId}
                    filename={jobInfo?.filename}
                    duration={effectiveDuration}
                    currentTime={currentTime}
                    isPlaying={isPlaying}
                    onSeekTo={seekTo}
                    onTogglePlay={togglePlay}
                    speakers={transcript.speakers}
                    speakerStats={speakerStats}
                    wordCount={transcript.word_count}
                    detectedLanguage={transcript.detected_language}
                  />
                ) : viewMode === "topics" ? (
              /* Topic-Wise Video Flow Table View */
              <TopicFlowView
                topics={topics}
                jobId={jobId}
                jobInfo={jobInfo}
                currentTime={currentTime}
                onSeekTo={seekTo}
                duration={effectiveDuration}
              />
            ) : viewMode === "reader" ? (
              /* Teleprompter Reader View */
              <div className="bg-white border border-slate-200 rounded-lg p-8 shadow-sm space-y-6">
                <div className="flex justify-between items-center pb-3 border-b border-slate-100 text-xs text-slate-400 font-mono">
                  <span className="font-sans font-semibold text-slate-700">TELEPROMPTER READING MODE</span>
                  <span>{transcript.word_count.toLocaleString()} words &bull; ~{Math.max(1, Math.round(transcript.word_count / 180))} min read</span>
                </div>
                {visibleTurns.map((turn) => {
                  const isTurnActive = currentTime >= turn.startTime && currentTime <= turn.endTime;
                  return (
                    <div
                      key={turn.turnIndex}
                      ref={isTurnActive ? activeTurnRef : null}
                      className={`p-3.5 rounded-lg transition-all ${
                        isTurnActive
                          ? "bg-blue-50/80 text-blue-950 font-medium ring-1 ring-blue-500/20 shadow-2xs"
                          : "text-slate-800 hover:bg-slate-50/60"
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1.5 text-xs">
                        <span
                          className="font-bold uppercase tracking-wider"
                          style={{ color: turn.colorHex }}
                        >
                          {turn.displayName}
                        </span>
                        <span className="text-slate-400 font-mono text-[11px]">
                          [{formatTimeMinutesOnly(turn.startTime)}]
                        </span>
                      </div>
                      <p
                        className={`${currentFontClass} leading-relaxed cursor-pointer`}
                        onClick={() => seekTo(turn.startTime)}
                      >
                        {turn.text}
                      </p>
                    </div>
                  );
                })}
              </div>
            ) : viewMode === "script" ? (
              /* Dialogue Script Mode */
              <div className="space-y-4">
                {/* Modern Script Stage Header Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-slate-200/80 bg-white/60 p-3 rounded-lg border border-slate-200/60 backdrop-blur-xs">
                  <div className="flex items-center gap-2 text-xs text-slate-600">
                    <span className="font-semibold text-slate-900 bg-slate-100 px-2 py-0.5 rounded-lg border border-slate-200 font-mono">
                      {visibleTurns.length} turns
                    </span>
                    <span>&bull;</span>
                    <span className="font-mono text-slate-500">
                      {transcript.word_count.toLocaleString()} words
                    </span>
                    <span>&bull;</span>
                    <span className="text-slate-400 hidden sm:inline">
                      ~{Math.max(1, Math.round(transcript.word_count / 180))} min read
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setIsTemplateModalOpen(true)}
                      className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-900 border border-blue-200 px-3 py-1.5 rounded-lg bg-blue-50/70 hover:bg-blue-100/70 shadow-2xs transition-all active:scale-98"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                      <span>Script Templates</span>
                    </button>
                    <button
                      onClick={copyScriptToClipboard}
                      className="flex items-center gap-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-50 shadow-2xs transition-all active:scale-98"
                    >
                      {copiedScript ? (
                        <Check className="w-3.5 h-3.5 text-emerald-600" />
                      ) : (
                        <Copy className="w-3.5 h-3.5 text-slate-500" />
                      )}
                      <span>{copiedScript ? "Script Copied!" : "Copy Full Script"}</span>
                    </button>
                  </div>
                </div>

                {visibleTurns.map((turn) => {
                  const isTurnActive = currentTime >= turn.startTime && currentTime <= turn.endTime;
                  const isEditingThisTurn = editingTurnIndex === turn.turnIndex;
                  const isLoopingThisTurn = isLoopingTurn && loopTurnRange?.start === turn.startTime;

                  return (
                    <DialogueTurnCard
                      key={turn.turnIndex}
                      turn={turn}
                      isActive={isTurnActive}
                      isPlaying={isPlaying}
                      isLooping={isLoopingThisTurn}
                      isEditing={isEditingThisTurn}
                      editingText={editingTurnText}
                      fontClass={currentFontClass}
                      showConfidence={showConfidence}
                      currentTime={isTurnActive ? currentTime : -1}
                      copiedTurnIndex={copiedTurnIndex}
                      speakers={transcript.speakers}
                      activeTurnRef={activeTurnRef}
                      onSeekTo={seekTo}
                      onLoopTurn={loopTurn}
                      onCopyTurn={copyTurnToClipboard}
                      onStartEdit={handleStartEditTurn}
                      onCancelEdit={handleCancelEditTurn}
                      onChangeEditText={setEditingTurnText}
                      onSaveEditText={handleSaveTurnText}
                      onReassignSpeaker={handleReassignSpeaker}
                      onReassignAddressee={handleReassignAddressee}
                      onAddMarker={handleAddMarker}
                      topics={topics}
                    />
                  );
                })}
              </div>
            ) : (
              /* Karaoke Segments Mode */
              <div className="space-y-3">
                {transcript.segments.map((seg) => {
                  const isSegmentActive = currentTime >= seg.start_time && currentTime <= seg.end_time;
                  const rawName = speakerNames[seg.speaker_label || ""] || seg.speaker_label;
                  const speakerName = formatSpeakerDisplayName(rawName, seg.speaker_label);

                  return (
                    <SegmentCard
                      key={seg.id}
                      segment={seg}
                      isActive={isSegmentActive}
                      speakerName={speakerName}
                      fontClass={currentFontClass}
                      currentTime={isSegmentActive ? currentTime : -1}
                      isPlaying={isPlaying}
                      speakers={transcript.speakers}
                      onSeekTo={seekTo}
                      onReassignSpeaker={handleReassignSpeaker}
                      topics={topics}
                    />
                  );
                })}
              </div>
            )}
          </>
        )}
          </div>

          {/* Edge Re-open Button when Right Sidebar is Collapsed */}
          {!isRightSidebarOpen && (
            <button
              onClick={() => setIsRightSidebarOpen(true)}
              className="absolute right-0 top-1/2 -translate-y-1/2 bg-white/95 hover:bg-white backdrop-blur-md border-l border-y border-slate-200/90 pr-1.5 pl-2 py-3 rounded-l-lg shadow-md text-slate-500 hover:text-blue-600 transition-all flex flex-col items-center gap-1.5 z-20 group hover:shadow-lg active:scale-95 cursor-pointer"
              title="Open Studio Tools Inspector"
            >
              <PanelRightOpen className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
              <span className="text-[9px] font-bold uppercase tracking-widest [writing-mode:vertical-lr] text-slate-400 group-hover:text-slate-700">
                Tools
              </span>
            </button>
          )}
        </div>

        {/* RIGHT SIDEBAR: ADVANCED STUDIO INSPECTOR */}
        <StudioInspector
          isOpen={isRightSidebarOpen}
          onClose={() => setIsRightSidebarOpen(false)}
          activeTab={inspectorTab}
          onTabChange={setInspectorTab}
          markers={markers}
          newMarkerText={newMarkerText}
          newMarkerTag={newMarkerTag}
          onChangeMarkerText={setNewMarkerText}
          onChangeMarkerTag={setNewMarkerTag}
          onAddMarker={handleAddMarker}
          onDeleteMarker={handleDeleteMarker}
          onSeekTo={seekTo}
          currentTime={currentTime}
          isPlaying={isPlaying}
          onTogglePlay={togglePlay}
          audioAnalytics={audioAnalytics}
          totalWords={transcript?.word_count || 0}
          dialogueTurnsCount={dialogueTurns.length}
          topKeywords={topKeywords}
          onSelectKeyword={(word) => {
            setSearchQuery(word);
            setIsSearchOpen(true);
          }}
          abLoop={abLoop}
          onSetAbLoopPoint={(point, time) => {
            setAbLoop((prev) => ({ ...prev, [point]: time }));
          }}
          onToggleAbLoop={() => {
            if (abLoop.a !== null && abLoop.b !== null) {
              setAbLoop((prev) => ({ ...prev, active: !prev.active }));
              if (!abLoop.active && abLoop.a !== null) seekTo(abLoop.a);
            }
          }}
          onClearAbLoop={() => setAbLoop({ a: null, b: null, active: false })}
          skipStep={skipStep}
          onChangeSkipStep={setSkipStep}
          fontSize={fontSize}
          onFontSizeChange={setFontSize}
          showConfidence={showConfidence}
          onToggleConfidence={() => setShowConfidence(!showConfidence)}
          followPlayhead={followPlayhead}
          onToggleFollow={() => setFollowPlayhead(!followPlayhead)}
          onOpenTemplateModal={() => setIsTemplateModalOpen(true)}
          jobId={jobId}
          mediaStem={mediaStem}
          onIdentifySpeakers={handleSmartIdentifySpeakers}
          isIdentifyingSpeakers={isIdentifyingSpeakers}
          onOpenSpeakerModal={() => setIsSpeakerModalOpen(true)}
          audioRef={audioRef}
        />
      </div>

      {/* 3. SCRIPT TEMPLATES INTERACTIVE MODAL */}
      <TemplateModal
        isOpen={isTemplateModalOpen}
        onClose={() => setIsTemplateModalOpen(false)}
        jobId={jobId}
        templateStyle={templateStyle}
        onSelectStyle={setTemplateStyle}
        timestampStyle={timestampStyle}
        onChangeTimestampStyle={setTimestampStyle}
        speakerCase={speakerCase}
        onChangeSpeakerCase={setSpeakerCase}
        includeStats={includeStats}
        onToggleStats={setIncludeStats}
        renderedContent={renderedTemplateContent}
        copied={copiedTemplate}
        onCopy={copyTemplateContent}
        onDownload={downloadTemplateContent}
        turnsCount={dialogueTurns.length}
        totalWords={transcript?.word_count || dialogueTurns.reduce((acc, t) => acc + t.wordCount, 0)}
        mediaStem={mediaStem}
        duration={effectiveDuration || duration}
        speakersCount={transcript?.speakers?.length || 1}
      />

      {/* 4. SPEAKER MANAGEMENT MODAL */}
      <SpeakerModal
        isOpen={isSpeakerModalOpen}
        onClose={() => setIsSpeakerModalOpen(false)}
        speakerStats={speakerStats}
        speakerNames={speakerNames}
        onChangeSpeakerName={(label, name) => {
          setSpeakerNames((prev) => ({ ...prev, [label]: name }));
        }}
        onApply={handleBulkSpeakerRename}
        onIdentifySpeakers={handleSmartIdentifySpeakers}
        isIdentifyingSpeakers={isIdentifyingSpeakers}
      />

      {/* 5. MULTI-AUDIO TRACK MUX STUDIO MODAL */}
      <MuxModal
        isOpen={isMuxModalOpen}
        onClose={() => setIsMuxModalOpen(false)}
        jobId={jobId}
        mediaStem={mediaStem}
      />

      {/* 6. PREFERENCES & ENGINE MANAGER MODAL */}
      <PreferencesModal
        isOpen={isPreferencesOpen}
        onClose={() => setIsPreferencesOpen(false)}
      />
    </div>
  );
}

export default function StudioWorkspace() {
  return (
    <React.Suspense
      fallback={
        <div className="h-screen flex flex-col items-center justify-center bg-slate-50/80 p-4">
          <div className="flex flex-col items-center gap-3 p-6 rounded-lg bg-white border border-slate-200/80 shadow-md max-w-xs w-full text-center">
            <div className="relative flex items-center justify-center w-12 h-12 rounded-lg bg-blue-50 border border-blue-200/60 shadow-inner p-2">
              <img src="/tmux-icon.png" alt="TMUX" className="h-6 w-auto object-contain" />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-slate-900">TMUX Studio</h3>
              <p className="text-xs text-slate-500">Preparing workstation & media deck...</p>
            </div>
            <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden mt-1">
              <div className="h-full w-2/3 bg-blue-600 rounded-full animate-shimmer-sweep" />
            </div>
          </div>
        </div>
      }
    >
      <StudioContent />
    </React.Suspense>
  );
}
