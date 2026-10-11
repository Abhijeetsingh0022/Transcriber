import React from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "success";
type Size    = "xs" | "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

// Primary = blue; surfaces use white
const variantClasses: Record<Variant, string> = {
  primary:   "bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-sm border-transparent",
  secondary: "bg-white text-slate-700 hover:bg-gray-50 active:bg-gray-100 border-slate-200 shadow-sm",
  ghost:     "bg-transparent text-slate-600 hover:bg-gray-100 hover:text-slate-900 active:bg-gray-200 border-transparent",
  danger:    "bg-red-600 text-white hover:bg-red-700 active:bg-red-800 shadow-sm border-transparent",
  success:   "bg-emerald-600 text-white hover:bg-emerald-700 active:bg-emerald-800 shadow-sm border-transparent",
};

const sizeClasses: Record<Size, string> = {
  xs: "px-2   py-0.5 text-xs  gap-1   rounded-lg h-6",
  sm: "px-3   py-1   text-xs  gap-1.5 rounded-lg h-7",
  md: "px-4   py-2   text-sm  gap-2   rounded-lg h-9",
  lg: "px-5   py-2.5 text-sm  gap-2   rounded-lg h-11",
};

export function Button({
  variant = "secondary",
  size    = "md",
  loading = false,
  icon,
  iconRight,
  children,
  disabled,
  className = "",
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      disabled={isDisabled}
      className={[
        "inline-flex items-center justify-center font-semibold border",
        "transition-all duration-150 cursor-pointer select-none",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1",
        "active:scale-[0.97]",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(" ")}
      {...rest}
    >
      {loading ? (
        <Loader2 className="animate-spin shrink-0 w-3.5 h-3.5" />
      ) : icon ? (
        <span className="shrink-0">{icon}</span>
      ) : null}
      {children && <span className="truncate">{children}</span>}
      {iconRight && !loading && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
}
