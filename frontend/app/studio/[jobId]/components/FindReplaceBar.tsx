"use client";

import React from "react";
import { Search, Replace, X } from "lucide-react";

interface FindReplaceBarProps {
  isOpen: boolean;
  onClose: () => void;
  searchQuery: string;
  onChangeSearchQuery: (q: string) => void;
  replaceQuery: string;
  onChangeReplaceQuery: (q: string) => void;
  searchMatchesCount: number;
  onReplaceAll: () => void;
}

export function FindReplaceBar({
  isOpen,
  onClose,
  searchQuery,
  onChangeSearchQuery,
  replaceQuery,
  onChangeReplaceQuery,
  searchMatchesCount,
  onReplaceAll,
}: FindReplaceBarProps) {
  if (!isOpen) return null;

  return (
    <div className="bg-white border-b border-slate-200 p-2.5 sm:p-3 px-3.5 sm:px-6 flex flex-wrap items-center gap-2 sm:gap-3 shrink-0 shadow-2xs z-10">
      <div className="flex items-center gap-2 flex-1 min-w-[130px] sm:flex-initial">
        <Search className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <input
          type="text"
          placeholder="Find in transcript..."
          value={searchQuery}
          onChange={(e) => onChangeSearchQuery(e.target.value)}
          className="w-full sm:w-48 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-blue-600"
          autoFocus
        />
      </div>

      <div className="flex items-center gap-2 flex-1 min-w-[130px] sm:flex-initial">
        <Replace className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        <input
          type="text"
          placeholder="Replace with..."
          value={replaceQuery}
          onChange={(e) => onChangeReplaceQuery(e.target.value)}
          className="w-full sm:w-48 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-900 focus:outline-none focus:border-blue-600"
        />
      </div>

      {searchQuery && (
        <div className="flex items-center gap-2 text-xs text-slate-500 font-mono shrink-0">
          <span>{searchMatchesCount} matches</span>
          <button
            onClick={onReplaceAll}
            disabled={!searchQuery.trim()}
            className="px-2.5 py-1 bg-slate-900 text-white rounded-lg text-xs font-sans hover:bg-slate-800 disabled:opacity-40 cursor-pointer active:scale-95"
          >
            Replace All
          </button>
        </div>
      )}

      <button onClick={onClose} className="text-slate-400 hover:text-slate-600 ml-auto p-1 rounded-lg hover:bg-slate-100 transition-colors">
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
