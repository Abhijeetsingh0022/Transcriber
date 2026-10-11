/**
 * API layer — single source for base URL and typed helpers.
 * All components import from here; never hardcode the base URL elsewhere.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined"
    ? window.location.port === "3000"
      ? `${window.location.protocol}//${window.location.hostname}:8000/api`
      : "/api"
    : "http://127.0.0.1:8000/api");

// In-flight deduplication cache for concurrent GET requests
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const inFlightRequests = new Map<string, Promise<any>>();

// ETag and cached data store for conditional HTTP 304 handling
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const etagStore = new Map<string, { etag: string; data: any }>();

/** GET with JSON response; throws on non-2xx */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || "GET").toUpperCase();
  if (method === "GET") {
    const key = `${path}::${init?.headers ? JSON.stringify(init.headers) : ""}`;
    const existing = inFlightRequests.get(key);
    if (existing) {
      return existing as Promise<T>;
    }
    const promise = (async () => {
      try {
        const cached = etagStore.get(path);
        const headers = new Headers(init?.headers || {});
        if (cached?.etag && !headers.has("If-None-Match")) {
          headers.set("If-None-Match", cached.etag);
        }

        const res = await fetch(`${API_BASE}${path}`, {
          ...init,
          headers,
        });

        if (res.status === 304 && cached) {
          return cached.data as T;
        }

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new ApiError(res.status, body?.detail ?? res.statusText);
        }

        const data = (await res.json()) as T;
        const etag = res.headers.get("ETag");
        if (etag) {
          etagStore.set(path, { etag, data });
        }
        return data;
      } finally {
        inFlightRequests.delete(key);
      }
    })();
    inFlightRequests.set(key, promise);
    return promise;
  }

  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.detail ?? res.statusText);
  }
  // Invalidate cached query results on mutating operations
  etagStore.clear();
  return res.json() as Promise<T>;
}

/** POST JSON */
export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  return apiFetch<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

/** POST FormData */
export async function apiPostForm<T>(path: string, form: FormData): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: form });
}

/** DELETE */
export async function apiDelete(path: string): Promise<void> {
  await apiFetch<void>(path, { method: "DELETE" });
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Settings & Model API Endpoints ──────────────────────────────
import type {
  ApiKeySettings,
  VerifyKeyResponse,
  ModelStatus,
  DownloadStatus,
  StorageInfo,
  ExecutiveIntelligence,
  AudioMarker,
  SearchResultItem,
} from "../types";

export async function fetchApiKeys(): Promise<ApiKeySettings> {
  return apiFetch<ApiKeySettings>("/settings/keys");
}

export async function saveApiKeys(payload: {
  gemini_key?: string;
  openrouter_key?: string;
  tokenharbor_key?: string;
}): Promise<ApiKeySettings & { success: boolean; message: string }> {
  return apiPost<ApiKeySettings & { success: boolean; message: string }>(
    "/settings/keys",
    payload
  );
}

export async function addApiKey(
  provider: "gemini" | "openrouter" | "tokenharbor",
  key: string
): Promise<ApiKeySettings> {
  return apiPost<ApiKeySettings>("/settings/keys/add", { provider, key });
}

export async function removeApiKey(
  provider: "gemini" | "openrouter" | "tokenharbor",
  keyIndex?: number,
  key?: string
): Promise<ApiKeySettings> {
  return apiPost<ApiKeySettings>("/settings/keys/remove", {
    provider,
    key_index: keyIndex,
    key,
  });
}

export async function verifyApiKey(
  provider: "gemini" | "openrouter" | "tokenharbor",
  key?: string,
  keyIndex?: number
): Promise<VerifyKeyResponse> {
  return apiPost<VerifyKeyResponse>("/settings/keys/verify", {
    provider,
    key,
    key_index: keyIndex,
  });
}

export async function fetchModels(): Promise<ModelStatus[]> {
  return apiFetch<ModelStatus[]>("/settings/models");
}

export async function startModelDownload(
  tier: string
): Promise<DownloadStatus> {
  return apiPost<DownloadStatus>(`/settings/models/${tier}/download`, {});
}

export async function fetchModelDownloadStatus(
  tier: string
): Promise<DownloadStatus> {
  return apiFetch<DownloadStatus>(`/settings/models/${tier}/download/status`);
}

export async function deleteModel(
  tier: string
): Promise<{ success: boolean; freed_mb: number; message: string }> {
  return apiFetch<{ success: boolean; freed_mb: number; message: string }>(
    `/settings/models/${tier}`,
    { method: "DELETE" }
  );
}

export async function fetchStorageInfo(): Promise<StorageInfo> {
  return apiFetch<StorageInfo>("/settings/storage");
}

export async function polishTranscript(
  jobId: string
): Promise<{ success: boolean; job_id: string; updated_segments: number }> {
  return apiPost<{ success: boolean; job_id: string; updated_segments: number }>(
    `/jobs/${jobId}/polish_transcript`,
    {}
  );
}

export async function fetchJobIntelligence(
  jobId: string
): Promise<ExecutiveIntelligence> {
  return apiFetch<ExecutiveIntelligence>(`/jobs/${jobId}/intelligence`);
}

export async function generateJobIntelligence(
  jobId: string
): Promise<ExecutiveIntelligence> {
  return apiPost<ExecutiveIntelligence>(`/jobs/${jobId}/intelligence/generate`, {});
}

export async function exportJobIntelligence(
  jobId: string,
  format = "markdown"
): Promise<{ job_id: string; format: string; content: string }> {
  return apiFetch<{ job_id: string; format: string; content: string }>(
    `/jobs/${jobId}/intelligence/export?format=${format}`
  );
}

// ── Audio Markers (Pins & Bookmarks) ───────────────────────────
export async function fetchJobMarkers(jobId: string): Promise<AudioMarker[]> {
  return apiFetch<AudioMarker[]>(`/jobs/${jobId}/markers`);
}

export async function saveJobMarker(
  jobId: string,
  marker: { id?: string; time: number; label: string; tag?: string }
): Promise<AudioMarker> {
  return apiPost<AudioMarker>(`/jobs/${jobId}/markers`, marker);
}

export async function deleteJobMarker(
  jobId: string,
  markerId: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/jobs/${jobId}/markers/${markerId}`, {
    method: "DELETE",
  });
}

// ── Full-Text Search (SQLite FTS5) ──────────────────────────────
export async function searchTranscripts(
  query: string,
  jobId?: string,
  limit = 50
): Promise<{ query: string; results: SearchResultItem[] }> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (jobId) params.append("job_id", jobId);
  return apiFetch<{ query: string; results: SearchResultItem[] }>(
    `/search?${params.toString()}`
  );
}

