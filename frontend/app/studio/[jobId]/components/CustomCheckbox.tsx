"use client";

import React, { memo } from "react";
import { Check } from "lucide-react";

export interface CustomCheckboxProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: React.ReactNode;
  description?: string;
  disabled?: boolean;
  className?: string;
  id?: string;
  size?: "sm" | "md" | "lg";
  ariaLabel?: string;
}

export const CustomCheckbox = memo(function CustomCheckbox({
  checked,
  onChange,
  label,
  description,
  disabled = false,
  className = "",
  id,
  size = "md",
  ariaLabel,
}: CustomCheckboxProps) {
  const autoId = React.useId();
  const inputId = id || autoId;
  const computedAria =
    ariaLabel || (typeof label === "string" ? label : description) || "Checkbox";

  const boxSize =
    size === "sm"
      ? "w-4 h-4 rounded-[2px]"
      : size === "lg"
      ? "w-6 h-6 rounded-[3px]"
      : "w-5 h-5 rounded-[2px]";

  const iconSize =
    size === "sm" ? "w-2.5 h-2.5" : size === "lg" ? "w-4 h-4" : "w-3.5 h-3.5";

  return (
    <label
      htmlFor={inputId}
      className={`inline-flex items-center gap-2.5 select-none transition-all ${
        disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
      } ${className}`}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="relative flex items-center justify-center shrink-0">
        <input
          id={inputId}
          type="checkbox"
          checked={checked}
          disabled={disabled}
          aria-label={computedAria}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />

        {/* Custom Visual Box */}
        <div
          className={`${boxSize} flex items-center justify-center border transition-all duration-150 peer-focus-visible:ring-2 peer-focus-visible:ring-emerald-500 peer-focus-visible:ring-offset-1 ${
            checked
              ? "bg-emerald-600 border-emerald-600 text-white shadow-xs ring-2 ring-emerald-500/20"
              : "bg-white border-slate-300 hover:border-slate-400 bg-gradient-to-b from-white to-slate-50/80 shadow-2xs"
          } ${disabled ? "bg-slate-100 border-slate-200" : ""}`}
        >
          {checked && (
            <Check
              className={`${iconSize} text-white stroke-[3] animate-in zoom-in-75 duration-100`}
            />
          )}
        </div>
      </div>

      {(label || description) && (
        <div className="min-w-0">
          {label && (
            <span
              className={`text-xs block font-semibold transition-colors leading-tight ${
                checked ? "text-slate-900" : "text-slate-700"
              }`}
            >
              {label}
            </span>
          )}
          {description && (
            <span className="text-[11px] text-slate-500 block mt-0.5 leading-normal">
              {description}
            </span>
          )}
        </div>
      )}
    </label>
  );
});
