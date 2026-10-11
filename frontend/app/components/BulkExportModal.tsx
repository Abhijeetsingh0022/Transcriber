"use client";

import React from "react";
import { Archive, X, Download, Loader2 } from "lucide-react";
import { BULK_EXPORT_FORMAT_OPTIONS } from "../constants";

interface BulkExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedCount: number;
  bulkExportFormats: string[];
  setBulkExportFormats: React.Dispatch<React.SetStateAction<string[]>>;
  isBulkExporting: boolean;
  onExecuteBulkExport: () => void;
}

export function BulkExportModal({
  isOpen,
  onClose,
  selectedCount,
  bulkExportFormats,
  setBulkExportFormats,
  isBulkExporting,
  onExecuteBulkExport,
}: BulkExportModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-lg border border-slate-200/90 shadow-2xl max-w-[calc(100vw-2rem)] sm:max-w-md w-full p-4 sm:p-6 animate-popover max-h-[92dvh] flex flex-col">
        <div className="flex items-center justify-between pb-3 sm:pb-3.5 border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/80 flex items-center justify-center p-1 shadow-2xs shrink-0">
              <img src="/tmux-icon.png" alt="TMUX" className="w-5 h-auto object-contain" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] font-bold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200/60 font-mono leading-none">
                  TMUX
                </span>
                <h3 className="font-semibold text-slate-900 text-sm">
                  Bulk Export Package
                </h3>
              </div>
              <p className="text-[11px] text-slate-500 font-medium">
                {selectedCount} item(s) selected
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-500 my-2.5 sm:my-3 shrink-0">
          Select the transcript formats you wish to bundle into your downloadable ZIP archive:
        </p>

        <div className="space-y-1.5 sm:space-y-2 mb-4 sm:mb-5 overflow-y-auto flex-1 min-h-0 pr-1">
          {BULK_EXPORT_FORMAT_OPTIONS.map((fmt) => (
            <label
              key={fmt.id}
              className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-slate-50 border border-slate-100 cursor-pointer text-xs transition-colors"
            >
              <input
                type="checkbox"
                checked={bulkExportFormats.includes(fmt.id)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setBulkExportFormats((prev) => [...prev, fmt.id]);
                  } else {
                    setBulkExportFormats((prev) => prev.filter((f) => f !== fmt.id));
                  }
                }}
                className="rounded-lg border-slate-300 text-slate-900 focus:ring-0"
              />
              <span className="font-semibold text-slate-800">{fmt.label}</span>
            </label>
          ))}
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-3.5 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-lg border border-slate-200/90 hover:bg-slate-50 transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isBulkExporting || !bulkExportFormats.length}
            onClick={onExecuteBulkExport}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-xs transition-all active:scale-95 cursor-pointer"
          >
            {isBulkExporting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Bundling ZIP...</span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>Download ZIP Bundle</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
