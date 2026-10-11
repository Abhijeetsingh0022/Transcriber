"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  X,
  Key,
  Cpu,
  Eye,
  EyeOff,
  Check,
  AlertCircle,
  ExternalLink,
  Loader2,
  Trash2,
  Download,
  HardDrive,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  Folder,
  Plus,
  Layers,
  Copy,
  Zap,
  ArrowRight,
  Sliders,
  Sparkles,
} from "lucide-react";
import {
  fetchApiKeys,
  saveApiKeys,
  verifyApiKey,
  addApiKey,
  removeApiKey,
  fetchModels,
  startModelDownload,
  deleteModel,
  fetchStorageInfo,
} from "../lib/api";
import {
  ApiKeySettings,
  KeyPoolItem,
  ModelStatus,
  StorageInfo,
  VerifyKeyResponse,
} from "../types";

// ── Provider Color Theming Helper ──────────────────────────────────────────
interface ProviderTheme {
  border: string;
  badgeBg: string;
  badgeText: string;
  badgeBorder: string;
  activeAccent: string;
  iconBg: string;
  iconText: string;
}

const PROVIDER_THEMES: Record<"gemini" | "openrouter" | "tokenharbor", ProviderTheme> = {
  gemini: {
    border: "border-blue-200/90",
    badgeBg: "bg-blue-50",
    badgeText: "text-blue-700",
    badgeBorder: "border-blue-200/80",
    activeAccent: "text-blue-600",
    iconBg: "bg-blue-500/10",
    iconText: "text-blue-600",
  },
  openrouter: {
    border: "border-cyan-200/90",
    badgeBg: "bg-cyan-50",
    badgeText: "text-cyan-700",
    badgeBorder: "border-cyan-200/80",
    activeAccent: "text-cyan-600",
    iconBg: "bg-cyan-500/10",
    iconText: "text-cyan-600",
  },
  tokenharbor: {
    border: "border-emerald-200/90",
    badgeBg: "bg-emerald-50",
    badgeText: "text-emerald-700",
    badgeBorder: "border-emerald-200/80",
    activeAccent: "text-emerald-600",
    iconBg: "bg-emerald-500/10",
    iconText: "text-emerald-600",
  },
};

interface ProviderKeySectionProps {
  title: string;
  provider: "gemini" | "openrouter" | "tokenharbor";
  tierTag: string;
  tierNumber: number;
  dashboardUrl: string;
  dashboardLabel: string;
  placeholder: string;
  keysList?: KeyPoolItem[];
  configured: boolean;
  inputValue: string;
  setInputValue: (v: string) => void;
  showPassword: boolean;
  setShowPassword: (v: boolean) => void;
  onAddKey: () => void;
  onRemoveKeyItem: (idx: number) => void;
  onVerifyKeyItem: (idx?: number, rawKey?: string) => void;
  keyVerifications: Record<string, { loading: boolean; result?: VerifyKeyResponse }>;
  isSavingKeys: boolean;
}

function ProviderKeySection({
  title,
  provider,
  tierTag,
  tierNumber,
  dashboardUrl,
  dashboardLabel,
  placeholder,
  keysList = [],
  configured,
  inputValue,
  setInputValue,
  showPassword,
  setShowPassword,
  onAddKey,
  onRemoveKeyItem,
  onVerifyKeyItem,
  keyVerifications,
  isSavingKeys,
}: ProviderKeySectionProps) {
  const poolCount = keysList.length;
  const inputTestState = keyVerifications[`${provider}:input`];
  const theme = PROVIDER_THEMES[provider];

  return (
    <div className="bg-white border border-slate-200/90 rounded-xl p-4 sm:p-5 shadow-2xs space-y-4 hover:border-slate-300 transition-colors">
      {/* Header Row */}
      <div className="flex items-center justify-between flex-wrap gap-2.5">
        <div className="flex items-center gap-2.5">
          <div
            className={`w-8 h-8 rounded-lg ${theme.iconBg} flex items-center justify-center ${theme.iconText} font-bold text-xs shrink-0`}
          >
            T{tierNumber}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-bold text-slate-900">{title}</span>
              <span className={`text-[10px] font-semibold ${theme.badgeBg} ${theme.badgeText} px-2 py-0.5 rounded border ${theme.badgeBorder}`}>
                {tierTag}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 font-medium mt-0.5">
              {provider === "gemini"
                ? "Studio reasoning, speaker identification & executive intelligence"
                : provider === "openrouter"
                ? "Secondary multi-model cluster fallback"
                : "Tertiary failover reasoning relay"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {poolCount > 1 ? (
            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-blue-50 text-blue-700 border border-blue-200/80 flex items-center gap-1.5 shadow-2xs">
              <Layers className="w-3 h-3 text-blue-600" />
              <span>{poolCount} Keys (Load-Balanced)</span>
            </span>
          ) : poolCount === 1 ? (
            <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80 flex items-center gap-1.5 shadow-2xs">
              <Check className="w-3 h-3 text-emerald-600" />
              <span>1 Key Configured</span>
            </span>
          ) : (
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-500 border border-slate-200">
              {provider === "gemini" ? "Not Configured" : "Standby (Optional)"}
            </span>
          )}

          <a
            href={dashboardUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] font-semibold text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1 transition-colors px-2 py-1 rounded hover:bg-blue-50"
          >
            <span>{dashboardLabel}</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Key Pool Roster (If keys exist) */}
      {poolCount > 0 && (
        <div className="space-y-2 bg-slate-50/70 border border-slate-200/80 rounded-xl p-3">
          <div className="flex items-center justify-between text-[11px] text-slate-600 font-semibold px-1">
            <span className="flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-slate-400" />
              <span>Active Key Pool ({poolCount})</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono">
              Intra-provider failover on HTTP 429
            </span>
          </div>

          <div className="space-y-1.5">
            {keysList.map((kItem, idx) => {
              const testKey = `${provider}:${idx}`;
              const testState = keyVerifications[testKey];
              return (
                <div
                  key={kItem.id ?? idx}
                  className="flex items-center justify-between gap-2.5 p-2 rounded-lg bg-white border border-slate-200/90 shadow-2xs hover:border-slate-300 transition-colors"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold shrink-0 ${
                        idx === 0
                          ? "bg-blue-50 text-blue-700 border border-blue-200/70"
                          : "bg-slate-100 text-slate-600 border border-slate-200"
                      }`}
                    >
                      #{idx + 1} {idx === 0 ? "Primary" : "Failover"}
                    </span>
                    <span className="font-mono text-xs text-slate-800 font-semibold truncate tracking-wider">
                      {kItem.masked}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    {testState?.result && (
                      <span
                        className={`text-[10px] font-medium px-2 py-0.5 rounded border flex items-center gap-1 ${
                          testState.result.rate_limited
                            ? "bg-amber-50 text-amber-700 border-amber-200"
                            : testState.result.valid
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200"
                        }`}
                      >
                        {testState.result.rate_limited ? (
                          <>
                            <AlertCircle className="w-2.5 h-2.5 text-amber-600" />
                            <span title={testState.result.error || "Rate limited"}>
                              Quota ({testState.result.latency_ms}ms)
                            </span>
                          </>
                        ) : testState.result.valid ? (
                          <>
                            <Check className="w-2.5 h-2.5 text-emerald-600" />
                            <span>{testState.result.latency_ms}ms</span>
                          </>
                        ) : (
                          <>
                            <AlertCircle className="w-2.5 h-2.5 text-rose-600" />
                            <span className="max-w-[120px] truncate" title={testState.result.error}>
                              {testState.result.error || "Failed"}
                            </span>
                          </>
                        )}
                      </span>
                    )}

                    <button
                      type="button"
                      onClick={() => onVerifyKeyItem(idx)}
                      disabled={testState?.loading || isSavingKeys}
                      className="px-2.5 py-1 rounded-md border border-slate-200/80 bg-slate-50 hover:bg-slate-100 text-slate-700 hover:text-slate-900 text-[11px] font-semibold flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50"
                      title="Test connection & latency for this key"
                    >
                      {testState?.loading ? (
                        <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                      ) : (
                        <RefreshCw className="w-3 h-3 text-slate-400" />
                      )}
                      <span>Test</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => onRemoveKeyItem(idx)}
                      disabled={isSavingKeys}
                      className="p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer disabled:opacity-50"
                      title="Remove key from pool"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Input Row for Adding a Key */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type={showPassword ? "text" : "password"}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && inputValue.trim()) {
                  e.preventDefault();
                  onAddKey();
                }
              }}
              placeholder={
                poolCount > 0
                  ? "Enter additional key to expand pool and balance load..."
                  : placeholder
              }
              className="w-full bg-slate-50/50 border border-slate-200 rounded-lg px-3 py-2 pr-10 text-xs font-mono text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 focus:bg-white transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              title={showPassword ? "Hide key" : "Show key"}
            >
              {showPassword ? (
                <EyeOff className="w-3.5 h-3.5" />
              ) : (
                <Eye className="w-3.5 h-3.5" />
              )}
            </button>
          </div>

          <button
            type="button"
            onClick={onAddKey}
            disabled={isSavingKeys || !inputValue.trim()}
            className="px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-40 disabled:pointer-events-none active:scale-95 cursor-pointer shrink-0 shadow-2xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>{poolCount > 0 ? "Add to Pool" : "Add Key"}</span>
          </button>
        </div>

        {/* Live Test for Typed Key Before Saving */}
        {inputValue.trim() && (
          <div className="flex items-center justify-between flex-wrap gap-2 pt-1">
            <button
              type="button"
              onClick={() => onVerifyKeyItem(undefined, inputValue.trim())}
              disabled={inputTestState?.loading || isSavingKeys}
              className="px-2.5 py-1 rounded-md border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-[11px] font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs disabled:opacity-50"
            >
              {inputTestState?.loading ? (
                <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
              ) : (
                <RefreshCw className="w-3 h-3 text-slate-500" />
              )}
              <span>Test Key Before Adding</span>
            </button>

            {inputTestState?.result && (
              <span
                className={`text-[11px] font-medium px-2 py-0.5 rounded border flex items-center gap-1.5 ${
                  inputTestState.result.rate_limited
                    ? "bg-amber-50 text-amber-800 border-amber-200"
                    : inputTestState.result.valid
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : "bg-rose-50 text-rose-800 border-rose-200"
                }`}
              >
                {inputTestState.result.rate_limited ? (
                  <>
                    <AlertCircle className="w-3 h-3 text-amber-600" />
                    <span>Rate limit / quota exceeded ({inputTestState.result.latency_ms}ms)</span>
                  </>
                ) : inputTestState.result.valid ? (
                  <>
                    <Check className="w-3 h-3 text-emerald-600" />
                    <span>Valid connection ({inputTestState.result.latency_ms}ms)</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3 h-3 text-rose-600" />
                    <span className="max-w-xs truncate">
                      {inputTestState.result.error || "Invalid key"}
                    </span>
                  </>
                )}
              </span>
            )}
          </div>
        )}
      </div>

      {poolCount > 1 && (
        <p className="text-[11px] text-slate-500 bg-blue-50/60 border border-blue-100 rounded-lg p-2 leading-relaxed flex items-center gap-2">
          <Zap className="w-3.5 h-3.5 text-blue-600 shrink-0" />
          <span>
            <strong>Load balancing active:</strong> Requests automatically cycle through all {poolCount} keys. If any key encounters HTTP 429 quota exhaustion, TMUX immediately fails over to the next healthy key with zero user delay.
          </span>
        </p>
      )}
    </div>
  );
}

interface PreferencesModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: "keys" | "models";
}

export function PreferencesModal({
  isOpen,
  onClose,
  initialTab = "keys",
}: PreferencesModalProps) {
  const [activeTab, setActiveTab] = useState<"keys" | "models">(initialTab);

  // ── API Key Management State ──────────────────────────────────────────
  const [keysConfig, setKeysConfig] = useState<ApiKeySettings | null>(null);
  const [geminiInput, setGeminiInput] = useState("");
  const [openrouterInput, setOpenrouterInput] = useState("");
  const [tokenharborInput, setTokenharborInput] = useState("");
  const [showGemini, setShowGemini] = useState(false);
  const [showOpenrouter, setShowOpenrouter] = useState(false);
  const [showTokenharbor, setShowTokenharbor] = useState(false);
  const [isSavingKeys, setIsSavingKeys] = useState(false);
  const [saveBanner, setSaveBanner] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const [keyVerifications, setKeyVerifications] = useState<
    Record<string, { loading: boolean; result?: VerifyKeyResponse }>
  >({});

  // ── Local Model Management State ──────────────────────────────────────
  const [models, setModels] = useState<ModelStatus[]>([]);
  const [storage, setStorage] = useState<StorageInfo | null>(null);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [deletingTier, setDeletingTier] = useState<string | null>(null);
  const [modelActionBanner, setModelActionBanner] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);
  const [copiedPath, setCopiedPath] = useState(false);

  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Reset tab on open
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      loadKeys();
      loadModelsAndStorage();
    } else {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    }
  }, [isOpen, initialTab]);

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // ── Data Fetching ─────────────────────────────────────────────────────
  const loadKeys = async () => {
    try {
      const data = await fetchApiKeys();
      setKeysConfig(data);
    } catch {
      // Offline or network error
    }
  };

  const loadModelsAndStorage = useCallback(async () => {
    try {
      setIsLoadingModels(true);
      const [modelsData, storageData] = await Promise.all([
        fetchModels(),
        fetchStorageInfo(),
      ]);
      setModels(modelsData);
      setStorage(storageData);
    } catch {
      // Handled silently
    } finally {
      setIsLoadingModels(false);
    }
  }, []);

  // Continuous background polling when any model is downloading
  useEffect(() => {
    if (!isOpen) return;
    const hasDownloading = models.some(
      (m) => m.download_status === "downloading"
    );

    if (hasDownloading && !pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        try {
          const updated = await fetchModels();
          setModels(updated);
          const stillDownloading = updated.some(
            (m) => m.download_status === "downloading"
          );
          if (!stillDownloading && pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
            // Also refresh storage
            fetchStorageInfo().then(setStorage).catch(() => {});
          }
        } catch {
          // ignore
        }
      }, 1500);
    } else if (!hasDownloading && pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [isOpen, models]);

  // ── Key Actions ───────────────────────────────────────────────────────
  const handleAddKey = async (provider: "gemini" | "openrouter" | "tokenharbor") => {
    const rawKey =
      provider === "gemini"
        ? geminiInput.trim()
        : provider === "openrouter"
        ? openrouterInput.trim()
        : tokenharborInput.trim();
    if (!rawKey) return;

    setIsSavingKeys(true);
    setSaveBanner(null);
    try {
      const res = await addApiKey(provider, rawKey);
      setKeysConfig(res);
      if (provider === "gemini") setGeminiInput("");
      else if (provider === "openrouter") setOpenrouterInput("");
      else setTokenharborInput("");

      const name =
        provider === "gemini"
          ? "Gemini"
          : provider === "openrouter"
          ? "OpenRouter"
          : "Token Harbor";
      const count =
        (provider === "gemini"
          ? res.gemini_count
          : provider === "openrouter"
          ? res.openrouter_count
          : res.tokenharbor_count) || 1;
      setSaveBanner({
        type: "success",
        text: `Key added to ${name} pool. Requests will load-balance across ${count} key${count > 1 ? "s" : ""} with automatic 429 failover.`,
      });
      setTimeout(() => setSaveBanner(null), 4000);
    } catch (err: unknown) {
      setSaveBanner({
        type: "error",
        text: (err as Error)?.message || "Failed to add API key.",
      });
    } finally {
      setIsSavingKeys(false);
    }
  };

  const handleRemoveKeyItem = async (
    provider: "gemini" | "openrouter" | "tokenharbor",
    keyIndex: number
  ) => {
    setIsSavingKeys(true);
    setSaveBanner(null);
    try {
      const res = await removeApiKey(provider, keyIndex);
      setKeysConfig(res);
      const name =
        provider === "gemini"
          ? "Gemini"
          : provider === "openrouter"
          ? "OpenRouter"
          : "Token Harbor";
      setSaveBanner({
        type: "success",
        text: `Removed key #${keyIndex + 1} from ${name} pool.`,
      });
      setTimeout(() => setSaveBanner(null), 4000);
    } catch (err: unknown) {
      setSaveBanner({
        type: "error",
        text: (err as Error)?.message || "Failed to remove key.",
      });
    } finally {
      setIsSavingKeys(false);
    }
  };

  const handleVerifyKeyItem = async (
    provider: "gemini" | "openrouter" | "tokenharbor",
    keyIndex?: number,
    rawKey?: string
  ) => {
    const vKey = `${provider}:${keyIndex !== undefined ? keyIndex : "input"}`;
    setKeyVerifications((prev) => ({
      ...prev,
      [vKey]: { loading: true },
    }));

    try {
      const res = await verifyApiKey(provider, rawKey, keyIndex);
      setKeyVerifications((prev) => ({
        ...prev,
        [vKey]: { loading: false, result: res },
      }));
    } catch (err: unknown) {
      const msg = (err as Error)?.message || "";
      const isNet =
        msg.includes("Load failed") ||
        msg.includes("Failed to fetch") ||
        msg.includes("NetworkError");
      const errorResult: VerifyKeyResponse = {
        valid: false,
        error: isNet ? "Backend unreachable" : msg || "Verification request failed.",
      };
      setKeyVerifications((prev) => ({
        ...prev,
        [vKey]: { loading: false, result: errorResult },
      }));
    }
  };

  const handleSaveKeys = async () => {
    setIsSavingKeys(true);
    setSaveBanner(null);
    try {
      const tasks: Promise<unknown>[] = [];
      if (geminiInput.trim()) tasks.push(addApiKey("gemini", geminiInput.trim()));
      if (openrouterInput.trim()) tasks.push(addApiKey("openrouter", openrouterInput.trim()));
      if (tokenharborInput.trim()) tasks.push(addApiKey("tokenharbor", tokenharborInput.trim()));

      if (tasks.length > 0) {
        await Promise.all(tasks);
        const res = await fetchApiKeys();
        setKeysConfig(res);
        setGeminiInput("");
        setOpenrouterInput("");
        setTokenharborInput("");
        setSaveBanner({
          type: "success",
          text: "API keys added to active pools and stored in safe storage.",
        });
      } else {
        const res = await fetchApiKeys();
        setKeysConfig(res);
        setSaveBanner({
          type: "success",
          text: "API key configuration up to date.",
        });
      }
      setTimeout(() => setSaveBanner(null), 4000);
    } catch (err: unknown) {
      setSaveBanner({
        type: "error",
        text: (err as Error)?.message || "Failed to save API keys.",
      });
    } finally {
      setIsSavingKeys(false);
    }
  };

  // ── Model Actions ─────────────────────────────────────────────────────
  const handleStartDownload = async (tier: string) => {
    setModelActionBanner(null);
    try {
      // Optimistic update
      setModels((prev) =>
        prev.map((m) =>
          m.id === tier
            ? { ...m, download_status: "downloading", download_progress: 0 }
            : m
        )
      );
      await startModelDownload(tier);
      // Trigger instant poll
      const updated = await fetchModels();
      setModels(updated);
    } catch (err: unknown) {
      setModelActionBanner({
        type: "error",
        text: (err as Error)?.message || `Failed to initiate download for ${tier}.`,
      });
      loadModelsAndStorage();
    }
  };

  const handleDeleteModel = async (tier: string, name: string) => {
    if (
      !window.confirm(
        `Are you sure you want to remove ${name} weights from local disk? You can redownload anytime.`
      )
    ) {
      return;
    }
    setDeletingTier(tier);
    setModelActionBanner(null);
    try {
      const res = await deleteModel(tier);
      setModelActionBanner({
        type: "success",
        text: res.message || `Removed ${name} — freed ${res.freed_mb} MB of disk space.`,
      });
      setTimeout(() => setModelActionBanner(null), 4000);
      await loadModelsAndStorage();
    } catch (err: unknown) {
      setModelActionBanner({
        type: "error",
        text: (err as Error)?.message || `Failed to delete ${name}.`,
      });
    } finally {
      setDeletingTier(null);
    }
  };

  const handleCopyPath = () => {
    if (!storage?.models_directory) return;
    navigator.clipboard.writeText(storage.models_directory);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 2000);
  };

  const totalKeysConfigured =
    (keysConfig?.gemini_keys?.length ?? 0) +
    (keysConfig?.openrouter_keys?.length ?? 0) +
    (keysConfig?.tokenharbor_keys?.length ?? 0);

  const installedModelsCount = models.filter((m) => m.is_installed).length;
  const isAnyDownloading = models.some((m) => m.download_status === "downloading");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-2.5 sm:p-5 md:p-6 animate-in fade-in duration-200">
      <div
        className="bg-white rounded-2xl border border-slate-200/90 shadow-2xl w-full max-w-5xl h-[92vh] max-h-[820px] flex flex-col overflow-hidden animate-popover"
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Modal Workstation Top Header ──────────────────────────────── */}
        <div className="px-5 sm:px-6 py-4 border-b border-slate-200/80 flex items-center justify-between shrink-0 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-50 border border-blue-200/70 flex items-center justify-center text-blue-600 shadow-2xs shrink-0">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 text-sm sm:text-base leading-snug">
                  Preferences &amp; Engine Manager
                </h3>
                <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200/70 font-mono tracking-wider">
                  TMUX WORKSTATION
                </span>
              </div>
              <p className="text-xs text-slate-500 font-medium">
                Cloud AI cascade, offline Faster-Whisper weights, and storage management
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Live Status Pill */}
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200/80 text-[11px] font-semibold text-emerald-800 shadow-2xs">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Engine Ready</span>
            </div>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-slate-700 p-2 rounded-xl hover:bg-slate-100 transition-colors cursor-pointer"
              title="Close modal (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Responsive Body (Desktop Sidebar + Main Work Area) ────────── */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden bg-slate-50/40">
          {/* Left Sidebar Navigation */}
          <div className="w-full md:w-64 border-b md:border-b-0 md:border-r border-slate-200/80 bg-slate-50/70 p-3 sm:p-4 flex md:flex-col justify-between shrink-0 gap-3">
            {/* Tab Navigation List */}
            <div className="flex md:flex-col gap-1.5 w-full">
              {/* Tab 1: Cloud AI & API Keys */}
              <button
                type="button"
                onClick={() => setActiveTab("keys")}
                className={`flex-1 md:flex-none flex items-center justify-between p-2.5 sm:p-3 rounded-xl text-left transition-all cursor-pointer ${
                  activeTab === "keys"
                    ? "bg-slate-900 text-white shadow-xs font-semibold"
                    : "text-slate-700 hover:bg-slate-200/60 font-medium"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      activeTab === "keys"
                        ? "bg-slate-800 text-blue-400"
                        : "bg-white text-slate-500 border border-slate-200"
                    }`}
                  >
                    <Key className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs truncate">Cloud AI &amp; Keys</div>
                    <div
                      className={`text-[10px] truncate hidden md:block ${
                        activeTab === "keys" ? "text-slate-300" : "text-slate-400"
                      }`}
                    >
                      Gemini • OpenRouter • Harbor
                    </div>
                  </div>
                </div>

                {totalKeysConfigured > 0 ? (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full shrink-0 font-bold ${
                      activeTab === "keys"
                        ? "bg-blue-500/20 text-blue-300 border border-blue-400/30"
                        : "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    }`}
                  >
                    {totalKeysConfigured}
                  </span>
                ) : (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded shrink-0 ${
                      activeTab === "keys"
                        ? "text-slate-400"
                        : "text-slate-400 bg-slate-100"
                    }`}
                  >
                    Optional
                  </span>
                )}
              </button>

              {/* Tab 2: Speech Models & Storage */}
              <button
                type="button"
                onClick={() => setActiveTab("models")}
                className={`flex-1 md:flex-none flex items-center justify-between p-2.5 sm:p-3 rounded-xl text-left transition-all cursor-pointer ${
                  activeTab === "models"
                    ? "bg-slate-900 text-white shadow-xs font-semibold"
                    : "text-slate-700 hover:bg-slate-200/60 font-medium"
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 ${
                      activeTab === "models"
                        ? "bg-slate-800 text-blue-400"
                        : "bg-white text-slate-500 border border-slate-200"
                    }`}
                  >
                    <Cpu className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs truncate">Models &amp; Storage</div>
                    <div
                      className={`text-[10px] truncate hidden md:block ${
                        activeTab === "models" ? "text-slate-300" : "text-slate-400"
                      }`}
                    >
                      Whisper Weights &amp; Cache
                    </div>
                  </div>
                </div>

                {isAnyDownloading ? (
                  <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin shrink-0" />
                ) : installedModelsCount > 0 ? (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full shrink-0 font-bold ${
                      activeTab === "models"
                        ? "bg-blue-500/20 text-blue-300 border border-blue-400/30"
                        : "bg-blue-50 text-blue-700 border border-blue-200"
                    }`}
                  >
                    {installedModelsCount}
                  </span>
                ) : null}
              </button>
            </div>

            {/* Hardware & Diagnostics Sidebar Card (Desktop Only) */}
            <div className="hidden md:block bg-white rounded-xl border border-slate-200/80 p-3.5 space-y-2.5 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-slate-800 flex items-center gap-1.5">
                  <HardDrive className="w-3.5 h-3.5 text-blue-600" />
                  <span>Hardware Core</span>
                </span>
                <span className="text-[10px] font-mono text-emerald-600 font-semibold bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200/70">
                  Apple Silicon MPS
                </span>
              </div>

              <div className="space-y-1 text-[11px] text-slate-600 font-medium">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Precision:</span>
                  <span className="font-mono text-slate-700 font-semibold">int8_float32</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Whisper Backend:</span>
                  <span className="font-mono text-slate-700 font-semibold">faster-whisper</span>
                </div>
                {storage && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Disk Free:</span>
                    <span className="font-mono text-slate-900 font-bold">
                      {storage.free_disk_gb} GB
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-1 border-t border-slate-100 flex items-center gap-1.5 text-[10px] text-emerald-700 font-medium">
                <ShieldCheck className="w-3 h-3 text-emerald-600 shrink-0" />
                <span>100% Offline Resilience</span>
              </div>
            </div>
          </div>

          {/* Right Main Content Area */}
          <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-white">
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
              {/* ═══════════════════════════════════════════════════════════
                  TAB 1: CLOUD AI & API KEYS (BYOK CASCADE)
                  ═══════════════════════════════════════════════════════════ */}
              {activeTab === "keys" && (
                <div className="space-y-6">
                  {/* Visual Cascade Architecture Card */}
                  <div className="bg-slate-50/80 border border-slate-200/90 rounded-2xl p-4 sm:p-5 space-y-3.5">
                    <div className="flex items-center justify-between flex-wrap gap-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-blue-600 shrink-0" />
                        <h4 className="text-xs sm:text-sm font-bold text-slate-900">
                          Multi-Tier Intelligence Cascade &amp; BYOK Architecture
                        </h4>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 bg-white px-2 py-0.5 rounded-full border border-slate-200 shadow-2xs font-semibold">
                        Zero Rate-Limit Interruption
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 leading-relaxed">
                      API keys are completely optional. TMUX Studio executes with an intelligent 3-tier cascade: if Gemini is configured, it powers premium multi-speaker diarization and executive reasoning. If rate-limited, it automatically falls back to OpenRouter or Token Harbor. If offline or no keys are set, the engine falls back to 100% local acoustic models.
                    </p>

                    {/* Flowchart Steps */}
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-1 font-mono text-xs">
                      {/* Tier 1 */}
                      <div
                        className={`p-2.5 rounded-xl border flex flex-col justify-between ${
                          (keysConfig?.gemini_keys?.length ?? 0) > 0
                            ? "bg-blue-50/70 border-blue-200 text-blue-900"
                            : "bg-white border-slate-200 text-slate-600"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold">
                          <span>TIER 1</span>
                          {(keysConfig?.gemini_keys?.length ?? 0) > 0 ? (
                            <span className="text-emerald-600 font-bold">✓ Active</span>
                          ) : (
                            <span className="text-slate-400">Standby</span>
                          )}
                        </div>
                        <div className="font-bold text-xs mt-1">Google Gemini</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">Primary Reasoning</div>
                      </div>

                      {/* Tier 2 */}
                      <div
                        className={`p-2.5 rounded-xl border flex flex-col justify-between ${
                          (keysConfig?.openrouter_keys?.length ?? 0) > 0
                            ? "bg-cyan-50/70 border-cyan-200 text-cyan-900"
                            : "bg-white border-slate-200 text-slate-600"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold">
                          <span>TIER 2</span>
                          {(keysConfig?.openrouter_keys?.length ?? 0) > 0 ? (
                            <span className="text-emerald-600 font-bold">✓ Active</span>
                          ) : (
                            <span className="text-slate-400">Standby</span>
                          )}
                        </div>
                        <div className="font-bold text-xs mt-1">OpenRouter</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">Alternative Pool</div>
                      </div>

                      {/* Tier 3 */}
                      <div
                        className={`p-2.5 rounded-xl border flex flex-col justify-between ${
                          (keysConfig?.tokenharbor_keys?.length ?? 0) > 0
                            ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
                            : "bg-white border-slate-200 text-slate-600"
                        }`}
                      >
                        <div className="flex items-center justify-between text-[10px] font-bold">
                          <span>TIER 3</span>
                          {(keysConfig?.tokenharbor_keys?.length ?? 0) > 0 ? (
                            <span className="text-emerald-600 font-bold">✓ Active</span>
                          ) : (
                            <span className="text-slate-400">Standby</span>
                          )}
                        </div>
                        <div className="font-bold text-xs mt-1">Token Harbor</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">Tertiary Failover</div>
                      </div>

                      {/* Local Fallback */}
                      <div className="p-2.5 rounded-xl border bg-slate-100/80 border-slate-200 text-slate-800 flex flex-col justify-between">
                        <div className="flex items-center justify-between text-[10px] font-bold">
                          <span>OFFLINE</span>
                          <span className="text-emerald-600 font-bold">✓ Ready</span>
                        </div>
                        <div className="font-bold text-xs mt-1">Local TMUX</div>
                        <div className="text-[10px] text-slate-500 mt-0.5">Acoustic Diarization</div>
                      </div>
                    </div>
                  </div>

                  {/* Save Banner Feedback */}
                  {saveBanner && (
                    <div
                      className={`p-3.5 rounded-xl border text-xs flex items-center gap-2.5 ${
                        saveBanner.type === "success"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs"
                          : "bg-rose-50 text-rose-800 border-rose-200 shadow-2xs"
                      }`}
                    >
                      {saveBanner.type === "success" ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                      )}
                      <span className="font-medium">{saveBanner.text}</span>
                    </div>
                  )}

                  {/* Tier 1: Gemini */}
                  <ProviderKeySection
                    title="Google Gemini API Key"
                    provider="gemini"
                    tierTag="Tier 1 • Primary (Recommended)"
                    tierNumber={1}
                    dashboardUrl="https://aistudio.google.com/app/apikey"
                    dashboardLabel="Get key at Google AI Studio"
                    placeholder="AIzaSy..."
                    keysList={keysConfig?.gemini_keys}
                    configured={keysConfig?.gemini_configured ?? false}
                    inputValue={geminiInput}
                    setInputValue={setGeminiInput}
                    showPassword={showGemini}
                    setShowPassword={setShowGemini}
                    onAddKey={() => handleAddKey("gemini")}
                    onRemoveKeyItem={(idx) => handleRemoveKeyItem("gemini", idx)}
                    onVerifyKeyItem={(idx, raw) => handleVerifyKeyItem("gemini", idx, raw)}
                    keyVerifications={keyVerifications}
                    isSavingKeys={isSavingKeys}
                  />

                  {/* Tier 2: OpenRouter */}
                  <ProviderKeySection
                    title="OpenRouter API Key"
                    provider="openrouter"
                    tierTag="Tier 2 • Alternative Multi-Model"
                    tierNumber={2}
                    dashboardUrl="https://openrouter.ai/keys"
                    dashboardLabel="OpenRouter Dashboard"
                    placeholder="sk-or-v1-..."
                    keysList={keysConfig?.openrouter_keys}
                    configured={keysConfig?.openrouter_configured ?? false}
                    inputValue={openrouterInput}
                    setInputValue={setOpenrouterInput}
                    showPassword={showOpenrouter}
                    setShowPassword={setShowOpenrouter}
                    onAddKey={() => handleAddKey("openrouter")}
                    onRemoveKeyItem={(idx) => handleRemoveKeyItem("openrouter", idx)}
                    onVerifyKeyItem={(idx, raw) => handleVerifyKeyItem("openrouter", idx, raw)}
                    keyVerifications={keyVerifications}
                    isSavingKeys={isSavingKeys}
                  />

                  {/* Tier 3: Token Harbor */}
                  <ProviderKeySection
                    title="Token Harbor API Key"
                    provider="tokenharbor"
                    tierTag="Tier 3 • Tertiary Failover"
                    tierNumber={3}
                    dashboardUrl="https://tokenharbor.ai"
                    dashboardLabel="Token Harbor Dashboard"
                    placeholder="thk_live_..."
                    keysList={keysConfig?.tokenharbor_keys}
                    configured={keysConfig?.tokenharbor_configured ?? false}
                    inputValue={tokenharborInput}
                    setInputValue={setTokenharborInput}
                    showPassword={showTokenharbor}
                    setShowPassword={setShowTokenharbor}
                    onAddKey={() => handleAddKey("tokenharbor")}
                    onRemoveKeyItem={(idx) => handleRemoveKeyItem("tokenharbor", idx)}
                    onVerifyKeyItem={(idx, raw) => handleVerifyKeyItem("tokenharbor", idx, raw)}
                    keyVerifications={keyVerifications}
                    isSavingKeys={isSavingKeys}
                  />

                  {/* Save All Keys CTA */}
                  {(geminiInput.trim() || openrouterInput.trim() || tokenharborInput.trim()) && (
                    <div className="p-3.5 bg-blue-50/70 border border-blue-200/90 rounded-xl flex items-center justify-between gap-3 shadow-2xs">
                      <div className="flex items-center gap-2 text-xs text-blue-900 font-medium">
                        <Key className="w-4 h-4 text-blue-600 shrink-0" />
                        <span>You have uncommitted keys typed above. Click below to save all keys simultaneously.</span>
                      </div>
                      <button
                        type="button"
                        onClick={handleSaveKeys}
                        disabled={isSavingKeys}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-2xs active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none flex items-center gap-1.5 cursor-pointer shrink-0"
                      >
                        {isSavingKeys && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                        <span>Save All Unsaved Keys</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════
                  TAB 2: SPEECH MODELS & LOCAL DISK STORAGE
                  ═══════════════════════════════════════════════════════════ */}
              {activeTab === "models" && (
                <div className="space-y-6">
                  {/* Storage Overview Card */}
                  <div className="bg-slate-50/80 border border-slate-200/90 rounded-2xl p-4 sm:p-5 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200/70 flex items-center justify-center text-blue-600 shrink-0">
                          <Folder className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <div className="text-xs font-bold text-slate-900">
                            Hugging Face Weights Cache Path
                          </div>
                          <div
                            className="font-mono text-[11px] text-slate-600 truncate mt-0.5"
                            title={storage?.models_directory}
                          >
                            {storage?.models_directory || "Resolving model cache directory..."}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          type="button"
                          onClick={handleCopyPath}
                          disabled={!storage?.models_directory}
                          className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-2xs disabled:opacity-50"
                        >
                          {copiedPath ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-600" />
                              <span className="text-emerald-700">Copied!</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5 text-slate-400" />
                              <span>Copy Path</span>
                            </>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={loadModelsAndStorage}
                          disabled={isLoadingModels}
                          className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition-all cursor-pointer shadow-2xs disabled:opacity-50"
                          title="Refresh storage and model status"
                        >
                          <RefreshCw
                            className={`w-3.5 h-3.5 ${isLoadingModels ? "animate-spin text-blue-600" : ""}`}
                          />
                        </button>
                      </div>
                    </div>

                    {/* Disk Storage Bar */}
                    {storage && (
                      <div className="space-y-1.5 pt-1 border-t border-slate-200/70">
                        <div className="flex items-center justify-between text-xs font-mono">
                          <span className="text-slate-500">
                            Used:{" "}
                            <strong className="text-slate-800">
                              {(storage.total_disk_gb - storage.free_disk_gb).toFixed(1)} GB
                            </strong>{" "}
                            / {storage.total_disk_gb} GB
                          </span>
                          <span className="text-emerald-700 font-bold">
                            {storage.free_disk_gb} GB Free
                          </span>
                        </div>

                        <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-600 h-full rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(
                                100,
                                Math.max(
                                  3,
                                  ((storage.total_disk_gb - storage.free_disk_gb) /
                                    (storage.total_disk_gb || 1)) *
                                    100
                                )
                              )}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  {modelActionBanner && (
                    <div
                      className={`p-3.5 rounded-xl border text-xs flex items-center gap-2.5 ${
                        modelActionBanner.type === "success"
                          ? "bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs"
                          : "bg-rose-50 text-rose-800 border-rose-200 shadow-2xs"
                      }`}
                    >
                      {modelActionBanner.type === "success" ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      ) : (
                        <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                      )}
                      <span className="font-medium">{modelActionBanner.text}</span>
                    </div>
                  )}

                  {/* 2x2 Workstation Grid of Models */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    {models.map((model) => {
                      const isDownloading = model.download_status === "downloading";
                      const isDeleting = deletingTier === model.id;

                      // Highlight tag helper
                      const isRecommended =
                        model.id === "whale-turbo" || model.id === "whale";

                      return (
                        <div
                          key={model.id}
                          className={`rounded-2xl border p-4 sm:p-5 flex flex-col justify-between transition-all bg-white shadow-2xs space-y-3.5 ${
                            model.is_installed
                              ? "border-slate-200/90 hover:border-slate-300"
                              : "border-slate-200/70 hover:border-slate-300 bg-slate-50/20"
                          }`}
                        >
                          <div className="space-y-2.5">
                            {/* Card Top Title Row */}
                            <div className="flex items-start justify-between gap-2.5">
                              <div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                                    {model.name}
                                  </h4>
                                  <span className="text-[10px] font-mono font-bold text-slate-500 bg-slate-100 px-2 py-0.5 rounded border border-slate-200/70">
                                    {model.label}
                                  </span>
                                  {isRecommended && (
                                    <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200/70">
                                      {model.id === "whale" ? "Studio Master" : "Recommended"}
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                                  {model.description}
                                </p>
                              </div>

                              {/* Status Badge */}
                              <div className="shrink-0">
                                {model.is_installed ? (
                                  <span className="text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/80 px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow-2xs">
                                    <Check className="w-3 h-3 text-emerald-600" />
                                    <span>Installed ({model.actual_size_mb} MB)</span>
                                  </span>
                                ) : isDownloading ? (
                                  <span className="text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 px-2.5 py-1 rounded-full flex items-center gap-1.5 shadow-2xs">
                                    <Loader2 className="w-3 h-3 animate-spin text-blue-600" />
                                    <span>{model.download_progress}%</span>
                                  </span>
                                ) : (
                                  <span className="text-[11px] font-medium bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full border border-slate-200">
                                    ~{model.approx_size_mb} MB
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Technical Specs Tags (3 columns) */}
                            <div className="grid grid-cols-3 gap-2 text-[10px] font-mono text-slate-600 pt-1">
                              <div className="bg-slate-50 border border-slate-200/70 rounded-lg p-2 text-center">
                                <span className="block text-slate-400 font-sans text-[9px] uppercase font-bold">
                                  RAM Footprint
                                </span>
                                <span className="font-semibold text-slate-800">
                                  {model.ram_required}
                                </span>
                              </div>
                              <div className="bg-slate-50 border border-slate-200/70 rounded-lg p-2 text-center">
                                <span className="block text-slate-400 font-sans text-[9px] uppercase font-bold">
                                  Decode Speed
                                </span>
                                <span className="font-semibold text-slate-800">
                                  {model.speed_rating}
                                </span>
                              </div>
                              <div className="bg-slate-50 border border-slate-200/70 rounded-lg p-2 text-center">
                                <span className="block text-slate-400 font-sans text-[9px] uppercase font-bold">
                                  Accuracy
                                </span>
                                <span className="font-semibold text-slate-800">
                                  {model.accuracy_rating}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Action Footer */}
                          <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                            {model.is_installed ? (
                              <>
                                <span className="text-[11px] text-emerald-700 font-medium flex items-center gap-1">
                                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
                                  <span>Ready for offline execution</span>
                                </span>

                                <button
                                  type="button"
                                  onClick={() => handleDeleteModel(model.id, model.name)}
                                  disabled={isDeleting || isDownloading}
                                  className="px-2.5 py-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg border border-transparent hover:border-rose-200 transition-all cursor-pointer disabled:opacity-50 text-xs font-semibold flex items-center gap-1"
                                  title="Delete model weights from disk"
                                >
                                  {isDeleting ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin text-rose-500" />
                                  ) : (
                                    <Trash2 className="w-3.5 h-3.5" />
                                  )}
                                  <span>Delete Weights</span>
                                </button>
                              </>
                            ) : isDownloading ? (
                              <div className="w-full space-y-1.5">
                                <div className="flex items-center justify-between text-[11px] text-blue-700 font-medium">
                                  <span className="flex items-center gap-1.5">
                                    <Loader2 className="w-3 h-3 animate-spin" />
                                    <span>Downloading weights from Hugging Face...</span>
                                  </span>
                                  <span className="font-mono font-bold">{model.download_progress}%</span>
                                </div>
                                <div className="w-full bg-blue-100 h-2 rounded-full overflow-hidden">
                                  <div
                                    className="bg-blue-600 h-full rounded-full transition-all duration-300"
                                    style={{ width: `${model.download_progress}%` }}
                                  />
                                </div>
                              </div>
                            ) : (
                              <>
                                <span className="text-[11px] text-slate-400">
                                  Repository: {model.repo_id}
                                </span>

                                <button
                                  type="button"
                                  onClick={() => handleStartDownload(model.id)}
                                  className="px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-all active:scale-95 cursor-pointer flex items-center gap-1.5 shadow-2xs"
                                >
                                  <Download className="w-3.5 h-3.5" />
                                  <span>Download Weights</span>
                                </button>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* ── Modal Workstation Bottom Footer ──────────────────────────── */}
            <div className="px-5 sm:px-6 py-3.5 border-t border-slate-200/80 bg-slate-50/70 flex items-center justify-between shrink-0">
              <div className="text-[11px] text-slate-500 font-mono flex items-center gap-2">
                <span>TMUX Studio Engine</span>
                <span className="text-slate-300">•</span>
                <span className="text-emerald-700 font-semibold">100% Offline Resilience</span>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-2xs transition-colors cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
