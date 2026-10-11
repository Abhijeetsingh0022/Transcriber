"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity,
  Check,
  CheckCircle2,
  ChevronDown,
  Film,
  Headphones,
  Maximize2,
  Minimize2,
  Music2,
  Pause,
  PictureInPicture2,
  Play,
  Repeat,
  RotateCcw,
  SkipBack,
  SkipForward,
  Sparkles,
  Star,
  UploadCloud,
  Volume1,
  Volume2,
  VolumeX,
} from "lucide-react";

import { API_BASE } from "../utils";
import { MuxTrack } from "../types";

export interface VideoInfo {
  has_video: boolean;
  filepath?: string;
  filename?: string;
  file_size?: number;
  is_custom?: boolean;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  duration?: number | null;
  codec?: string | null;
  has_audio?: boolean;
  is_output?: boolean;
}

interface MuxVideoPlayerProps {
  jobId: string;
  videoInfo: VideoInfo | null;
  outputVideoInfo?: VideoInfo | null;
  hasOutputVideo?: boolean;
  activeMode?: "source" | "output";
  onModeChange?: (mode: "source" | "output") => void;
  isLoadingInfo?: boolean;
  auditionLabel?: string | null;
  isMuteAllAudio?: boolean;
  onTimeUpdate?: (currentTime: number) => void;
  onPlayStateChange?: (isPlaying: boolean) => void;
  onUploadVideoClick?: () => void;
  onResetVideoClick?: () => void;
  tracks?: MuxTrack[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string | null) => void;
  onSetDefaultTrack?: (trackId: string) => void;
  className?: string;
  playerVolume?: number;
  onVolumeChange?: (volume: number) => void;
  isPlayerMuted?: boolean;
  onToggleMute?: () => void;
}

const SPEED_PRESETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0];

function formatTime(seconds: number): string {
  if (isNaN(seconds) || seconds < 0) return "00:00.000";
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  const p = (n: number, w: number) => String(n).padStart(w, "0");
  if (hrs > 0) return `${p(hrs, 2)}:${p(mins, 2)}:${p(secs, 2)}.${p(ms, 3)}`;
  return `${p(mins, 2)}:${p(secs, 2)}.${p(ms, 3)}`;
}

export function MuxVideoPlayer({
  jobId,
  videoInfo,
  outputVideoInfo,
  hasOutputVideo = false,
  activeMode,
  onModeChange,
  isLoadingInfo = false,
  auditionLabel,
  isMuteAllAudio = false,
  onTimeUpdate,
  onPlayStateChange,
  onUploadVideoClick,
  onResetVideoClick,
  tracks,
  selectedTrackId = null,
  onSelectTrack,
  onSetDefaultTrack,
  className = "",
  playerVolume,
  onVolumeChange,
  isPlayerMuted,
  onToggleMute,
}: MuxVideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const scrubberRef = useRef<HTMLDivElement | null>(null);
  const hideControlsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [internalMode, setInternalMode] = useState<"source" | "output">("source");
  const mode = activeMode ?? internalMode;
  const setMode = (m: "source" | "output") => {
    setInternalMode(m);
    onModeChange?.(m);
    videoRef.current?.pause();
    setIsPlaying(false);
    onPlayStateChange?.(false);
  };
  const isOutputMode = mode === "output";
  const activeInfo = isOutputMode && outputVideoInfo ? outputVideoInfo : videoInfo;

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [bufferedPct, setBufferedPct] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);
  const [localVolume, setLocalVolume] = useState(1.0);
  const [localMuted, setLocalMuted] = useState(false);
  const volume = playerVolume !== undefined ? playerVolume : localVolume;
  const isMuted = isPlayerMuted !== undefined ? isPlayerMuted : localMuted;
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isPiPActive, setIsPiPActive] = useState(false);
  const [isScrubbing, setIsScrubbing] = useState(false);
  const [hoverTime, setHoverTime] = useState<number | null>(null);
  const [hoverPositionPct, setHoverPositionPct] = useState<number>(0);
  const [controlsVisible, setControlsVisible] = useState(true);
  const [isLooping, setIsLooping] = useState(false);
  const [loopRange, setLoopRange] = useState<{ start: number; end: number } | null>(null);
  const [centerRipple, setCenterRipple] = useState<{ active: boolean; type: "play" | "pause" } | null>(null);
  const [isVolumeHovered, setIsVolumeHovered] = useState(false);
  const [isVolumeDragging, setIsVolumeDragging] = useState(false);
  const [isSpeedMenuOpen, setIsSpeedMenuOpen] = useState(false);
  const [isTrackMenuOpen, setIsTrackMenuOpen] = useState(false);
  const [showRemainingTime, setShowRemainingTime] = useState(false);
  const trackMenuRef = useRef<HTMLDivElement | null>(null);
  const speedMenuRef = useRef<HTMLDivElement | null>(null);
  const clickTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [hudMessage, setHudMessage] = useState<string | null>(null);
  const hudTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showHud = (msg: string) => {
    setHudMessage(msg);
    if (hudTimerRef.current) clearTimeout(hudTimerRef.current);
    hudTimerRef.current = setTimeout(() => setHudMessage(null), 1800);
  };

  const currentTrack = tracks?.find((t) => t.id === selectedTrackId);

  const handleTrackSelect = (trackId: string | null) => {
    setIsTrackMenuOpen(false);
    onSelectTrack?.(trackId);
    const chosen = tracks?.find((t) => t.id === trackId);
    showHud(`Track: ${chosen ? chosen.label : isOutputMode ? "Muxed Output" : "Source Video"}`);
  };

  const cycleTrack = useCallback(() => {
    if (!tracks || tracks.length === 0) return;
    const opts: (string | null)[] = [null, ...tracks.map((t) => t.id)];
    const idx = opts.indexOf(selectedTrackId ?? null);
    handleTrackSelect(opts[(idx + 1) % opts.length]);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tracks, selectedTrackId, isOutputMode]);

  useEffect(() => {
    if (!isTrackMenuOpen) return;
    const h = (e: MouseEvent) => {
      if (trackMenuRef.current && !trackMenuRef.current.contains(e.target as Node))
        setIsTrackMenuOpen(false);
    };
    window.addEventListener("mousedown", h);
    return () => window.removeEventListener("mousedown", h);
  }, [isTrackMenuOpen]);

  useEffect(() => {
    if (!isSpeedMenuOpen) return;
    const h = (e: MouseEvent) => {
      if (speedMenuRef.current && !speedMenuRef.current.contains(e.target as Node))
        setIsSpeedMenuOpen(false);
    };
    window.addEventListener("mousedown", h);
    return () => window.removeEventListener("mousedown", h);
  }, [isSpeedMenuOpen]);

  const isStemActive = Boolean(selectedTrackId || auditionLabel);
  const isAudiblyMuted = isMuted || (!isStemActive && isMuteAllAudio);
  const isVideoTagMuted = isStemActive || isAudiblyMuted;
  const fps = activeInfo?.fps && activeInfo.fps > 0 ? activeInfo.fps : 30;
  const frameDuration = 1 / fps;
  const streamUrl = isOutputMode
    ? `${API_BASE}/jobs/${jobId}/mux/output/stream`
    : `${API_BASE}/jobs/${jobId}/mux/video/stream`;

  const triggerRipple = (type: "play" | "pause") => {
    setCenterRipple({ active: true, type });
    setTimeout(() => setCenterRipple(null), 450);
  };

  const updateBuffered = useCallback(() => {
    if (!videoRef.current || duration <= 0) return;
    const b = videoRef.current.buffered;
    if (b.length > 0)
      setBufferedPct(Math.min(100, (b.end(b.length - 1) / duration) * 100));
  }, [duration]);

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current
        .play()
        .then(() => { setIsPlaying(true); onPlayStateChange?.(true); triggerRipple("play"); })
        .catch(() => {});
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
      onPlayStateChange?.(false);
      triggerRipple("pause");
    }
  }, [onPlayStateChange]);

  const stepFrame = useCallback(
    (direction: 1 | -1) => {
      if (!videoRef.current) return;
      if (!videoRef.current.paused) {
        videoRef.current.pause();
        setIsPlaying(false);
        onPlayStateChange?.(false);
      }
      const t = Math.max(
        0,
        Math.min(videoRef.current.currentTime + direction * frameDuration, duration)
      );
      videoRef.current.currentTime = t;
      setCurrentTime(t);
      onTimeUpdate?.(t);
      showHud(direction > 0 ? "+1 Frame" : "-1 Frame");
    },
    [duration, frameDuration, onPlayStateChange, onTimeUpdate]
  );

  const jumpSeconds = useCallback(
    (seconds: number) => {
      if (!videoRef.current) return;
      const t = Math.max(0, Math.min(videoRef.current.currentTime + seconds, duration));
      videoRef.current.currentTime = t;
      setCurrentTime(t);
      onTimeUpdate?.(t);
      showHud(`${seconds > 0 ? "+" : ""}${seconds}s`);
    },
    [duration, onTimeUpdate]
  );

  const togglePiP = useCallback(async () => {
    if (!videoRef.current) return;
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const doc = document as any;
      if (doc.pictureInPictureElement) {
        await doc.exitPictureInPicture?.();
        setIsPiPActive(false);
      } else if (videoRef.current.requestPictureInPicture) {
        await videoRef.current.requestPictureInPicture();
        setIsPiPActive(true);
      }
    } catch { /* silent */ }
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const doc = document as any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const elem = containerRef.current as any;
    const isFs = !!(doc.fullscreenElement || doc.webkitFullscreenElement || doc.mozFullScreenElement || doc.msFullscreenElement);
    if (!isFullscreen && !isFs) {
      const req = elem.requestFullscreen ?? elem.webkitRequestFullscreen ?? elem.mozRequestFullScreen ?? elem.msRequestFullscreen;
      if (req) {
        try {
          const p = req.call(elem);
          if (p && typeof p.then === "function") {
            p.then(() => setIsFullscreen(true)).catch(() => setIsFullscreen(true));
          } else {
            setIsFullscreen(true);
          }
        } catch {
          setIsFullscreen(true);
        }
      } else {
        setIsFullscreen(true);
      }
    } else {
      const exit = doc.exitFullscreen ?? doc.webkitExitFullscreen ?? doc.mozCancelFullScreen ?? doc.msExitFullscreen;
      if (exit && isFs) {
        try { exit.call(doc); } catch { /* silent */ }
      }
      setIsFullscreen(false);
    }
  }, [isFullscreen]);

  useEffect(() => {
    const h = () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const doc = document as any;
      const isFs = !!(doc.fullscreenElement || doc.webkitFullscreenElement || doc.mozFullScreenElement || doc.msFullscreenElement);
      setIsFullscreen(isFs);
    };
    document.addEventListener("fullscreenchange", h);
    document.addEventListener("webkitfullscreenchange", h);
    document.addEventListener("mozfullscreenchange", h);
    return () => {
      document.removeEventListener("fullscreenchange", h);
      document.removeEventListener("webkitfullscreenchange", h);
      document.removeEventListener("mozfullscreenchange", h);
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onEnter = () => setIsPiPActive(true);
    const onLeave = () => setIsPiPActive(false);
    video.addEventListener("enterpictureinpicture", onEnter);
    video.addEventListener("leavepictureinpicture", onLeave);
    return () => {
      video.removeEventListener("enterpictureinpicture", onEnter);
      video.removeEventListener("leavepictureinpicture", onLeave);
    };
  }, []);

  const handleMouseMoveContainer = () => {
    setControlsVisible(true);
    if (hideControlsTimerRef.current) clearTimeout(hideControlsTimerRef.current);
    if (isPlaying)
      hideControlsTimerRef.current = setTimeout(() => {
        setControlsVisible(false);
        setIsSpeedMenuOpen(false);
      }, 2500);
  };

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.isContentEditable ||
          Boolean(t.closest("input, textarea, [contenteditable='true']")))
      ) {
        return;
      }
      if (e.key === "Escape" && isFullscreen) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const doc = document as any;
        const exit = doc.exitFullscreen ?? doc.webkitExitFullscreen ?? doc.mozCancelFullScreen ?? doc.msExitFullscreen;
        if (exit) { try { exit.call(doc); } catch { /* silent */ } }
        setIsFullscreen(false);
      } else if (e.code === "Space" || e.key === "k" || e.key === "K") {
        e.preventDefault();
        togglePlay();
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        e.shiftKey ? jumpSeconds(-5) : stepFrame(-1);
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        e.shiftKey ? jumpSeconds(5) : stepFrame(1);
      } else if (e.key === "j" || e.key === "J") {
        e.preventDefault();
        jumpSeconds(-5);
      } else if (e.key === "l" || e.key === "L") {
        e.preventDefault();
        if (e.shiftKey) {
          toggleLoop();
        } else {
          jumpSeconds(5);
        }
      } else if (e.key === "m" || e.key === "M") {
        e.preventDefault();
        if (onToggleMute) onToggleMute();
        else setLocalMuted((p) => !p);
      } else if (e.key === "f" || e.key === "F") {
        e.preventDefault();
        toggleFullscreen();
      } else if (e.key === "p" || e.key === "P") {
        e.preventDefault();
        togglePiP();
      } else if (e.key === "t" || e.key === "T") {
        e.preventDefault();
        cycleTrack();
      } else if (e.key === "Home") {
        e.preventDefault();
        if (videoRef.current) {
          videoRef.current.currentTime = 0;
          setCurrentTime(0);
          onTimeUpdate?.(0);
          showHud("00:00.000");
        }
      } else if (e.key === "End") {
        e.preventDefault();
        if (videoRef.current && duration > 0) {
          videoRef.current.currentTime = duration;
          setCurrentTime(duration);
          onTimeUpdate?.(duration);
        }
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [jumpSeconds, stepFrame, toggleFullscreen, togglePlay, togglePiP, cycleTrack, isFullscreen, onToggleMute, duration, onTimeUpdate]);

  const toggleLoop = () => {
    if (isLooping) {
      setIsLooping(false);
      setLoopRange(null);
      showHud("Loop Cleared");
    } else {
      const start = Math.max(0, currentTime - 1.5);
      const end = Math.min(duration, currentTime + 2.5);
      setLoopRange({ start, end });
      setIsLooping(true);
      if (videoRef.current) videoRef.current.currentTime = start;
      showHud("Loop Active (4s)");
    }
  };

  const handleTimeUpdate = () => {
    if (!videoRef.current) return;
    const t = videoRef.current.currentTime;
    if (isLooping && loopRange && t >= loopRange.end) {
      videoRef.current.currentTime = loopRange.start;
      setCurrentTime(loopRange.start);
      onTimeUpdate?.(loopRange.start);
      return;
    }
    setCurrentTime(t);
    onTimeUpdate?.(t);
    updateBuffered();
  };

  const handleScrubberMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!scrubberRef.current || duration <= 0 || !videoRef.current) return;
    setIsScrubbing(true);
    const rect = scrubberRef.current.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    const t = ratio * duration;
    videoRef.current.currentTime = t;
    setCurrentTime(t);
    onTimeUpdate?.(t);
    setHoverPositionPct(ratio * 100);
    setHoverTime(t);
  };

  const handleScrubberMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!scrubberRef.current || duration <= 0) return;
    const rect = scrubberRef.current.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setHoverPositionPct(ratio * 100);
    setHoverTime(ratio * duration);
  };

  useEffect(() => {
    if (!isScrubbing) return;
    const handleWindowMouseMove = (e: MouseEvent) => {
      if (!scrubberRef.current || duration <= 0 || !videoRef.current) return;
      const rect = scrubberRef.current.getBoundingClientRect();
      const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const t = ratio * duration;
      videoRef.current.currentTime = t;
      setCurrentTime(t);
      onTimeUpdate?.(t);
      setHoverPositionPct(ratio * 100);
      setHoverTime(t);
    };
    const handleWindowMouseUp = () => setIsScrubbing(false);
    window.addEventListener("mousemove", handleWindowMouseMove);
    window.addEventListener("mouseup", handleWindowMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleWindowMouseMove);
      window.removeEventListener("mouseup", handleWindowMouseUp);
    };
  }, [isScrubbing, duration, onTimeUpdate]);

  const handleVolumeChange = (v: number) => {
    if (onVolumeChange) {
      onVolumeChange(v);
    } else {
      setLocalVolume(v);
      if (videoRef.current) {
        videoRef.current.volume = v;
        if (v === 0) setLocalMuted(true);
        else if (localMuted) setLocalMuted(false);
      }
    }
  };

  useEffect(() => {
    if (!videoRef.current) return;
    if (isStemActive) {
      videoRef.current.muted = true;
    } else {
      videoRef.current.muted = isAudiblyMuted;
      videoRef.current.volume = volume;
    }
  }, [isStemActive, isAudiblyMuted, volume]);

  const handleSpeedSelect = (s: number) => {
    setPlaybackSpeed(s);
    if (videoRef.current) videoRef.current.playbackRate = s;
    setIsSpeedMenuOpen(false);
    showHud(`Speed: ${s}x`);
  };

  const cycleSpeed = () => {
    const idx = SPEED_PRESETS.indexOf(playbackSpeed);
    handleSpeedSelect(SPEED_PRESETS[(idx + 1) % SPEED_PRESETS.length]);
  };

  const handleViewportClick = () => {
    if (clickTimerRef.current) {
      clearTimeout(clickTimerRef.current);
      clickTimerRef.current = null;
      toggleFullscreen();
    } else {
      clickTimerRef.current = setTimeout(() => {
        togglePlay();
        clickTimerRef.current = null;
      }, 220);
    }
  };

  const playedPct = duration > 0 ? (currentTime / duration) * 100 : 0;
  const loopStartPct = loopRange && duration > 0 ? (loopRange.start / duration) * 100 : 0;
  const loopEndPct = loopRange && duration > 0 ? (loopRange.end / duration) * 100 : 0;

  // ── Empty State ──
  if (!isLoadingInfo && (!videoInfo || !videoInfo.has_video)) {
    return (
      <div className={`bg-slate-50/70 backdrop-blur-md flex flex-col items-center justify-center p-8 text-center relative overflow-hidden border-b border-slate-200/80 ${className}`}>
        <div className="relative z-10 space-y-4">
          <div className="w-14 h-14 mx-auto rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 shadow-sm">
            <Film className="w-7 h-7 text-emerald-600" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800">No Video Attached</h4>
            <p className="text-xs text-slate-500 mt-1.5 max-w-xs mx-auto leading-relaxed">
              Attach a video to preview visuals and audition synchronized audio stems.
            </p>
          </div>
          <button
            type="button"
            onClick={onUploadVideoClick}
            className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all cursor-pointer active:scale-95"
          >
            <UploadCloud className="w-3.5 h-3.5" />
            Upload Video
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      onMouseMove={handleMouseMoveContainer}
      className={`flex flex-col relative select-none transition-all ${
        isFullscreen
          ? "fixed inset-0 w-screen h-screen z-[99999] rounded-none border-0 overflow-hidden bg-slate-950/95 backdrop-blur-2xl"
          : "overflow-hidden bg-white/70 backdrop-blur-2xl border-b border-slate-200/80 shadow-2xs"
      } ${className}`}
    >
      {/* ── TOP TOOLBAR (White Transparent Glass) ── */}
      <div
        className={`shrink-0 px-3.5 py-2.5 bg-white/80 backdrop-blur-2xl border-b border-slate-200/80 flex items-center justify-between gap-2 text-xs z-30 transition-opacity duration-200 shadow-2xs ${
          controlsVisible || !isFullscreen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Identity */}
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-6.5 h-6.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 backdrop-blur-md flex items-center justify-center shrink-0 shadow-2xs">
            <Film className="w-3.5 h-3.5 text-emerald-600" />
          </div>
          <div className="flex items-center gap-2 min-w-0">
            <span
              className="font-semibold text-slate-800 truncate max-w-[160px] sm:max-w-[260px]"
              title={activeInfo?.filename}
            >
              {isOutputMode
                ? outputVideoInfo?.filename || "Mux Output"
                : videoInfo?.filename || "Video Monitor"}
            </span>
            {isOutputMode ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 border border-emerald-500/25 font-bold flex items-center gap-1.5 shrink-0 backdrop-blur-md">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Muxed Output
              </span>
            ) : videoInfo?.is_custom ? (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-700 border border-blue-500/25 font-semibold shrink-0 backdrop-blur-md">
                Custom
              </span>
            ) : (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-500/10 text-slate-600 border border-slate-500/20 shrink-0 backdrop-blur-md">
                Source
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0">
          {hasOutputVideo && (
            <div className="flex items-center rounded-lg bg-slate-100/80 backdrop-blur-xl p-0.5 border border-slate-200/80 text-[11px] font-semibold shadow-2xs">
              <button
                type="button"
                onClick={() => setMode("source")}
                className={`px-2.5 py-0.5 rounded-lg transition-all cursor-pointer ${
                  mode === "source"
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-800"
                }`}
              >
                Source
              </button>
              <button
                type="button"
                onClick={() => setMode("output")}
                className={`flex items-center gap-1 px-2.5 py-0.5 rounded-lg transition-all cursor-pointer ${
                  mode === "output"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "text-emerald-700 hover:text-emerald-800"
                }`}
              >
                <CheckCircle2 className="w-3 h-3" />
                Output
              </button>
            </div>
          )}

          {activeInfo?.width && activeInfo?.height && (
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-mono text-slate-500 bg-white/80 backdrop-blur-xl px-2.5 py-0.5 rounded-lg border border-slate-200/80 shadow-2xs">
              {activeInfo.width}x{activeInfo.height}
              <span className="text-slate-300">·</span>
              {fps}fps
              {activeInfo.codec && (
                <>
                  <span className="text-slate-300">·</span>
                  <span className="uppercase">{activeInfo.codec}</span>
                </>
              )}
            </span>
          )}

          {!isOutputMode && videoInfo?.is_custom && onResetVideoClick && (
            <button
              type="button"
              onClick={onResetVideoClick}
              className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg text-slate-600 hover:text-rose-600 bg-white/80 hover:bg-rose-50 backdrop-blur-xl border border-slate-200/80 transition-colors cursor-pointer shadow-2xs active:scale-95"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}

          {!isOutputMode && onUploadVideoClick && (
            <button
              type="button"
              onClick={onUploadVideoClick}
              className="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-lg bg-white/80 hover:bg-white backdrop-blur-xl text-slate-700 hover:text-slate-900 border border-slate-200/80 transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              <UploadCloud className="w-3 h-3 text-slate-500" />
              Replace
            </button>
          )}
        </div>
      </div>

      {/* ── VIDEO VIEWPORT ── */}
      <div
        className={`w-full bg-slate-950 flex items-center justify-center select-none cursor-pointer group relative overflow-hidden ${
          isFullscreen ? "flex-1 min-h-0" : "h-[256px] sm:h-[296px] md:h-[336px]"
        }`}
        onClick={handleViewportClick}
      >
        <video
          ref={videoRef}
          src={streamUrl}
          preload="metadata"
          muted={isVideoTagMuted}
          className="w-full h-full object-contain pointer-events-none"
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={() => {
            if (videoRef.current) {
              setDuration(videoRef.current.duration);
              updateBuffered();
            }
          }}
          onProgress={updateBuffered}
          onEnded={() => { setIsPlaying(false); onPlayStateChange?.(false); }}
        />

        {/* Status badges — White Transparent Glass */}
        {isOutputMode && !currentTrack ? (
          <div className="absolute top-3 left-3 pointer-events-none z-20">
            <span className="text-[10px] font-mono font-bold tracking-wide px-3 py-1 rounded-lg bg-white/85 text-emerald-800 shadow-xl flex items-center gap-1.5 backdrop-blur-xl border border-white/80">
              <Sparkles className="w-3 h-3 text-emerald-600" />
              FINAL MUXED OUTPUT
            </span>
          </div>
        ) : (currentTrack || auditionLabel) ? (
          <div className="absolute top-3 left-3 pointer-events-none z-20">
            <span className="text-[10px] font-mono font-bold tracking-wide px-3 py-1 rounded-lg bg-white/85 text-slate-800 shadow-xl flex items-center gap-1.5 backdrop-blur-xl border border-white/80">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <Headphones className="w-3 h-3 text-emerald-600" />
              TRACK: {(currentTrack?.label || auditionLabel || "STEM").toUpperCase()}
              {currentTrack?.is_default ? " ★" : ""}
            </span>
          </div>
        ) : null}

        {isLooping && loopRange && (
          <div className="absolute top-3 right-3 pointer-events-none z-20">
            <span className="text-[10px] font-mono font-bold px-2.5 py-1 rounded-lg bg-white/85 text-amber-800 shadow-xl flex items-center gap-1 backdrop-blur-xl border border-white/80">
              <Repeat className="w-2.5 h-2.5 text-amber-600" />
              LOOP {formatTime(loopRange.start)} - {formatTime(loopRange.end)}
            </span>
          </div>
        )}

        {hudMessage && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-40 animate-in fade-in zoom-in-95 duration-150">
            <div className="px-4 py-2.5 rounded-lg bg-white/90 border border-white/90 backdrop-blur-2xl shadow-2xl flex items-center gap-2.5 text-slate-900">
              <Headphones className="w-4 h-4 text-emerald-600" />
              <span className="text-xs font-semibold tracking-wide font-mono">{hudMessage}</span>
            </div>
          </div>
        )}

        {centerRipple?.active && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
            <div className="w-20 h-20 rounded-full bg-white/40 backdrop-blur-md border border-white/80 text-slate-900 flex items-center justify-center shadow-2xl animate-ping">
              {centerRipple.type === "play" ? (
                <Play className="w-8 h-8 fill-emerald-600 text-emerald-600 ml-1" />
              ) : (
                <Pause className="w-8 h-8 fill-amber-600 text-amber-600" />
              )}
            </div>
          </div>
        )}

        {!isPlaying && (
          <div className="absolute inset-0 bg-slate-950/20 backdrop-blur-[2px] flex items-center justify-center z-10">
            <div className="w-20 h-20 rounded-full bg-white/75 hover:bg-white/95 text-slate-900 flex items-center justify-center shadow-[0_12px_40px_rgba(0,0,0,0.2),inset_0_1px_2px_rgba(255,255,255,1)] ring-1 ring-white/80 hover:ring-white border border-white/70 transition-all duration-300 hover:scale-105 active:scale-95 group/play backdrop-blur-2xl">
              <Play className="w-8 h-8 fill-emerald-600 text-emerald-600 ml-1 drop-shadow-xs group-hover/play:scale-110 transition-transform" />
            </div>
          </div>
        )}
      </div>

      {/* ── SCRUBBER (White Transparent Glass) ── */}
      <div
        ref={scrubberRef}
        onMouseDown={handleScrubberMouseDown}
        onMouseMove={handleScrubberMouseMove}
        onMouseLeave={() => setHoverTime(null)}
        className={`shrink-0 relative h-2 hover:h-2.5 bg-slate-200/80 hover:bg-slate-200 cursor-pointer select-none transition-all duration-100 z-30 backdrop-blur-md ${
          controlsVisible || !isFullscreen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        <div
          className="absolute inset-y-0 left-0 bg-slate-300/80 pointer-events-none transition-all"
          style={{ width: `${bufferedPct}%` }}
        />
        {isLooping && loopRange && (
          <div
            className="absolute inset-y-0 bg-amber-400/35 border-l border-r border-amber-500 pointer-events-none"
            style={{ left: `${loopStartPct}%`, width: `${Math.max(1, loopEndPct - loopStartPct)}%` }}
          />
        )}
        <div
          className="absolute inset-y-0 left-0 bg-gradient-to-r from-emerald-500 to-teal-500 pointer-events-none shadow-xs"
          style={{ width: `${playedPct}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 -ml-2 w-4 h-4 bg-white shadow-md ring-2 ring-emerald-500 rounded-full pointer-events-none group-hover:scale-125 transition-transform"
          style={{ left: `${playedPct}%` }}
        />
        {hoverTime !== null && (
          <div
            className="absolute -top-8 -translate-x-1/2 pointer-events-none z-40"
            style={{ left: `${hoverPositionPct}%` }}
          >
            <div className="bg-white/95 backdrop-blur-md text-slate-800 font-mono text-[10px] font-bold px-2 py-0.5 rounded-lg border border-slate-200 shadow-xl">
              {formatTime(hoverTime)}
            </div>
          </div>
        )}
      </div>

      {/* ── TRANSPORT CONTROLS (White Transparent Glass) ── */}
      <div
        className={`shrink-0 px-3.5 py-2.5 bg-white/80 backdrop-blur-2xl border-t border-slate-200/80 flex items-center justify-between gap-2 z-30 transition-opacity duration-200 shadow-2xs ${
          controlsVisible || !isFullscreen ? "opacity-100" : "opacity-0 pointer-events-none"
        }`}
      >
        {/* Left: Playback controls */}
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => stepFrame(-1)}
            className="p-1.5 rounded-lg bg-white/80 hover:bg-white backdrop-blur-xl text-slate-600 hover:text-slate-900 border border-slate-200/80 shadow-2xs active:scale-95 transition-all cursor-pointer"
            title="-1 Frame (Left Arrow)"
          >
            <SkipBack className="w-3.5 h-3.5" />
          </button>

          <button
            type="button"
            onClick={togglePlay}
            className={`px-3.5 py-1.5 rounded-lg font-semibold text-xs flex items-center gap-1.5 active:scale-95 transition-all cursor-pointer shadow-xs ${
              isPlaying
                ? "bg-amber-500/15 hover:bg-amber-500/25 text-amber-900 border border-amber-400/40 backdrop-blur-xl"
                : "bg-emerald-600 hover:bg-emerald-700 text-white border border-emerald-600"
            }`}
            title="Play / Pause (Space)"
          >
            {isPlaying ? (
              <><Pause className="w-3.5 h-3.5 fill-current" /><span>Pause</span></>
            ) : (
              <><Play className="w-3.5 h-3.5 fill-current ml-0.5" /><span>Play</span></>
            )}
          </button>

          <button
            type="button"
            onClick={() => stepFrame(1)}
            className="p-1.5 rounded-lg bg-white/80 hover:bg-white backdrop-blur-xl text-slate-600 hover:text-slate-900 border border-slate-200/80 shadow-2xs active:scale-95 transition-all cursor-pointer"
            title="+1 Frame (Right Arrow)"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>

          {/* Timecode */}
          <button
            type="button"
            onClick={() => setShowRemainingTime((p) => !p)}
            className="ml-1 font-mono text-xs px-2.5 py-1 rounded-lg bg-slate-50/90 hover:bg-slate-100/90 backdrop-blur-sm border border-slate-200/90 flex items-center gap-2 text-slate-800 shadow-2xs cursor-pointer transition-colors"
            title="Click to toggle remaining / total duration"
          >
            {isPlaying ? (
              <div className="flex items-end gap-0.5 h-3 w-2.5">
                <span className="w-0.5 bg-emerald-500 rounded-full animate-bounce h-full" style={{ animationDelay: "0ms" }} />
                <span className="w-0.5 bg-teal-500 rounded-full animate-bounce h-2/3" style={{ animationDelay: "150ms" }} />
                <span className="w-0.5 bg-sky-500 rounded-full animate-bounce h-4/5" style={{ animationDelay: "75ms" }} />
              </div>
            ) : (
              <Activity className="w-3 h-3 text-slate-400" />
            )}
            <span className="text-emerald-700 font-bold">{formatTime(currentTime)}</span>
            <span className="text-slate-300 font-light">/</span>
            <span className="text-slate-500 font-medium">
              {showRemainingTime ? `-${formatTime(Math.max(0, duration - currentTime))}` : formatTime(duration)}
            </span>
            <span className="text-[10px] text-slate-400 hidden sm:inline border-l border-slate-200 pl-1.5">
              F {Math.floor(currentTime * fps)}
            </span>
          </button>
        </div>

        {/* Right: Tools */}
        <div className="flex items-center gap-1.5">
          {/* A-B Loop */}
          <button
            type="button"
            onClick={toggleLoop}
            className={`p-1.5 rounded-lg border backdrop-blur-xl transition-all cursor-pointer shadow-2xs ${
              isLooping
                ? "bg-amber-500/15 text-amber-800 border-amber-400/50"
                : "bg-white/80 hover:bg-white text-slate-600 hover:text-slate-900 border-slate-200/80"
            }`}
            title="A-B Loop (L)"
          >
            <Repeat className="w-3.5 h-3.5" />
          </button>

          {/* Track Selector */}
          <div ref={trackMenuRef} className="relative">
            <button
              type="button"
              onClick={() => setIsTrackMenuOpen((p) => !p)}
              className={`flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1.5 rounded-lg border backdrop-blur-xl transition-all cursor-pointer shadow-2xs ${
                isTrackMenuOpen || selectedTrackId
                  ? "bg-emerald-500/10 text-emerald-800 border-emerald-500/30 hover:bg-emerald-500/20"
                  : "bg-white/80 hover:bg-white text-slate-700 border-slate-200/80"
              }`}
              title="Switch audio track (T to cycle)"
            >
              <Headphones className="w-3.5 h-3.5 text-emerald-600" />
              <span className="font-mono text-slate-400 hidden sm:inline">Track:</span>
              <span className="max-w-[70px] sm:max-w-[110px] truncate">
                {currentTrack ? currentTrack.label : isOutputMode ? "Muxed" : "Source"}
              </span>
              <ChevronDown
                className={`w-3 h-3 text-slate-400 transition-transform ${isTrackMenuOpen ? "rotate-180" : ""}`}
              />
            </button>

            {isTrackMenuOpen && (
              <div className="absolute bottom-full right-0 sm:left-0 sm:right-auto mb-2 w-72 sm:w-80 bg-white/95 border border-slate-200/90 rounded-lg shadow-2xl p-2 z-50 backdrop-blur-2xl animate-in fade-in zoom-in-95 duration-150">
                <div className="flex items-center justify-between px-2 py-1.5 mb-1 border-b border-slate-100">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-800">
                    <Music2 className="w-3.5 h-3.5 text-emerald-600" />
                    Select Audio Track
                  </div>
                  <span className="text-[10px] font-mono text-slate-500 bg-slate-50 px-1.5 py-0.5 rounded-lg border border-slate-200">
                    T to cycle
                  </span>
                </div>
                <div className="space-y-0.5 max-h-60 overflow-y-auto">
                  <div
                    onClick={() => handleTrackSelect(null)}
                    className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors text-xs ${
                      selectedTrackId === null
                        ? "bg-emerald-50 text-emerald-900 border border-emerald-200 font-semibold"
                        : "hover:bg-slate-50 text-slate-700 border border-transparent"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-4 h-4 flex items-center justify-center shrink-0">
                        {selectedTrackId === null && <Check className="w-3.5 h-3.5 text-emerald-600" />}
                      </div>
                      <div className="min-w-0">
                        <div className="font-medium text-slate-800">
                          {isOutputMode ? "Rendered Mux Output" : "Source Video Audio"}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {isOutputMode ? "Default muxed audio stream" : "Embedded audio from video"}
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-lg bg-slate-100 text-slate-600 border border-slate-200 shrink-0 ml-2">
                      Primary
                    </span>
                  </div>

                  {tracks && tracks.length > 0 && (
                    <div className="pt-1">
                      <div className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                        Configured Stems ({tracks.length})
                      </div>
                      {tracks.map((t, idx) => {
                        const isSel = selectedTrackId === t.id;
                        return (
                          <div
                            key={t.id}
                            onClick={() => handleTrackSelect(t.id)}
                            className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition-colors text-xs group ${
                              isSel
                                ? "bg-emerald-50 text-emerald-900 border border-emerald-200 font-semibold"
                                : "hover:bg-slate-50 text-slate-700 border border-transparent"
                            }`}
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <div className="w-4 h-4 flex items-center justify-center shrink-0">
                                {isSel ? (
                                  <Check className="w-3.5 h-3.5 text-emerald-600" />
                                ) : (
                                  <span className="font-mono text-[10px] text-slate-400">#{idx + 1}</span>
                                )}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="font-medium text-slate-800 truncate flex items-center gap-1.5">
                                  {t.label}
                                  {t.is_default && (
                                    <span className="text-[9px] font-mono px-1 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200 font-bold">
                                      DEFAULT
                                    </span>
                                  )}
                                </div>
                                <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1.5">
                                  <span className="uppercase text-slate-600 font-semibold">{t.language}</span>
                                  <span>·</span>
                                  <span>{t.channels === 2 ? "Stereo" : "Mono"}</span>
                                  <span>·</span>
                                  <span>{t.sample_rate ? `${t.sample_rate}Hz` : "44.1kHz"}</span>
                                </div>
                              </div>
                            </div>
                            {onSetDefaultTrack && (
                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onSetDefaultTrack(t.id);
                                  showHud(`Default: ${t.label}`);
                                }}
                                className={`p-1 rounded-lg cursor-pointer shrink-0 ml-1 transition-colors ${
                                  t.is_default
                                    ? "text-amber-500"
                                    : "text-slate-300 hover:text-amber-500 opacity-0 group-hover:opacity-100"
                                }`}
                              >
                                <Star className={`w-3.5 h-3.5 ${t.is_default ? "fill-amber-500" : ""}`} />
                              </button>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {(!tracks || tracks.length === 0) && (
                    <div className="p-3 text-center text-xs text-slate-500 italic">
                      No audio stems configured.
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Volume & Audio (Inline Seamless Control) */}
          <div
            onMouseEnter={() => setIsVolumeHovered(true)}
            onMouseLeave={() => { if (!isVolumeDragging) setIsVolumeHovered(false); }}
            className={`flex items-center rounded-lg border backdrop-blur-xl transition-all shadow-2xs group/vol ${
              isAudiblyMuted
                ? "bg-rose-50 text-rose-700 border-rose-300"
                : "bg-white/80 hover:bg-white text-slate-700 border-slate-200/80"
            }`}
          >
            <button
              type="button"
              onClick={() => {
                if (onToggleMute) onToggleMute();
                else setLocalMuted((p) => !p);
              }}
              className="flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1.5 transition-colors cursor-pointer select-none"
              title={isAudiblyMuted ? "Unmute audio (M)" : "Mute audio (M)"}
            >
              {isAudiblyMuted ? (
                <VolumeX className="w-3.5 h-3.5 text-rose-500 shrink-0" />
              ) : volume > 0.5 ? (
                <Volume2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              ) : (
                <Volume1 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              )}
              <span className="hidden sm:inline shrink-0">
                {isAudiblyMuted
                  ? "Muted"
                  : isStemActive
                  ? currentTrack?.label
                    ? currentTrack.label.slice(0, 10)
                    : "Stem"
                  : "Audio"}
              </span>
            </button>
            <div
              className={`transition-all duration-200 flex items-center overflow-hidden ${
                isVolumeHovered || isVolumeDragging
                  ? "w-18 pr-2.5 opacity-100"
                  : "w-0 pr-0 opacity-0 pointer-events-none"
              }`}
            >
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isAudiblyMuted ? 0 : volume}
                onMouseDown={() => setIsVolumeDragging(true)}
                onMouseUp={() => setIsVolumeDragging(false)}
                onTouchStart={() => setIsVolumeDragging(true)}
                onTouchEnd={() => setIsVolumeDragging(false)}
                onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                className="w-16 h-1 accent-emerald-600 cursor-pointer"
              />
            </div>
          </div>

          {/* Speed */}
          <div ref={speedMenuRef} className="relative">
            <button
              type="button"
              onClick={cycleSpeed}
              onContextMenu={(e) => { e.preventDefault(); setIsSpeedMenuOpen((p) => !p); }}
              className="text-[11px] font-mono font-semibold px-2.5 py-1.5 rounded-lg bg-white/80 hover:bg-white backdrop-blur-xl text-slate-700 border border-slate-200/80 transition-all cursor-pointer shadow-2xs"
              title="Click to cycle speed"
            >
              {playbackSpeed}x
            </button>
            {isSpeedMenuOpen && (
              <div className="absolute bottom-full right-0 mb-1 bg-white/95 border border-slate-200/90 p-1 rounded-lg shadow-xl flex flex-col gap-0.5 z-40 backdrop-blur-xl">
                {SPEED_PRESETS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => handleSpeedSelect(s)}
                    className={`px-2 py-0.5 text-[10px] font-mono rounded-lg text-left cursor-pointer transition-colors ${
                      playbackSpeed === s
                        ? "bg-emerald-600 text-white font-bold"
                        : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                    }`}
                  >
                    {s}x
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* PiP */}
          <button
            type="button"
            onClick={togglePiP}
            className={`p-1.5 rounded-lg border backdrop-blur-xl transition-all cursor-pointer shadow-2xs ${
              isPiPActive
                ? "bg-emerald-500/10 text-emerald-700 border-emerald-500/30"
                : "bg-white/80 hover:bg-white text-slate-600 hover:text-slate-900 border-slate-200/80"
            }`}
            title="Picture-in-Picture (P)"
          >
            <PictureInPicture2 className="w-3.5 h-3.5" />
          </button>

          {/* Fullscreen */}
          <button
            type="button"
            onClick={toggleFullscreen}
            className="p-1.5 rounded-lg bg-white/80 hover:bg-white backdrop-blur-xl text-slate-600 hover:text-slate-900 border border-slate-200/80 shadow-2xs active:scale-95 transition-all cursor-pointer"
            title="Fullscreen (F / Double-click)"
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>
    </div>
  );
}
