import React from "react";

type BadgeVariant = "default" | "primary" | "success" | "warning" | "danger" | "info" | "outline";

interface BadgeProps {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
  className?: string;
  children: React.ReactNode;
}

// Primary = blue brand
const variants: Record<BadgeVariant, string> = {
  default: "bg-gray-100  text-slate-700  border-gray-200",
  primary: "bg-blue-50   text-blue-700   border-blue-200/80",
  success: "bg-emerald-50 text-emerald-700 border-emerald-200/80",
  warning: "bg-amber-50  text-amber-700   border-amber-200/80",
  danger:  "bg-red-50    text-red-700     border-red-200/80",
  info:    "bg-sky-50    text-sky-700     border-sky-200/80",
  outline: "bg-white     text-slate-600   border-slate-300",
};

const dotColors: Record<BadgeVariant, string> = {
  default: "bg-slate-400",
  primary: "bg-blue-500",
  success: "bg-emerald-500",
  warning: "bg-amber-500",
  danger:  "bg-red-500",
  info:    "bg-sky-500",
  outline: "bg-slate-400",
};

const sizes = {
  sm: "px-1.5 py-0.5 text-[10px] gap-1   rounded-lg",
  md: "px-2   py-0.5 text-xs     gap-1.5 rounded-lg",
};

export function Badge({ variant = "default", size = "md", dot, className = "", children }: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center font-semibold border",
        variants[variant],
        sizes[size],
        className,
      ].join(" ")}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotColors[variant]}`} />}
      {children}
    </span>
  );
}
