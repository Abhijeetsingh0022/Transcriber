"use client";

import React, { useEffect, useRef } from "react";
import { AlertTriangle, Info, CheckCircle2, Trash2, X } from "lucide-react";

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────

export type ModalVariant = "danger" | "warning" | "info" | "success";

export interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ModalVariant;
  onConfirm: () => void;
  onCancel: () => void;
}

export interface AlertModalProps {
  open: boolean;
  title: string;
  message: string;
  buttonLabel?: string;
  variant?: ModalVariant;
  onClose: () => void;
}

// ─────────────────────────────────────────────
// Variant Configuration Helpers
// ─────────────────────────────────────────────

interface VariantConfig {
  badgeBg: string;
  badgeBorder: string;
  badgeText: string;
  confirmBtnBg: string;
  icon: React.ReactNode;
}

function getVariantConfig(variant: ModalVariant = "info"): VariantConfig {
  switch (variant) {
    case "danger":
      return {
        badgeBg: "bg-rose-50",
        badgeBorder: "border-rose-200/80",
        badgeText: "text-rose-600",
        confirmBtnBg: "bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-xs shadow-rose-600/20",
        icon: <Trash2 className="w-5 h-5" />,
      };
    case "warning":
      return {
        badgeBg: "bg-amber-50",
        badgeBorder: "border-amber-200/80",
        badgeText: "text-amber-600",
        confirmBtnBg: "bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-xs shadow-amber-600/20",
        icon: <AlertTriangle className="w-5 h-5" />,
      };
    case "success":
      return {
        badgeBg: "bg-emerald-50",
        badgeBorder: "border-emerald-200/80",
        badgeText: "text-emerald-600",
        confirmBtnBg: "bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-xs shadow-emerald-600/20",
        icon: <CheckCircle2 className="w-5 h-5" />,
      };
    case "info":
    default:
      return {
        badgeBg: "bg-blue-50",
        badgeBorder: "border-blue-200/80",
        badgeText: "text-blue-600",
        confirmBtnBg: "bg-slate-900 hover:bg-slate-800 active:bg-black text-white shadow-xs shadow-slate-900/20",
        icon: <Info className="w-5 h-5" />,
      };
  }
}

// ─────────────────────────────────────────────
// Shared Modal Backdrop + Panel Shell
// ─────────────────────────────────────────────

function ModalShell({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const prevActive = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      prevActive?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in duration-150"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        className="bg-white rounded-lg border border-slate-200/90 shadow-2xl max-w-md w-full p-6 animate-popover relative outline-none transition-all"
      >
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
// ConfirmModal Component
// ─────────────────────────────────────────────

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel = "Cancel",
  variant = "danger",
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  const confirmButtonRef = useRef<HTMLButtonElement>(null);
  const cfg = getVariantConfig(variant);
  const resolvedConfirmLabel = confirmLabel || (variant === "danger" ? "Delete" : "Confirm");

  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => confirmButtonRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  return (
    <ModalShell open={open} onClose={onCancel}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3.5">
          <div
            className={`w-10 h-10 rounded-lg ${cfg.badgeBg} border ${cfg.badgeBorder} flex items-center justify-center ${cfg.badgeText} shrink-0 mt-0.5`}
          >
            {cfg.icon}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-base tracking-tight leading-snug">
              {title}
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 font-normal mt-1 leading-relaxed">
              {message}
            </p>
          </div>
        </div>
        <button
          onClick={onCancel}
          type="button"
          aria-label="Close dialog"
          className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center justify-end gap-2.5 pt-5 mt-4 border-t border-slate-100">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:text-slate-900 rounded-lg border border-slate-200/90 hover:bg-slate-50 transition-colors cursor-pointer active:scale-95"
        >
          {cancelLabel}
        </button>
        <button
          ref={confirmButtonRef}
          type="button"
          onClick={onConfirm}
          className={`flex items-center justify-center px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all cursor-pointer active:scale-95 ${cfg.confirmBtnBg}`}
        >
          {resolvedConfirmLabel}
        </button>
      </div>
    </ModalShell>
  );
}

// ─────────────────────────────────────────────
// AlertModal Component
// ─────────────────────────────────────────────

export function AlertModal({
  open,
  title,
  message,
  buttonLabel = "Dismiss",
  variant = "warning",
  onClose,
}: AlertModalProps) {
  const dismissButtonRef = useRef<HTMLButtonElement>(null);
  const cfg = getVariantConfig(variant);

  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => dismissButtonRef.current?.focus(), 50);
      return () => clearTimeout(timer);
    }
  }, [open]);

  return (
    <ModalShell open={open} onClose={onClose}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3.5">
          <div
            className={`w-10 h-10 rounded-lg ${cfg.badgeBg} border ${cfg.badgeBorder} flex items-center justify-center ${cfg.badgeText} shrink-0 mt-0.5`}
          >
            {cfg.icon}
          </div>
          <div>
            <h3 className="font-semibold text-slate-900 text-base tracking-tight leading-snug">
              {title}
            </h3>
            <p className="text-xs sm:text-sm text-slate-500 font-normal mt-1 leading-relaxed">
              {message}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          type="button"
          aria-label="Close dialog"
          className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex items-center justify-end pt-5 mt-4 border-t border-slate-100">
        <button
          ref={dismissButtonRef}
          type="button"
          onClick={onClose}
          className="px-4 py-2 text-xs sm:text-sm font-semibold text-slate-700 hover:text-slate-900 rounded-lg border border-slate-200/90 hover:bg-slate-50 transition-colors cursor-pointer active:scale-95"
        >
          {buttonLabel}
        </button>
      </div>
    </ModalShell>
  );
}
