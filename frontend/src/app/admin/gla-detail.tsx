"use client";

import {appFetch as fetch} from '@/lib/app-path';

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Loader2,
  MessageCircle,
  Sparkles,
  Brain,
  Image as ImageIcon,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

type JsonObject = Record<string, any>;

interface RunStage {
  stage: string;
  queued: number;
  in_progress: number;
  succeeded: number;
  failed: number;
}

interface LastEvent {
  message?: string;
  stage?: string;
  event_type?: string;
  created_at?: string;
}

interface PipelineRun {
  run_id: string;
  listing_id: number;
  status: string;
  config?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  pipeline_type?: string;
  jobs_queued: number;
  jobs_in_progress: number;
  jobs_succeeded: number;
  jobs_failed: number;
  jobs_total: number;
  current_stage?: string;
  stages?: RunStage[];
  last_event?: LastEvent | null;
  jobs?: JsonObject[];
}

interface ListingItem {
  id: number;
  url?: string;
  title?: string;
  created_at?: string;
  updated_at?: string;
  latest_run?: PipelineRun | null;
  stale_stages: { stage: string; label: string; stored: string; current: string }[];
}

type GLATab = "chat" | "opinions" | "memory" | "images";

interface GLADetailPayload {
  success: boolean;
  listing_id: number;
  phone_number?: string | null;
  conversations?: JsonObject[];
  user_profile?: JsonObject | null;
  chat_history?: JsonObject[];
  gla_opinion?: JsonObject | null;
  v5_pir_target?: JsonObject | null;
  smart_m2?: JsonObject | null;
  image_versions?: JsonObject[];
  room_decisions?: JsonObject[];
  pipeline_run?: PipelineRun | null;
  error?: string;
}

const fmtFull = (iso?: string) =>
  !iso
    ? "—"
    : new Date(iso).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });

const truncate = (s: string, maxLen: number) => {
  const t = String(s || "").trim();
  if (t.length <= maxLen) return t;
  return t.slice(0, Math.max(0, maxLen - 3)) + "...";
};

const tryJson = (text: string): any | null => {
  const raw = String(text || "").trim();
  if (!raw) return null;
  if (!(raw.startsWith("{") || raw.startsWith("["))) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
};

const Badge: React.FC<{ label: string }> = ({ label }) => (
  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-[#da654d]/20 text-[#ffd9cf] border border-[#da654d]/40">
    {label}
  </span>
);

const TabButton: React.FC<{
  active: boolean;
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
}> = ({ active, label, icon, onClick }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs border transition-colors ${
      active
        ? "bg-stone-800 border-stone-600 text-white"
        : "bg-transparent border-stone-800 text-stone-400 hover:text-white hover:border-stone-600"
    }`}
    aria-label={`Open ${label} tab`}
  >
    {icon}
    {label}
  </button>
);

const CollapsibleJson: React.FC<{ title: string; value: any }> = ({ title, value }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-stone-800/60 rounded-lg overflow-hidden bg-stone-900/40">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-white/[0.03] transition-colors"
        aria-label={`${open ? "Collapse" : "Expand"} ${title}`}
      >
        <span className="text-[11px] text-stone-300 font-medium">{title}</span>
        {open ? (
          <ChevronDown className="w-4 h-4 text-stone-500" />
        ) : (
          <ChevronRight className="w-4 h-4 text-stone-500" />
        )}
      </button>
      {open && (
        <pre className="text-[10px] leading-[1.6] text-stone-300 p-3 overflow-auto max-h-[280px] bg-[#0d1117] border-t border-stone-800/60">
          {JSON.stringify(value, null, 2)}
        </pre>
      )}
    </div>
  );
};

const ChatBubble: React.FC<{
  side: "left" | "right";
  header?: string;
  children: React.ReactNode;
}> = ({ side, header, children }) => {
  const isRight = side === "right";
  return (
    <div className={`flex ${isRight ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[92%] sm:max-w-[75%] rounded-2xl px-3 py-2 border ${
          isRight
            ? "bg-emerald-950/30 border-emerald-900/40 text-stone-100"
            : "bg-stone-900/60 border-stone-800/50 text-stone-100"
        }`}
      >
        {header && <div className="text-[10px] text-stone-400 mb-1">{header}</div>}
        <div className="text-[12px] whitespace-pre-wrap break-words">{children}</div>
      </div>
    </div>
  );
};

export const GLADetail: React.FC<{
  listing: ListingItem;
  onBack: () => void;
  onRefresh: () => void;
}> = ({ listing, onBack, onRefresh }) => {
  const [tab, setTab] = useState<GLATab>("chat");
  const [payload, setPayload] = useState<GLADetailPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`/api/admin/listings/${listing.id}/gla-detail`, { cache: "no-store" });
      const d = (await r.json()) as GLADetailPayload;
      if (!d.success) throw new Error(d.error || "Failed to load GLA detail");
      setPayload(d);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load GLA detail");
    } finally {
      setLoading(false);
    }
  }, [listing.id]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const chat = useMemo(() => {
    return (payload?.chat_history || []) as JsonObject[];
  }, [payload?.chat_history]);
  const opinionsRooms = useMemo(() => {
    const rooms = (payload?.gla_opinion as any)?.rooms;
    return Array.isArray(rooms) ? rooms : [];
  }, [payload]);

  const memorySummary = String((payload?.user_profile as any)?.memory_summary || "").trim();
  const memoryEvents = useMemo(() => {
    const out: Array<{ created_at?: string; args: any }> = [];
    for (const m of chat) {
      if (String(m?.message_type || "") !== "tool_call") continue;
      const parsed = tryJson(String(m?.message_text || ""));
      if (!parsed || parsed.name !== "save_memory") continue;
      out.push({ created_at: m?.created_at, args: parsed.args });
    }
    return out;
  }, [chat]);

  const imageVersions = useMemo(() => {
    return (payload?.image_versions || []) as JsonObject[];
  }, [payload?.image_versions]);
  const imageGroups = useMemo(() => {
    const map = new Map<string, any[]>();
    for (const v of imageVersions) {
      const roomId = String(v?.room_id || "unknown");
      const arr = map.get(roomId) || [];
      arr.push(v);
      map.set(roomId, arr);
    }
    return Array.from(map.entries()).map(([room_id, versions]) => ({
      room_id,
      versions: [...versions].sort((a, b) => Number(a?.version || 0) - Number(b?.version || 0)),
    }));
  }, [imageVersions]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-stone-800/50 flex items-center gap-3 bg-[#0a0a0a]/95 sticky top-0 z-10 backdrop-blur-sm">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg hover:bg-stone-800 text-stone-400 hover:text-white transition-colors shrink-0"
          aria-label="Back"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <h2 className="text-base sm:text-lg font-semibold text-white">
          Listing {listing.id}
        </h2>
        <Badge label="GLA" />
        <div className="flex-1" />
        <button
          onClick={() => {
            onRefresh();
            fetchDetail();
          }}
          className="px-3 py-1.5 text-xs rounded-lg border border-stone-800 text-stone-400 hover:text-white hover:border-stone-600 transition-colors"
          aria-label="Refresh GLA detail"
        >
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="flex flex-col lg:flex-row gap-5 lg:gap-6 p-4 sm:p-6 max-w-7xl">
          <div className="w-full lg:w-72 lg:shrink-0 space-y-4">
            <div className="bg-stone-900/50 rounded-lg p-3 border border-stone-800/40">
              <div className="text-[10px] uppercase tracking-wider text-stone-500">WhatsApp</div>
              <div className="mt-1 text-xs text-stone-300">
                {payload?.phone_number ? payload.phone_number : "No phone linked yet"}
              </div>
              {payload?.pipeline_run?.run_id && (
                <div className="mt-2 text-[11px] text-stone-600 space-y-0.5">
                  <div>
                    Run:{" "}
                    <span className="text-stone-500 font-mono">
                      {payload.pipeline_run.run_id}
                    </span>
                  </div>
                  <div>Started: {fmtFull(payload.pipeline_run.created_at)}</div>
                  {payload.pipeline_run.updated_at && (
                    <div>Updated: {fmtFull(payload.pipeline_run.updated_at)}</div>
                  )}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <div className="text-xs font-semibold text-stone-400 uppercase tracking-wider">
                Behind the scenes
              </div>
              <div className="flex flex-wrap gap-2">
                <TabButton
                  active={tab === "chat"}
                  label="Chat"
                  icon={<MessageCircle className="w-4 h-4" />}
                  onClick={() => setTab("chat")}
                />
                <TabButton
                  active={tab === "opinions"}
                  label="Opinions"
                  icon={<Sparkles className="w-4 h-4" />}
                  onClick={() => setTab("opinions")}
                />
                <TabButton
                  active={tab === "memory"}
                  label="Memory"
                  icon={<Brain className="w-4 h-4" />}
                  onClick={() => setTab("memory")}
                />
                <TabButton
                  active={tab === "images"}
                  label="Images"
                  icon={<ImageIcon className="w-4 h-4" />}
                  onClick={() => setTab("images")}
                />
              </div>
            </div>

            <div className="text-[11px] text-stone-600 pt-2 border-t border-stone-800/30">
              Note: clear-from-stage in admin is V5-oriented; for GLA, use WhatsApp tools to iterate.
            </div>
          </div>

          <div className="flex-1 min-w-0">
            {loading && (
              <div className="flex items-center justify-center py-12 text-stone-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="ml-2">Loading GLA detail...</span>
              </div>
            )}
            {error && !loading && (
              <div className="py-10 text-center text-sm text-red-400">{error}</div>
            )}

            {!loading && !error && payload && tab === "chat" && (
              <div className="space-y-3">
                {!chat.length && (
                  <div className="text-xs text-stone-600 py-6 text-center">
                    No chat history yet.
                  </div>
                )}
                {chat.map((m, idx) => {
                  const role = String(m?.role || "");
                  const mtype = String(m?.message_type || "text");
                  const createdAt = String(m?.created_at || "");
                  const rawText = String(m?.message_text || "");
                  const parsed = tryJson(rawText);

                  if (mtype === "tool_call" && parsed?.name) {
                    return (
                      <ChatBubble key={m?.id || idx} side="left" header={`${fmtFull(createdAt)} · tool_call`}>
                        <CollapsibleJson title={`Called ${parsed.name}`} value={parsed} />
                      </ChatBubble>
                    );
                  }

                  if (mtype === "tool_result") {
                    return (
                      <ChatBubble key={m?.id || idx} side="left" header={`${fmtFull(createdAt)} · tool_result`}>
                        {parsed ? (
                          <CollapsibleJson title="Tool result" value={parsed} />
                        ) : (
                          truncate(rawText, 1400)
                        )}
                      </ChatBubble>
                    );
                  }

                  const side = role === "user" ? "right" : "left";
                  return (
                    <ChatBubble key={m?.id || idx} side={side} header={fmtFull(createdAt)}>
                      {truncate(rawText, 2000)}
                    </ChatBubble>
                  );
                })}
              </div>
            )}

            {!loading && !error && payload && tab === "opinions" && (
              <div className="space-y-3">
                {!opinionsRooms.length && (
                  <div className="text-xs text-stone-600 py-6 text-center">
                    No GLA opinions yet (pipeline may still be running).
                  </div>
                )}
                {opinionsRooms.map((r: any, idx: number) => (
                  <CollapsibleJson
                    key={r?.room_id || idx}
                    title={`${r?.room_type || "room"} · ${r?.room_id || `#${idx + 1}`}`}
                    value={r}
                  />
                ))}
              </div>
            )}

            {!loading && !error && payload && tab === "memory" && (
              <div className="space-y-4">
                <div className="bg-stone-900/50 rounded-lg p-4 border border-stone-800/40">
                  <div className="text-xs font-semibold text-stone-300">User profile</div>
                  <div className="mt-2 text-[11px] text-stone-500 space-y-1">
                    <div>Phone: <span className="font-mono text-stone-400">{payload.phone_number || "—"}</span></div>
                    <div>Name: <span className="text-stone-400">{String((payload.user_profile as any)?.display_name || "—")}</span></div>
                    <div>Message count: <span className="text-stone-400">{String((payload.user_profile as any)?.message_count ?? "—")}</span></div>
                    <div>Last listing: <span className="text-stone-400">{String((payload.user_profile as any)?.last_listing_id ?? "—")}</span></div>
                  </div>
                </div>

                <div className="bg-stone-900/50 rounded-lg p-4 border border-stone-800/40">
                  <div className="text-xs font-semibold text-stone-300">Current memory summary</div>
                  <div className="mt-2 text-[12px] text-stone-200 whitespace-pre-wrap break-words">
                    {memorySummary || <span className="text-stone-600">(empty)</span>}
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-semibold text-stone-300">Memory evolution</div>
                  {!memoryEvents.length && (
                    <div className="text-xs text-stone-600">No `save_memory` calls recorded yet.</div>
                  )}
                  {memoryEvents.map((evt, idx) => (
                    <CollapsibleJson
                      key={`${evt.created_at || "t"}-${idx}`}
                      title={`${fmtFull(evt.created_at)} · save_memory`}
                      value={evt.args}
                    />
                  ))}
                </div>
              </div>
            )}

            {!loading && !error && payload && tab === "images" && (
              <div className="space-y-4">
                {!imageGroups.length && (
                  <div className="text-xs text-stone-600 py-6 text-center">
                    No generated images yet.
                  </div>
                )}

                {imageGroups.map((g) => (
                  <div key={g.room_id} className="bg-stone-900/40 border border-stone-800/40 rounded-lg p-4">
                    <div className="text-xs font-semibold text-stone-300 mb-3">
                      Room: <span className="font-mono text-stone-400">{g.room_id}</span>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                      {g.versions.map((v: any, idx: number) => {
                        const after = String(v?.image_data || "");
                        const def = String(v?.defurnished_data || "");
                        const imgSrc = after ? `data:image/jpeg;base64,${after}` : "";
                        const defSrc = def ? `data:image/jpeg;base64,${def}` : "";
                        return (
                          <div key={v?.id || idx} className="rounded-lg border border-stone-800/60 overflow-hidden bg-stone-950/20">
                            <div className="px-3 py-2 text-[11px] text-stone-400 border-b border-stone-800/50 flex items-center justify-between">
                              <span>v{Number(v?.version || idx + 1)}</span>
                              <span className="text-stone-600">{fmtFull(v?.created_at)}</span>
                            </div>
                            <div className="p-3 space-y-2">
                              {imgSrc ? (
                                // eslint-disable-next-line @next/next/no-img-element
                                <img src={imgSrc} alt={`render v${idx + 1}`} className="w-full h-auto rounded-md border border-stone-800/50" />
                              ) : (
                                <div className="w-full aspect-[4/3] rounded-md border border-stone-800/50 bg-stone-900/60 flex items-center justify-center text-xs text-stone-600">
                                  No render
                                </div>
                              )}
                              {defSrc && (
                                <details className="group">
                                  <summary className="cursor-pointer text-[11px] text-stone-500 hover:text-stone-300 transition-colors">
                                    Defurnished input
                                  </summary>
                                  <div className="mt-2">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img src={defSrc} alt="defurnished input" className="w-full h-auto rounded-md border border-stone-800/50" />
                                  </div>
                                </details>
                              )}
                              {v?.prompt_used && (
                                <details className="group">
                                  <summary className="cursor-pointer text-[11px] text-stone-500 hover:text-stone-300 transition-colors">
                                    Prompt used
                                  </summary>
                                  <pre className="mt-2 text-[10px] text-stone-300 whitespace-pre-wrap break-words bg-[#0d1117] rounded-md p-2 border border-stone-800/60 max-h-[220px] overflow-auto">
                                    {String(v.prompt_used)}
                                  </pre>
                                </details>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

