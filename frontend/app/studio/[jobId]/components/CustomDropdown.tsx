"use client";

import React, { useState, useRef, useEffect, useMemo, memo } from "react";
import { ChevronDown, Check, Search, X } from "lucide-react";

export interface DropdownOption {
  value: string;
  label: string;
  icon?: React.ReactNode;
  badge?: string;
  description?: string;
}

interface CustomDropdownProps {
  label?: string;
  value: string;
  onChange: (value: string) => void;
  options: DropdownOption[];
  placeholder?: string;
  searchable?: boolean;
  searchPlaceholder?: string;
  disabled?: boolean;
  className?: string;
  direction?: "up" | "down" | "auto";
}

export const CustomDropdown = memo(function CustomDropdown({
  label,
  value,
  onChange,
  options,
  placeholder = "Select...",
  searchable = false,
  searchPlaceholder = "Search options...",
  disabled = false,
  className = "",
  direction = "auto",
}: CustomDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [openDirection, setOpenDirection] = useState<"up" | "down">("down");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Direction calculation (smart positioning to prevent overlapping/clipping)
  useEffect(() => {
    if (!isOpen) return;

    if (direction === "up") {
      setOpenDirection("up");
      return;
    }
    if (direction === "down") {
      setOpenDirection("down");
      return;
    }

    // Auto detection
    if (dropdownRef.current) {
      const rect = dropdownRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      // If space below is tight (< 250px) and there is more space above, open upwards
      if (spaceBelow < 250 && spaceAbove > spaceBelow) {
        setOpenDirection("up");
      } else {
        setOpenDirection("down");
      }
    }
  }, [isOpen, direction]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setSearch("");
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  // Focus search input when opened
  useEffect(() => {
    if (isOpen && searchable) {
      setTimeout(() => {
        searchInputRef.current?.focus();
      }, 50);
    }
  }, [isOpen, searchable]);

  // Filter options
  const filteredOptions = useMemo(() => {
    if (!search.trim()) return options;
    const query = search.toLowerCase();
    return options.filter(
      (opt) =>
        opt.label.toLowerCase().includes(query) ||
        opt.value.toLowerCase().includes(query) ||
        (opt.description && opt.description.toLowerCase().includes(query))
    );
  }, [options, search]);

  const selectedOption = useMemo(
    () => options.find((opt) => opt.value === value),
    [options, value]
  );

  return (
    <div
      className={`relative ${isOpen ? "z-40" : "z-10"} ${className}`}
      ref={dropdownRef}
    >
      {label && (
        <label className="text-[11px] font-semibold text-slate-700 block mb-1">
          {label}
        </label>
      )}

      {/* Trigger Button */}
      <button
        type="button"
        disabled={disabled}
        onClick={() => {
          if (!disabled) {
            setIsOpen((prev) => !prev);
            setSearch("");
          }
        }}
        className={`w-full flex items-center justify-between gap-2 px-3 py-1.5 text-xs rounded-sm border bg-white text-left transition-all duration-150 cursor-pointer shadow-2xs ${
          isOpen
            ? "border-emerald-500 ring-2 ring-emerald-500/15"
            : "border-slate-300 hover:border-slate-400"
        } ${disabled ? "opacity-50 cursor-not-allowed bg-slate-50" : ""}`}
      >
        <div className="flex items-center gap-2 min-w-0">
          {selectedOption?.icon && (
            <span className="shrink-0 text-slate-500">{selectedOption.icon}</span>
          )}
          <span className="font-semibold text-slate-800 truncate">
            {selectedOption?.label || placeholder}
          </span>
          {selectedOption?.badge && (
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-xs bg-slate-100 text-slate-600 border border-slate-200 shrink-0">
              {selectedOption.badge}
            </span>
          )}
        </div>

        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 shrink-0 transition-transform duration-200 ${
            isOpen ? "rotate-180 text-emerald-600" : ""
          }`}
        />
      </button>

      {/* Animated Dropdown Menu Popover */}
      {isOpen && (
        <div
          className={`absolute left-0 right-0 ${
            openDirection === "up"
              ? "bottom-full mb-1.5 origin-bottom"
              : "top-full mt-1.5 origin-top"
          } bg-white/98 backdrop-blur-md border border-slate-200/90 rounded-md shadow-2xl p-1 z-50 animate-in fade-in-0 zoom-in-95 duration-150 ring-1 ring-slate-900/10 select-none`}
        >
          {searchable && (
            <div className="p-1.5 border-b border-slate-100 mb-1">
              <div className="relative flex items-center">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2 pointer-events-none" />
                <input
                  ref={searchInputRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={searchPlaceholder}
                  className="w-full bg-slate-50 border border-slate-200/90 rounded-sm pl-7 pr-7 py-1 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 focus:bg-white transition-colors"
                />
                {search && (
                  <button
                    type="button"
                    onClick={() => setSearch("")}
                    className="absolute right-2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Options List */}
          <div className="max-h-48 sm:max-h-52 overflow-y-auto space-y-0.5 pr-0.5 custom-scrollbar">
            {filteredOptions.length === 0 ? (
              <div className="py-4 text-center text-xs text-slate-400 font-medium">
                No matches found
              </div>
            ) : (
              filteredOptions.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                      setSearch("");
                    }}
                    className={`w-full flex items-center justify-between gap-2 px-2.5 py-1.5 rounded-xs text-xs transition-colors cursor-pointer text-left ${
                      isSelected
                        ? "bg-emerald-50 text-emerald-900 font-bold"
                        : "text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-medium"
                    }`}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      {opt.icon && <span className="shrink-0">{opt.icon}</span>}
                      <div className="min-w-0">
                        <span className="block truncate">{opt.label}</span>
                        {opt.description && (
                          <span className="block text-[10px] text-slate-400 font-normal leading-tight truncate">
                            {opt.description}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {opt.badge && (
                        <span className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded-xs bg-slate-100 text-slate-600 border border-slate-200 uppercase">
                          {opt.badge}
                        </span>
                      )}
                      {isSelected && (
                        <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                      )}
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
});
