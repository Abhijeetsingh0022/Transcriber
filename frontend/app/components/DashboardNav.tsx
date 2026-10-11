"use client";

import React, { useState, useEffect } from "react";
import { Mic, UploadCloud, Layers, Loader2, ArrowUp, Cpu, Settings } from "lucide-react";
import { SystemTelemetry } from "../types";

interface DashboardNavProps {
  telemetry: SystemTelemetry | null;
  totalJobsCount: number;
  onOpenSettings?: () => void;
}

export function DashboardNav({ telemetry, totalJobsCount, onOpenSettings }: DashboardNavProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [activeSection, setActiveSection] = useState<"ingestion" | "queue">("ingestion");

  const isEngineActive = telemetry?.worker_status === "processing";

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 15);
      const queueEl = document.getElementById("queue-section");
      if (queueEl) {
        setActiveSection(queueEl.getBoundingClientRect().top <= 240 ? "queue" : "ingestion");
      }
    };
    handleScroll();
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollTo = (e: React.MouseEvent, id: string) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const scrollTop = (e: React.MouseEvent) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <header
      className={`sticky top-0 z-40 px-4 w-full flex justify-center pointer-events-none transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        isScrolled ? "pt-2 sm:pt-2.5" : "pt-4 sm:pt-5"
      }`}
    >
      <nav
        className={`pointer-events-auto relative flex items-center justify-between gap-3 sm:gap-5 rounded-full transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] ${
          isScrolled
            ? "liquid-glass-dock-scrolled max-w-xl sm:max-w-[620px] w-full px-3.5 py-1.5 sm:px-5 sm:py-2"
            : "liquid-glass-dock max-w-xl sm:max-w-2xl w-full px-4 py-2 sm:px-6 sm:py-2.5"
        }`}
      >
        {/* Specular edge highlight */}
        <div className="pointer-events-none absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-white to-transparent opacity-95 rounded-full" />

        {/* Brand */}
        <button
          onClick={scrollTop}
          type="button"
          className="flex items-center gap-1.5 sm:gap-2 group cursor-pointer select-none shrink-0"
          title="TMUX Studio — scroll to top"
        >
          {/* TMUX official brand mark */}
          <img
            src="/tmux-logo.png"
            alt="TMUX"
            className="h-5 sm:h-6 w-auto object-contain group-hover:scale-105 transition-transform duration-200"
          />
          <span className="text-[10px] text-slate-400 font-mono tracking-wider uppercase hidden sm:inline border-l border-slate-200 pl-2 ml-0.5">
            Studio
          </span>
        </button>

        {/* Segmented nav pills */}
        <div className="flex items-center gap-0.5 sm:gap-1.5 bg-gray-100/80 p-0.5 sm:p-1 rounded-full border border-gray-200/60">
          {(["ingestion", "queue"] as const).map((section) => {
            const isActive = activeSection === section;
            return (
              <button
                key={section}
                onClick={(e) => scrollTo(e, section === "ingestion" ? "upload-card" : "queue-section")}
                className={`px-2 sm:px-3 py-1 text-[11px] sm:text-xs font-semibold rounded-full transition-all duration-200 flex items-center gap-1 sm:gap-1.5 cursor-pointer ${
                  isActive
                    ? "bg-white text-blue-700 shadow-sm border border-blue-100"
                    : "text-slate-500 hover:text-slate-900 hover:bg-white/70"
                }`}
              >
                {section === "ingestion" ? (
                  <UploadCloud className={`w-3.5 h-3.5 ${isActive ? "text-blue-500" : "text-slate-400"}`} />
                ) : (
                  <Layers className={`w-3.5 h-3.5 ${isActive ? "text-blue-500" : "text-slate-400"}`} />
                )}
                <span className="capitalize">{section}</span>
                {section === "queue" && totalJobsCount > 0 && (
                  <span
                    className={`px-1.5 py-px rounded-full text-[10px] font-mono font-bold transition-colors ${
                      isActive
                        ? "bg-blue-600 text-white"
                        : "bg-white text-slate-700 border border-gray-200 shadow-xs"
                    }`}
                  >
                    {totalJobsCount}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Right: engine status + scroll-to-top */}
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          {isScrolled && (
            <button
              onClick={scrollTop}
              className="p-1 sm:p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-full transition-all active:scale-95 cursor-pointer border border-gray-200/80 bg-white shadow-xs"
              title="Back to top"
            >
              <ArrowUp className="w-3.5 h-3.5" />
            </button>
          )}

          {telemetry ? (
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border shadow-xs transition-all ${
                isEngineActive
                  ? "bg-blue-50 text-blue-700 border-blue-200"
                  : "bg-white text-emerald-700 border-emerald-200"
              }`}
              title={isEngineActive ? "Engine Active: Processing Audio" : "Engine Ready"}
            >
              {isEngineActive ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600" />
                  </span>
                  <span className="text-[11px]">Active</span>
                </>
              ) : (
                <>
                  <Cpu className="w-3 h-3 text-emerald-500" />
                  <span className="text-[11px]">Ready</span>
                </>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-slate-400 text-xs px-2.5 py-1">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            </div>
          )}

          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="p-1 sm:p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-full transition-all active:scale-95 cursor-pointer border border-gray-200/80 bg-white shadow-xs"
              title="Preferences & AI Engine Settings"
            >
              <Settings className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </nav>
    </header>
  );
}
