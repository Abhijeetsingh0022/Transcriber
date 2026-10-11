"use client";

import { useState, useEffect, useCallback } from "react";
import { API_BASE, apiFetch } from "../api";
import type { Job } from "../../types";

function notify(title: string, body: string) {
  if (typeof window === "undefined" || !("Notification" in window)) return;
  if (Notification.permission === "granted") {
    new Notification(title, { body });
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission().then((p) => {
      if (p === "granted") new Notification(title, { body });
    });
  }
}

export function useJobs(pollMs = 15000) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchJobs = useCallback(async () => {
    // Skip background polling if tab is minimized or hidden
    if (typeof document !== "undefined" && document.hidden) return;
    try {
      const data = await apiFetch<{ jobs: Job[] }>("/jobs?limit=100");
      setJobs(data.jobs ?? []);
    } catch {
      // keep stale data on transient errors
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();

    // Relaxed safety-net interval (15s default); SSE handles real-time updates instantly
    const interval = setInterval(fetchJobs, pollMs);

    const onVisibilityChange = () => {
      if (!document.hidden) fetchJobs();
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    // SSE for real-time progress & completion events
    let es: EventSource | null = null;
    try {
      es = new EventSource(`${API_BASE}/events`);

      es.addEventListener("job_progress", (e) => {
        try {
          const p = JSON.parse(e.data);
          setJobs((prev) =>
            prev.map((j) =>
              j.id === p.job_id
                ? { ...j, progress: p.progress, current_stage: p.stage, status: p.status ?? j.status }
                : j
            )
          );
        } catch {}
      });

      es.addEventListener("job_completed", (e) => {
        fetchJobs();
        try {
          const data = JSON.parse(e.data);
          notify(
            "Transcription Complete",
            data.filename
              ? `Finished transcribing ${data.filename}`
              : "Your audio has been transcribed successfully."
          );
        } catch {
          notify("Transcription Complete", "Your audio has been transcribed successfully.");
        }
      });

      es.addEventListener("job_failed", (e) => {
        fetchJobs();
        try {
          const data = JSON.parse(e.data);
          notify("Transcription Failed", data.error || "A processing error occurred.");
        } catch {
          notify("Transcription Failed", "A processing error occurred.");
        }
      });
    } catch {}

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      es?.close();
    };
  }, [fetchJobs, pollMs]);

  return { jobs, loading, refetch: fetchJobs, setJobs };
}
