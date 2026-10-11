import React from "react";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
  noPadding?: boolean;
  children: React.ReactNode;
}

export function Card({ hoverable, noPadding, className = "", children, ...rest }: CardProps) {
  return (
    <div
      className={[
        // White card on off-white canvas
        "bg-white border border-gray-200/80 rounded-lg shadow-sm",
        hoverable
          ? "transition-all duration-200 hover:shadow-md hover:border-blue-200/60 hover:-translate-y-px cursor-pointer"
          : "",
        noPadding ? "" : "p-5",
        className,
      ].join(" ")}
      {...rest}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export function CardHeader({ title, subtitle, actions, className = "" }: CardHeaderProps) {
  return (
    <div className={`flex items-start justify-between gap-3 ${className}`}>
      <div>
        <div className="font-semibold text-slate-900 text-sm">{title}</div>
        {subtitle && <div className="text-xs text-slate-500 mt-0.5">{subtitle}</div>}
      </div>
      {actions && <div className="shrink-0 flex items-center gap-1.5">{actions}</div>}
    </div>
  );
}
