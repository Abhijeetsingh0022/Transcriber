"use client";

/**
 * MuxModal — Orchestrator for the Mux Studio.
 * Holds all async state and wires the three sub-panels together:
 *   MuxVideoPlayer  — left panel video preview
 *   MuxTrackCard    — rendered inside left panel track list
 *   MuxExportPanel  — right panel export settings & status
 *
 * Sub-modal sheets are handled by:
 *   MuxUploadVideoModal  — replace video sheet
 *   MuxAddTrackModal     — add audio track sheet
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  Layers,
  Loader2,
  Music,
  Plus,
  Sliders,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";

import { MuxJob, MuxTrack } from "../types";
import { API_BASE } from "../utils";
import { TrackMixState } from "../muxConstants";

import { MuxTrackCard } from "./MuxTrackCard";
import { MuxVideoPlayer, VideoInfo } from "./MuxVideoPlayer";
import { MuxExportPanel } from "./MuxExportPanel";
import { MuxUploadVideoModal } from "./MuxUploadVideoModal";
import { MuxAddTrackModal } from "./MuxAddTrackModal";

interface MuxModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  mediaStem?: string;
}

export function MuxModal({ isOpen, onClose, jobId }: MuxModalProps) {
  // ── Track data ─────────────────────────────────────────────────────────────
  const [tracks, setTracks] = useState<MuxTrack[]>([]);
  const [isLoadingTracks, setIsLoadingTracks] = useState(false);
  const [isImportingOriginal, setIsImportingOriginal] = useState(false);

  // ── UI navigation ──────────────────────────────────────────────────────────
  const [mobileTab, setMobileTab] = useState<"tracks" | "export">("tracks");

  // ── Video source ───────────────────────────────────────────────────────────
  const [videoInfo, setVideoInfo] = useState<VideoInfo | null>(null);
  const [outputVideoInfo, setOutputVideoInfo] = useState<VideoInfo | null>(null);
  const [isLoadingVideoInfo, setIsLoadingVideoInfo] = useState(false);
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);
  const [isUploadingVideo, setIsUploadingVideo] = useState(false);
  const [videoUploadError, setVideoUploadError] = useState<string | null>(null);

  // ── Add track sheet ────────────────────────────────────────────────────────
  const [isAddTrackOpen, setIsAddTrackOpen] = useState(false);
  const [isUploadingStem, setIsUploadingStem] = useState(false);
  const [stemUploadError, setStemUploadError] = useState<string | null>(null);

  // ── Export settings ────────────────────────────────────────────────────────
  const [outputFormat, setOutputFormat] = useState<"mp4" | "mkv" | "mov">("mp4");
  const [muxMode, setMuxMode] = useState<"tracks" | "blend">("tracks");
  const [muteAllAudio, setMuteAllAudio] = useState(false);
  const [isMuxing, setIsMuxing] = useState(false);
  const [muxJob, setMuxJob] = useState<MuxJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Player state ───────────────────────────────────────────────────────────
  const [playerMode, setPlayerMode] = useState<"source" | "output">("source");
  const [isVideoPlaying, setIsVideoPlaying] = useState(false);
  const videoCurrentTimeRef = useRef(0);

  // ── Mixer state ────────────────────────────────────────────────────────────
  const [mixUI, setMixUI] = useState<Map<string, TrackMixState>>(new Map());
  const [playingTrackId, setPlayingTrackId] = useState<string | null>(null);
  const [playerVolume, setPlayerVolume] = useState<number>(1.0);
  const [isPlayerMuted, setIsPlayerMuted] = useState<boolean>(false);
  const previewAudioRef = useRef<HTMLAudioElement | null>(null);

  const handleTogglePlayerMute = () => {
    setIsPlayerMuted((prev) => !prev);
  };

  const handlePlayerVolumeChange = (vol: number) => {
    setPlayerVolume(vol);
    if (vol === 0) setIsPlayerMuted(true);
    else if (isPlayerMuted) setIsPlayerMuted(false);
  };

  // ── Helpers: mixer ─────────────────────────────────────────────────────────
  const getMix = useCallback(
    (id: string): TrackMixState =>
      mixUI.get(id) ?? { gain: 1, muted: false, soloed: false },
    [mixUI]
  );

  const allMuted = tracks.length > 0 && tracks.every((t) => getMix(t.id).muted);

  const handleToggleMasterMute = () => {
    setMixUI((prev) => {
      const next = new Map(prev);
      tracks.forEach((t) => {
        const s = next.get(t.id) ?? { gain: 1, muted: false, soloed: false };
        next.set(t.id, { ...s, muted: !allMuted });
      });
      return next;
    });
  };

  const updateGain = (trackId: string, gain: number) => {
    setMixUI((prev) => {
      const next = new Map(prev);
      const s = next.get(trackId) ?? { gain: 1, muted: false, soloed: false };
      next.set(trackId, { ...s, gain });
      return next;
    });
    fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ gain }),
    }).catch(() => {});
  };

  const toggleMute = (trackId: string) =>
    setMixUI((prev) => {
      const next = new Map(prev);
      const s = next.get(trackId) ?? { gain: 1, muted: false, soloed: false };
      next.set(trackId, { ...s, muted: !s.muted });
      return next;
    });

  const toggleSolo = (trackId: string) =>
    setMixUI((prev) => {
      const next = new Map(prev);
      const s = next.get(trackId) ?? { gain: 1, muted: false, soloed: false };
      next.set(trackId, { ...s, soloed: !s.soloed });
      return next;
    });

  // ── API: fetch tracks ──────────────────────────────────────────────────────
  const fetchTracks = useCallback(async () => {
    setIsLoadingTracks(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks`);
      if (!res.ok) return;
      const data: MuxTrack[] = await res.json();
      setTracks(data);
      setMixUI((prev) => {
        const next = new Map(prev);
        data.forEach((t) => {
          if (!next.has(t.id))
            next.set(t.id, { gain: t.gain ?? 1, muted: t.is_muted ?? false, soloed: false });
        });
        return next;
      });
    } catch { /* silent */ }
    finally { setIsLoadingTracks(false); }
  }, [jobId]);

  const fetchVideoInfo = useCallback(async () => {
    setIsLoadingVideoInfo(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/video/info`);
      if (res.ok) setVideoInfo(await res.json());
    } catch { /* silent */ }
    finally { setIsLoadingVideoInfo(false); }
  }, [jobId]);

  const fetchOutputVideoInfo = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/output/info`);
      if (res.ok) setOutputVideoInfo(await res.json());
    } catch { /* silent */ }
  }, [jobId]);

  const fetchMuxStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/status`);
      if (!res.ok) return;
      const data: MuxJob = await res.json();
      setMuxJob(data);
      if (data.status === "completed" || data.status === "failed") {
        setIsMuxing(false);
        if (pollRef.current) clearInterval(pollRef.current);
        if (data.status === "completed") fetchOutputVideoInfo();
      }
    } catch { /* silent */ }
  }, [jobId, fetchOutputVideoInfo]);

  useEffect(() => {
    if (!isOpen) return;
    const timer = setTimeout(() => {
      fetchTracks();
      fetchVideoInfo();
      fetchMuxStatus();
    }, 0);
    return () => {
      clearTimeout(timer);
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isOpen, fetchTracks, fetchVideoInfo, fetchMuxStatus]);

  // ── API: track mutations ───────────────────────────────────────────────────
  const handleDeleteTrack = async (trackId: string) => {
    await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}`, { method: "DELETE" }).catch(() => {});
    setTracks((p) => p.filter((t) => t.id !== trackId));
    setMixUI((prev) => { const next = new Map(prev); next.delete(trackId); return next; });
    if (playingTrackId === trackId) {
      setPlayingTrackId(null);
      previewAudioRef.current?.pause();
    }
  };

  const handleMoveTrack = async (trackId: string, direction: "up" | "down") => {
    const idx = tracks.findIndex((t) => t.id === trackId);
    if (idx === -1) return;
    const newIdx = direction === "up" ? idx - 1 : idx + 1;
    if (newIdx < 0 || newIdx >= tracks.length) return;
    const reordered = [...tracks];
    [reordered[idx], reordered[newIdx]] = [reordered[newIdx], reordered[idx]];
    setTracks(reordered);
    await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/reorder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ track_ids: reordered.map((t) => t.id) }),
    }).catch(() => {});
  };

  const handleSetDefault = async (trackId: string) => {
    setTracks((p) => p.map((t) => ({ ...t, is_default: t.id === trackId })));
    await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ is_default: true }),
    }).catch(() => {});
  };

  const handleUpdateLabel = async (trackId: string, label: string) => {
    setTracks((p) => p.map((t) => (t.id === trackId ? { ...t, label } : t)));
    await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    }).catch(() => {});
  };

  const handleUpdateLanguage = async (trackId: string, language: string) => {
    setTracks((p) => p.map((t) => (t.id === trackId ? { ...t, language } : t)));
    await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language }),
    }).catch(() => {});
  };

  // ── Preview / track selection ──────────────────────────────────────────────
  const togglePreview = (track: MuxTrack) => {
    if (playingTrackId === track.id) {
      handleSelectAudioTrack(null);
    } else {
      handleSelectAudioTrack(track.id);
    }
  };

  const handleSelectAudioTrack = useCallback(
    (trackId: string | null) => {
      setPlayingTrackId(trackId);
      if (!previewAudioRef.current) previewAudioRef.current = new Audio();
      const audio = previewAudioRef.current;
      if (trackId === null) {
        audio.pause();
        audio.src = "";
        return;
      }
      const track = tracks.find((t) => t.id === trackId);
      if (!track) return;
      const targetSrc = `${API_BASE}/jobs/${jobId}/mux/tracks/${trackId}/stream`;
      if (audio.src !== targetSrc) {
        audio.src = targetSrc;
      }
      const delayMs = track.delay_ms ?? 0;
      const targetTime = Math.max(0, videoCurrentTimeRef.current - delayMs / 1000);
      const mix = getMix(trackId);
      audio.muted = isPlayerMuted || mix.muted;
      audio.volume = isPlayerMuted || mix.muted ? 0 : Math.min(1, playerVolume * mix.gain);

      const syncAndPlay = () => {
        try {
          audio.currentTime = targetTime;
        } catch { /* wait for readyState */ }
        if (isVideoPlaying) {
          audio.play().catch(() => {});
        }
      };

      if (audio.readyState >= 1) {
        syncAndPlay();
      } else {
        audio.addEventListener("loadedmetadata", syncAndPlay, { once: true });
        audio.load();
      }
    },
    [tracks, isVideoPlaying, jobId, getMix, isPlayerMuted, playerVolume]
  );

  const handleVideoTimeUpdate = useCallback(
    (currentTime: number) => {
      videoCurrentTimeRef.current = currentTime;
      if (playingTrackId && previewAudioRef.current) {
        const audio = previewAudioRef.current;
        const track = tracks.find((t) => t.id === playingTrackId);
        const delayMs = track?.delay_ms ?? 0;
        const expected = Math.max(0, currentTime - delayMs / 1000);
        if (audio.readyState >= 1 && Math.abs(audio.currentTime - expected) > 0.15) {
          try {
            audio.currentTime = expected;
          } catch { /* ignore */ }
        }
      }
    },
    [playingTrackId, tracks]
  );

  const handleVideoPlayStateChange = useCallback(
    (playing: boolean) => {
      setIsVideoPlaying(playing);
      if (!previewAudioRef.current || !playingTrackId) return;
      const audio = previewAudioRef.current;
      if (playing) {
        const track = tracks.find((t) => t.id === playingTrackId);
        const delayMs = track?.delay_ms ?? 0;
        const targetTime = Math.max(0, videoCurrentTimeRef.current - delayMs / 1000);
        const mix = getMix(playingTrackId);
        audio.muted = isPlayerMuted || mix.muted;
        audio.volume = isPlayerMuted || mix.muted ? 0 : Math.min(1, playerVolume * mix.gain);

        const doPlay = () => {
          try {
            audio.currentTime = targetTime;
          } catch { /* ignore */ }
          audio.play().catch(() => {});
        };

        if (audio.readyState >= 1) {
          doPlay();
        } else {
          audio.addEventListener("loadedmetadata", doPlay, { once: true });
          audio.load();
        }
      } else {
        audio.pause();
      }
    },
    [playingTrackId, tracks, getMix, isPlayerMuted, playerVolume]
  );

  useEffect(() => {
    if (previewAudioRef.current) {
      previewAudioRef.current.muted = isPlayerMuted;
      if (playingTrackId) {
        const mix = getMix(playingTrackId);
        previewAudioRef.current.volume = isPlayerMuted || mix.muted ? 0 : Math.min(1, playerVolume * mix.gain);
      }
    }
  }, [mixUI, playingTrackId, getMix, isPlayerMuted, playerVolume]);

  // ── Import original audio ──────────────────────────────────────────────────
  const handleImportOriginal = async () => {
    setIsImportingOriginal(true);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/import-original`, { method: "POST" });
      if (res.ok) await fetchTracks();
    } catch { /* silent */ }
    finally { setIsImportingOriginal(false); }
  };

  // ── Upload video ───────────────────────────────────────────────────────────
  const handleUploadVideo = async (opts: {
    file: File;
    extractAudio: boolean;
    audioLabel: string;
    audioLang: string;
  }) => {
    setIsUploadingVideo(true);
    setVideoUploadError(null);
    try {
      const form = new FormData();
      form.append("file", opts.file);
      form.append("extract_audio", String(opts.extractAudio));
      if (opts.extractAudio) {
        form.append("audio_label", opts.audioLabel);
        form.append("audio_language", opts.audioLang);
      }
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/video/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Upload failed");
      }
      await fetchVideoInfo();
      if (opts.extractAudio) await fetchTracks();
      setIsVideoModalOpen(false);
    } catch (err: unknown) {
      setVideoUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsUploadingVideo(false);
    }
  };

  const handleResetVideo = async () => {
    await fetch(`${API_BASE}/jobs/${jobId}/mux/video/reset`, { method: "POST" }).catch(() => {});
    fetchVideoInfo();
  };

  // ── Upload stem ────────────────────────────────────────────────────────────
  const handleAddTrack = async (opts: {
    file: File;
    label: string;
    language: string;
    codec: string;
    disposition: string;
    isDefault: boolean;
  }) => {
    setIsUploadingStem(true);
    setStemUploadError(null);
    try {
      const form = new FormData();
      form.append("file", opts.file);
      form.append("label", opts.label);
      form.append("language", opts.language);
      form.append("codec", opts.codec);
      form.append("disposition", opts.disposition);
      form.append("is_default", String(opts.isDefault));
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/tracks/upload`, { method: "POST", body: form });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Upload failed");
      }
      await fetchTracks();
      setIsAddTrackOpen(false);
    } catch (err: unknown) {
      setStemUploadError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsUploadingStem(false);
    }
  };

  // ── Export mux ─────────────────────────────────────────────────────────────
  const handleStartMux = async () => {
    setIsMuxing(true);
    setMuxJob(null);
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/mux/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          output_format: outputFormat,
          include_video: true,
          faststart: true,
          mux_mode: muxMode,
          mute_all_audio: muteAllAudio,
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Mux failed to start");
      }
      const data = await res.json();
      setMuxJob(data);
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(fetchMuxStatus, 1000);
    } catch (err: unknown) {
      setIsMuxing(false);
      setMuxJob({
        job_id: jobId,
        status: "failed",
        output_path: null,
        output_format: outputFormat,
        error_message: err instanceof Error ? err.message : String(err),
      });
    }
  };

  const hasOriginalTrack = tracks.some(
    (t) =>
      t.label.toLowerCase().includes("original") ||
      t.label.toLowerCase().includes("source")
  );

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-3 animate-in fade-in duration-200 select-none"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white border border-slate-200 rounded-lg shadow-2xl max-w-[1560px] w-full flex flex-col h-[96dvh] max-h-[96dvh] overflow-hidden ring-1 ring-slate-900/5 animate-in zoom-in-95 duration-200">

        {/* ── HEADER ──────────────────────────────────────────────────────── */}
        <div className="px-5 py-3.5 border-b border-slate-200 bg-white flex items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center text-white shadow-sm shadow-emerald-500/25 shrink-0">
              <Layers className="w-4.5 h-4.5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 text-sm tracking-tight truncate">Mux Studio</h3>
                <span className="text-[10px] font-mono font-bold bg-emerald-50 border border-emerald-200 text-emerald-700 px-2 py-0.5 rounded-full uppercase tracking-wide shrink-0">
                  Multi-Track Exporter
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-0.5 truncate hidden sm:block">
                Compose Hindi, English, and custom dubs onto video without quality loss
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-xs font-mono font-semibold text-slate-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{tracks.length} {tracks.length === 1 ? "track" : "tracks"}</span>
            </div>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
              title="Close (Esc)"
            >
              <X className="w-4.5 h-4.5" />
            </button>
          </div>
        </div>

        {/* ── MOBILE TABS ──────────────────────────────────────────────────── */}
        <div className="lg:hidden px-4 py-2 bg-slate-50 border-b border-slate-200 grid grid-cols-2 gap-1.5 shrink-0">
          {([
            ["tracks", "Video & Tracks", Sliders],
            ["export", "Export", Layers],
          ] as const).map(([tab, label, Icon]) => (
            <button
              key={tab}
              type="button"
              onClick={() => setMobileTab(tab)}
              className={`flex items-center justify-center gap-2 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                mobileTab === tab
                  ? "bg-white text-emerald-700 shadow-sm border border-slate-200"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* ── BODY ─────────────────────────────────────────────────────────── */}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 overflow-y-auto lg:overflow-hidden">

          {/* LEFT: Video + Tracks (7/12 cols) */}
          <div
            className={`lg:col-span-7 flex flex-col min-h-0 border-b lg:border-b-0 lg:border-r border-slate-200 ${
              mobileTab === "tracks" ? "flex" : "hidden lg:flex"
            }`}
          >
            {/* Player */}
            <div className="shrink-0">
              <MuxVideoPlayer
                jobId={jobId}
                videoInfo={videoInfo}
                outputVideoInfo={outputVideoInfo}
                hasOutputVideo={muxJob?.status === "completed"}
                activeMode={playerMode}
                onModeChange={setPlayerMode}
                isLoadingInfo={isLoadingVideoInfo}
                tracks={tracks}
                selectedTrackId={playingTrackId}
                onSelectTrack={handleSelectAudioTrack}
                onSetDefaultTrack={handleSetDefault}
                auditionLabel={
                  playingTrackId
                    ? tracks.find((t) => t.id === playingTrackId)?.label ??
                      tracks.find((t) => t.id === playingTrackId)?.language?.toUpperCase() ??
                      "Audio Stem"
                    : null
                }
                isMuteAllAudio={muteAllAudio}
                onTimeUpdate={handleVideoTimeUpdate}
                onPlayStateChange={handleVideoPlayStateChange}
                onUploadVideoClick={() => setIsVideoModalOpen(true)}
                onResetVideoClick={handleResetVideo}
                playerVolume={playerVolume}
                onVolumeChange={handlePlayerVolumeChange}
                isPlayerMuted={isPlayerMuted}
                onToggleMute={handleTogglePlayerMute}
              />
            </div>

            {/* Tracks toolbar */}
            <div className="px-5 py-3 border-b border-slate-200 bg-white flex items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Audio Tracks
                  <span className="ml-1.5 text-[10px] font-mono bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full border border-slate-200 normal-case tracking-normal">
                    {tracks.length}
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-2">
                {tracks.length > 0 && (
                  <button
                    type="button"
                    onClick={handleToggleMasterMute}
                    className={`flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg border transition-all active:scale-95 cursor-pointer ${
                      allMuted
                        ? "bg-rose-50 border-rose-200 text-rose-700 hover:bg-rose-100"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {allMuted ? <VolumeX className="w-3 h-3" /> : <Volume2 className="w-3 h-3" />}
                    {allMuted ? "Unmute All" : "Mute All"}
                  </button>
                )}
                {!hasOriginalTrack && (
                  <button
                    type="button"
                    onClick={handleImportOriginal}
                    disabled={isImportingOriginal}
                    className="flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 transition-all active:scale-95 cursor-pointer disabled:opacity-50"
                  >
                    {isImportingOriginal ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Music className="w-3 h-3" />
                    )}
                    Import Original
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setIsAddTrackOpen(true)}
                  className="flex items-center gap-1 text-xs font-semibold px-3 py-1 rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 transition-all active:scale-95 cursor-pointer shadow-sm"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Track
                </button>
              </div>
            </div>

            {/* Tracks list */}
            <div className="flex-1 min-h-0 p-4 sm:p-5 overflow-y-auto">
              {isLoadingTracks && tracks.length === 0 ? (
                <div className="h-44 flex flex-col items-center justify-center text-slate-400 gap-2">
                  <Loader2 className="w-6 h-6 animate-spin text-emerald-600" />
                  <span className="text-xs font-medium">Loading tracks...</span>
                </div>
              ) : tracks.length === 0 ? (
                <div className="p-8 text-center bg-slate-50 border border-dashed border-slate-200 rounded-lg space-y-3">
                  <div className="w-11 h-11 rounded-lg bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto text-emerald-600">
                    <Music className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-900 text-sm">No audio tracks yet</h4>
                    <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 leading-relaxed">
                      Add audio stems (e.g. Hindi from video + English dub) to mux onto your video.
                    </p>
                  </div>
                  <div className="pt-1 flex items-center justify-center gap-2 flex-wrap">
                    <button
                      type="button"
                      onClick={() => setIsAddTrackOpen(true)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all active:scale-95 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Audio Track
                    </button>
                    {!hasOriginalTrack && (
                      <button
                        type="button"
                        onClick={handleImportOriginal}
                        disabled={isImportingOriginal}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 rounded-lg text-xs font-semibold transition-all active:scale-95 cursor-pointer"
                      >
                        <Music className="w-3.5 h-3.5" />
                        Import Project Audio
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {tracks.map((track, idx) => {
                    const mix = getMix(track.id);
                    return (
                      <MuxTrackCard
                        key={track.id}
                        track={track}
                        index={idx}
                        isFirst={idx === 0}
                        isLast={idx === tracks.length - 1}
                        isPlaying={playingTrackId === track.id}
                        gain={mix.gain}
                        isMuted={mix.muted}
                        isSoloed={mix.soloed}
                        onTogglePreview={togglePreview}
                        onGainChange={updateGain}
                        onToggleMute={toggleMute}
                        onToggleSolo={toggleSolo}
                        onSetDefault={handleSetDefault}
                        onMove={handleMoveTrack}
                        onDelete={handleDeleteTrack}
                        onUpdateLabel={handleUpdateLabel}
                        onUpdateLanguage={handleUpdateLanguage}
                      />
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Export panel (5/12 cols) */}
          <div className={mobileTab === "export" ? "contents" : "hidden lg:contents"}>
            <MuxExportPanel
              jobId={jobId}
              trackCount={tracks.length}
              customVideoName={muxJob?.custom_video_name}
              muxJob={muxJob}
              isMuxing={isMuxing}
              outputFormat={outputFormat}
              muxMode={muxMode}
              muteAllAudio={muteAllAudio}
              playerMode={playerMode}
              onOutputFormatChange={setOutputFormat}
              onMuxModeChange={setMuxMode}
              onMuteAllAudioChange={setMuteAllAudio}
              onStartMux={handleStartMux}
              onWatchOutput={() => {
                setPlayerMode("output");
                if (mobileTab === "export") setMobileTab("tracks");
              }}
            />
          </div>
        </div>

        {/* ── FOOTER ───────────────────────────────────────────────────────── */}
        <div className="h-10 px-5 border-t border-slate-200 bg-white flex items-center justify-between text-xs text-slate-500 shrink-0 select-none">
          <div className="flex items-center gap-2 text-slate-600 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>FFmpeg Stream Passthrough Active</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 bg-slate-100 border border-slate-200 hover:bg-slate-200 text-slate-700 font-semibold rounded-lg text-xs transition-all active:scale-95 cursor-pointer"
          >
            Done
          </button>
        </div>
      </div>

      {/* ── SUB-MODALS ─────────────────────────────────────────────────────── */}
      {isVideoModalOpen && (
        <MuxUploadVideoModal
          onClose={() => { setIsVideoModalOpen(false); setVideoUploadError(null); }}
          onApply={handleUploadVideo}
          isUploading={isUploadingVideo}
          error={videoUploadError}
        />
      )}

      {isAddTrackOpen && (
        <MuxAddTrackModal
          onClose={() => { setIsAddTrackOpen(false); setStemUploadError(null); }}
          onAdd={handleAddTrack}
          isUploading={isUploadingStem}
          error={stemUploadError}
        />
      )}
    </div>
  );
}
