"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "../api";
import type { SystemTelemetry } from "../../types";

export function useTelemetry(pollMs = 10000) {
  const [telemetry, setTelemetry] = useState<SystemTelemetry | null>(null);

  const fetch = useCallback(async () => {
    // Skip polling if the browser tab is not visible
    if (typeof document !== "undefined" && document.hidden) return;
    try {
      const data = await apiFetch<SystemTelemetry>("/system/status");
      setTelemetry(data);
    } catch {}
  }, []);

  useEffect(() => {
    fetch();
    const id = setInterval(fetch, pollMs);

    const onVisible = () => {
      if (!document.hidden) fetch();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [fetch, pollMs]);

  return { telemetry, refetch: fetch };
}
