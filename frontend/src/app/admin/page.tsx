"use client";

import {appFetch as fetch} from '@/lib/app-path';
import React, { useState, useEffect, useCallback, useMemo } from "react";
import {
  RefreshCw, ChevronRight, CheckCircle, XCircle, Clock, Loader2,
  AlertTriangle, ExternalLink, Copy, Check, Sparkles,
  LayoutList, Users, Settings, Trash2, Play, RotateCcw, ChevronLeft,
  AlertOctagon, ArrowLeft, Clipboard, Eye, Square, StopCircle,
  Home, MapPin, BedDouble, Bath, Ruler, Zap, Star,
} from "lucide-react";
import { PasteLinkModal } from "@/components";
import { scrapeUrl, createListing, runPipeline } from "@/lib/api";
import { type ScrapedData } from "@/lib/types";
import { GLADetail } from "./gla-detail";

// ── Types ──
interface RunStage { stage: string; queued: number; in_progress: number; succeeded: number; failed: number; }
interface LastEvent { message?: string; stage?: string; event_type?: string; created_at?: string; }
interface PipelineRun {
  run_id: string; listing_id: number; status: string; config?: Record<string, any>;
  created_at?: string; updated_at?: string;
  pipeline_type?: string;
  jobs_queued: number; jobs_in_progress: number; jobs_succeeded: number; jobs_failed: number; jobs_total: number;
  current_stage?: string; stages?: RunStage[];
  last_event?: LastEvent | null;
}
interface ListingItem {
  id: number; url?: string; title?: string; created_at?: string; updated_at?: string;
  latest_run?: PipelineRun | null;
  stale_stages: { stage: string; label: string; stored: string; current: string }[];
}
interface LogEntry { id?: number; event_type?: string; message?: string; data?: Record<string, any>; created_at?: string; stage?: string; }
interface CostData {
  listing_id: number;
  total_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_regular: number;
  by_model: Record<string, any>;
  cleared_costs?: Record<string, any>;
  timing?: { clean_runtime_s?: number; by_stage_s?: Record<string, number>; jobs_counted?: number };
}
type PipelineState = "idle" | "scraping" | "creating" | "triggering" | "done" | "error";

// ── Constants ──
const RERUN_STAGES = ["snapshot","comparables","clustering","v5_room_tags","v5_pir","v5_select","v5_comparables","v5_delta","v5_delta_review","v5_decompose","v5_smart_m2","v5_bcca_match","v5_quant_plan","v5_forage","v5_boq_assembly","v5_finalize","v5_eli5","v5_negotiation","v5_room_images","v5_translations"];
const STATUS_STAGES = ["snapshot","comparables","clustering","v5_room_tags","v5_pir","v5_select","v5_comparables","v5_delta","v5_delta_review","v5_decompose","v5_smart_m2","v5_bcca_match","v5_quant_plan","v5_forage","v5_boq_assembly","v5_finalize","v5_eli5","v5_negotiation","v5_room_images_defurnish","v5_room_images_prompt_generation","v5_room_images_style_consistency","v5_room_images_photo_generation","v5_translations"];
const GLA_STATUS_STAGES = ["snapshot","clustering","room_tags","pir","smart_m2","opinion"];
const SL: Record<string, string> = {
  snapshot:"Snapshot",
  comparables:"Comparables",
  clustering:"Clustering",
  // GLA stages
  room_tags:"Room Tags",
  pir:"PIR Analysis",
  smart_m2:"Smart M\u00B2",
  opinion:"Leo Opinion",
  // V5 stages
  v5_room_tags:"Room Tags",
  v5_pir:"PIR",
  v5_select:"Select Comp",
  v5_comparables:"Comp Analysis",
  v5_delta:"Delta",
  v5_delta_review:"Delta Review",
  v5_decompose:"Work Items",
  v5_smart_m2:"Smart M\u00B2",
  v5_bcca_match:"BCCA Match",
  v5_quant_plan:"Quant Plan",
  v5_forage:"Photo Signals",
  v5_boq_assembly:"BOQ",
  v5_finalize:"Finalize",
  v5_eli5:"ELI5",
  v5_negotiation:"Negotiation",
  v5_room_images:"Room Images",
  v5_room_images_defurnish:"Photo Defurnishing",
  v5_room_images_prompt_generation:"Prompt Generation",
  v5_room_images_style_consistency:"Style Consistency",
  v5_room_images_photo_generation:"Photo Generation",
  v5_translations:"Translations",
};

const stagesForPipeline = (pipelineType?: string) => {
  if (pipelineType === "gla") return GLA_STATUS_STAGES;
  return STATUS_STAGES;
};

const runHasActionableFail = (run?: PipelineRun | null): boolean => {
  return (run?.jobs_failed || 0) > 0;
};

// ── Helpers ──
const fmtTime = (iso?: string) => { if (!iso) return "\u2014"; const ms = Date.now()-new Date(iso).getTime(); const m=Math.floor(ms/60000),h=Math.floor(m/60),d=Math.floor(h/24); if(m<1) return "just now"; if(m<60) return m+"m ago"; if(h<24) return h+"h ago"; if(d<7) return d+"d ago"; return new Date(iso).toLocaleDateString("en-US",{month:"short",day:"numeric"}); };
const fmtTs = (iso?: string) => !iso?"":new Date(iso).toLocaleTimeString("en-US",{hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false});
const fmtFull = (iso?: string) => !iso?"\u2014":new Date(iso).toLocaleString("en-US",{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit",hour12:false});
const domain = (url?: string) => { if(!url) return ""; try{return new URL(url).hostname.replace("www.","");}catch{return url.slice(0,40);} };
const CASAFARI = 3.5;
const $$ = (n: number) => n>=1?`$${n.toFixed(2)}`:n>=0.01?`$${n.toFixed(3)}`:`$${n.toFixed(4)}`;
const fmtTok = (n: number) => n>=1e6?`${(n/1e6).toFixed(1)}M`:n>=1e3?`${(n/1e3).toFixed(1)}K`:String(n);
const fmtDur = (s?: number) => {
  const sec = Math.max(0, Number(s || 0));
  if (!Number.isFinite(sec)) return "0s";
  if (sec >= 3600) {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    return `${h}h ${m}m`;
  }
  if (sec >= 60) {
    const mins = sec / 60;
    const dp = mins < 10 ? 1 : 0;
    return `${mins.toFixed(dp)}m`;
  }
  return `${Math.round(sec)}s`;
};

function describeRun(run?: PipelineRun|null): {label:string;color:string;icon:React.ReactNode} {
  if (!run) return {label:"Never run",color:"text-stone-500",icon:<Clock className="w-3.5 h-3.5"/>};

  // Pipeline status from filtered jobs
  const {jobs_failed:f,jobs_in_progress:ip,jobs_succeeded:s,jobs_total:t,stages} = run;
  const stageOrder = stagesForPipeline(run.pipeline_type);
  const sorted = [...(stages||[])].sort((a,b)=>(stageOrder.indexOf(a.stage)===-1?999:stageOrder.indexOf(a.stage))-(stageOrder.indexOf(b.stage)===-1?999:stageOrder.indexOf(b.stage)));
  const active = sorted.find(x=>x.in_progress>0);
  const firstFail = sorted.find(x=>x.failed>0);
  if (s===t && t>0) return {label:"Complete",color:"text-emerald-400",icon:<CheckCircle className="w-3.5 h-3.5"/>};
  if (ip>0) return {label:`Running ${active?(SL[active.stage]||active.stage):""}...`,color:"text-blue-400",icon:<Loader2 className="w-3.5 h-3.5 animate-spin"/>};
  if (run.jobs_queued>0) return {label:"Waiting for worker...",color:"text-amber-400",icon:<Clock className="w-3.5 h-3.5"/>};
  if (f>0) return {label:`Failed at ${firstFail?(SL[firstFail.stage]||firstFail.stage):"?"}`,color:"text-red-400",icon:<XCircle className="w-3.5 h-3.5"/>};
  if (run.status==="stopped"){const last=[...sorted].reverse().find(x=>x.succeeded>0);return{label:`Stopped${last?` after ${SL[last.stage]||last.stage}`:""}`,color:"text-orange-400",icon:<Square className="w-3.5 h-3.5"/>};}
  if (s>0&&s<t){const last=[...sorted].reverse().find(x=>x.succeeded>0);return{label:`Stopped after ${last?(SL[last.stage]||last.stage):"?"}`,color:"text-amber-400",icon:<AlertTriangle className="w-3.5 h-3.5"/>};}
  return {label:run.status,color:"text-stone-500",icon:<Clock className="w-3.5 h-3.5"/>};
}
const pct = (r?: PipelineRun|null) => (!r||r.jobs_total===0)?0:Math.round(r.jobs_succeeded/r.jobs_total*100);

// ── StageTimeline ──
// Shows ALL V5 stages in order — not just the ones that have jobs.
// Stages without jobs appear as dim "pending" dots, giving a complete picture.
const StageTimeline: React.FC<{stages:RunStage[];pipelineType?:string}> = ({stages,pipelineType}) => {
  const stageMap = new Map(stages.map(s=>[s.stage,s]));
  const stageOrder = stagesForPipeline(pipelineType);
  return (<div className="space-y-0">{stageOrder.map((stageName,i)=>{
    const s = stageMap.get(stageName) || { stage: stageName, queued: 0, in_progress: 0, succeeded: 0, failed: 0 };
    const rawFail = s.failed>0;
    const run = s.in_progress>0;
    const done = s.succeeded>0&&!rawFail&&!run;
    const fail = rawFail;
    const queued = s.queued>0;
    let dot="bg-stone-700/50",line="bg-stone-800/30";
    if(fail){dot="bg-red-500";line="bg-red-900/50";}else if(run){dot="bg-blue-500 animate-pulse";line="bg-blue-900/30";}else if(done){dot="bg-emerald-500";line="bg-emerald-900/30";}else if(queued){dot="bg-amber-500/50";line="bg-amber-900/20";}
    return(<div key={stageName} className="flex items-start gap-3"><div className="flex flex-col items-center w-4 shrink-0"><div className={`w-2.5 h-2.5 rounded-full mt-1 ${dot}`}/>{i<stageOrder.length-1&&<div className={`w-0.5 flex-1 min-h-[20px] ${line}`}/>}</div><div className={`pb-2 text-xs ${fail?"text-red-400":run?"text-blue-300":done?"text-stone-300":queued?"text-amber-400/60":"text-stone-700"}`}><span className="font-medium">{SL[stageName]||stageName}</span>{run&&<span className="ml-2 text-blue-400">running...</span>}{fail&&<span className="ml-2 text-red-400">failed</span>}{queued&&<span className="ml-2 text-amber-400/50">queued</span>}</div></div>);
  })}</div>);
};

// ── CostDetail ──
const CostDetail: React.FC<{runId:string}> = ({runId}) => {
  const[costs,setCosts]=useState<CostData|null>(null);const[loading,setLoading]=useState(true);const[copied,setCopied]=useState(false);
  useEffect(()=>{(async()=>{try{const r=await fetch(`/api/admin/runs/${encodeURIComponent(runId)}/costs`);const d=await r.json();if(d.success&&d.has_data)setCosts(d.costs);}catch{}finally{setLoading(false);}})();},[runId]);
  const copyText=useCallback(()=>{if(!costs)return"";const t=costs.total_cost_regular+CASAFARI;const cleared=costs.cleared_costs&&Object.keys(costs.cleared_costs).length>0?` | Cleared: ${Object.entries(costs.cleared_costs).map(([k,v]:any)=>`#${k} ${$$(Number(v?.cost_regular??0))}`).join(", ")}`:"";const rt=costs.timing?.clean_runtime_s!=null?` | Clean runtime: ${fmtDur(costs.timing.clean_runtime_s)}`:"";return`Cost: ${$$(t)} | LLM: ${$$(costs.total_cost_regular)} | Casafari: ${$$(CASAFARI)} | ${costs.total_calls} calls | ${costs.total_input_tokens.toLocaleString()} in / ${costs.total_output_tokens.toLocaleString()} out${rt}${cleared}`;},[costs]);
  const handleCopy=async()=>{const t=copyText();try{await navigator.clipboard.writeText(t);}catch{const el=document.createElement("textarea");el.value=t;document.body.appendChild(el);el.select();document.execCommand("copy");document.body.removeChild(el);}setCopied(true);setTimeout(()=>setCopied(false),2000);};
  if(loading)return<div className="text-xs text-stone-600 py-2">Loading costs...</div>;
  if(!costs)return<div className="text-xs text-stone-600 py-2">No cost data.</div>;
  const total=costs.total_cost_regular+CASAFARI;
  const cleared = costs.cleared_costs || {};
  const clearedEntries = Object.entries(cleared).sort(([a],[b])=>Number(a)-Number(b));
  return(<div className="bg-stone-900/50 rounded-lg p-3 sm:p-4 space-y-3"><div className="flex items-center justify-between"><h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Cost</h4><button onClick={handleCopy} className="flex items-center gap-1 px-2 py-1 text-[10px] rounded border border-stone-700 text-stone-500 hover:text-white hover:border-stone-500 transition-colors">{copied?<><Check className="w-3 h-3 text-emerald-400"/> Copied</>:<><Copy className="w-3 h-3"/> Copy</>}</button></div><div className="flex items-baseline gap-2"><span className="text-xl sm:text-2xl font-bold text-amber-400">{$$(total)}</span><span className="text-xs text-stone-500">total</span></div><div className="flex gap-3 sm:gap-4 text-[10px] sm:text-[11px] text-stone-500 flex-wrap"><span>LLM: {$$(costs.total_cost_regular)}</span><span>Casafari: {$$(CASAFARI)}</span><span>{costs.total_calls} calls</span>{costs.timing?.clean_runtime_s!=null&&<span>Runtime: {fmtDur(costs.timing.clean_runtime_s)}</span>}</div>{clearedEntries.length>0&&(<div className="pt-2 border-t border-stone-800/50 space-y-1"><div className="text-[10px] text-stone-500 uppercase tracking-wider">Cleared attempts</div>{clearedEntries.map(([seq,d]:any)=>(<div key={seq} className="flex items-center justify-between text-[11px]"><span className="text-stone-500">#{seq}{d?.from_stage?` from ${d.from_stage}`:""}</span><span className="text-stone-600">{$$(Number(d?.cost_regular??0))}{d?.calls?` · ${d.calls} calls`:""}</span></div>))}</div>)}{costs.by_model&&Object.keys(costs.by_model).length>0&&(<div className="pt-2 border-t border-stone-800/50 space-y-1">{Object.entries(costs.by_model).map(([m,d]:any)=>(<div key={m} className="flex items-center justify-between text-[11px]"><span className="font-mono text-stone-400">{m}</span><span className="text-stone-500">{d.calls??0} calls &middot; {$$(d.cost_regular??d.total_cost??0)}</span></div>))}</div>)}</div>);
};

// ── LogViewer ──
const LogViewer: React.FC<{runId:string}> = ({runId}) => {
  const[logs,setLogs]=useState<LogEntry[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);const[copied,setCopied]=useState(false);
  const fetchLogs=useCallback(async()=>{try{const r=await fetch(`/api/admin/runs/${encodeURIComponent(runId)}/logs?limit=20000`);const d=await r.json();if(d.success){setLogs(d.logs||[]);setError(null);}else setError(d.error||"Failed");}catch{setError("Network error");}finally{setLoading(false);}},[runId]);
  useEffect(()=>{fetchLogs();const t=setInterval(fetchLogs,3000);return()=>clearInterval(t);},[fetchLogs]);
  const handleCopy=async()=>{const text=logs.map(l=>`${fmtTs(l.created_at)}  ${(l.stage||"\u2014").padEnd(22)}  ${l.message||""}`).join("\n");try{await navigator.clipboard.writeText(text);}catch{const el=document.createElement("textarea");el.value=text;document.body.appendChild(el);el.select();document.execCommand("copy");document.body.removeChild(el);}setCopied(true);setTimeout(()=>setCopied(false),2000);};
  if(loading)return<div className="flex items-center justify-center py-8"><Loader2 className="w-4 h-4 animate-spin text-stone-500"/><span className="ml-2 text-xs text-stone-500">Loading logs...</span></div>;
  if(error)return<div className="py-6 text-center text-xs text-red-400">{error}</div>;
  if(!logs.length)return<div className="py-6 text-center text-xs text-stone-600">No logs yet.</div>;
  return(<div className="bg-stone-900/50 rounded-lg overflow-hidden">
    <div className="flex items-center gap-1.5 px-3 py-2 bg-stone-900/80 text-[10px] overflow-x-auto border-b border-stone-800/50">
      <span className="text-stone-500">Live logs ({logs.length})</span>
      <div className="flex-1"/>
      <button onClick={handleCopy} className="flex items-center gap-1 px-2 py-0.5 rounded border border-stone-700 text-stone-500 hover:text-white hover:border-stone-500 transition-colors shrink-0" aria-label="Copy logs">{copied?<><Check className="w-3 h-3 text-emerald-400"/> Copied</>:<><Clipboard className="w-3 h-3"/> Copy logs</>}</button>
    </div>
    <div className="bg-[#0d1117] text-[#c9d1d9] font-mono text-[10px] sm:text-[11px] leading-[1.7] overflow-auto max-h-[350px] sm:max-h-[500px] p-2 sm:p-3">
      {logs.map((log,i)=>{const err=log.event_type==="failed"||log.event_type==="error";const prog=log.event_type==="progress";const cleared=log.event_type==="cleared";if(cleared)return(<div key={log.id||i} className="flex items-center gap-2 my-1.5"><div className="flex-1 h-px bg-amber-800/40"/><span className="text-[10px] text-amber-500/80 shrink-0 px-2 flex items-center gap-1"><RotateCcw className="w-3 h-3"/>{log.message||"Logs cleared"}</span><div className="flex-1 h-px bg-amber-800/40"/></div>);return(<div key={log.id||i} className={`flex gap-1.5 sm:gap-2 group hover:bg-white/[0.03] rounded px-1 -mx-1 ${err?"text-[#f85149]":""}`}><span className="text-[#484f58] select-none shrink-0 w-[50px] sm:w-[60px] text-[9px] sm:text-[11px]">{fmtTs(log.created_at)}</span><span className={`shrink-0 w-[70px] sm:w-[90px] truncate text-[9px] sm:text-[11px] ${err?"text-[#f85149]":prog?"text-[#58a6ff]":"text-[#7ee787]"}`}>{log.stage||"\u2014"}</span><span className="flex-1 whitespace-pre-wrap break-all">{log.message||"\u2014"}{log.data&&Object.keys(log.data).length>0&&JSON.stringify(log.data).length<200&&<span className="text-[#484f58] ml-2 hidden sm:inline">{JSON.stringify(log.data)}</span>}</span></div>);})}
    </div>
  </div>);
};

// ── ClearDropdown ──
const ClearDropdown: React.FC<{listingId:number;onDone:()=>void}> = ({listingId,onDone}) => {
  const[open,setOpen]=useState(false);const[stage,setStage]=useState("");const[confirm,setConfirm]=useState(false);const[busy,setBusy]=useState(false);const[msg,setMsg]=useState<string|null>(null);
  const go=async()=>{if(!stage)return;setBusy(true);setMsg(null);try{const r=await fetch(`/api/admin/listings/${listingId}/clear-from-stage`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({from_stage:stage})});const d=await r.json();if(d.success){const extra=d.cleared_cost_rows?` \u2014 cleared ${d.cleared_cost_rows} cost rows (seq #${d.clear_seq??"?"})`:"";setMsg(`Done \u2014 cleared ${d.deleted?.length??0} artifacts, requeued ${d.requeued?.length??0} jobs, reset downstream logs${extra}`);setTimeout(()=>{setOpen(false);setConfirm(false);setMsg(null);setStage("");onDone();},2500);}else setMsg(`Error: ${d.error}`);}catch{setMsg("Network error");}finally{setBusy(false);}};
  if(!open)return<button onClick={()=>setOpen(true)} className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-amber-800/50 text-amber-400 hover:bg-amber-900/20 transition-colors"><RotateCcw className="w-3.5 h-3.5"/> Clear &amp; rerun from...</button>;
  return(<div className="bg-stone-900 border border-stone-700 rounded-lg p-4 space-y-3 w-full">
    <p className="text-xs text-stone-300 font-medium">Choose where to clear from:</p>
    <p className="text-[11px] text-stone-500">Everything from this stage onward gets deleted and requeued.</p>
    <select value={stage} onChange={e=>{setStage(e.target.value);setConfirm(false);}} className="w-full px-3 py-2 text-sm bg-stone-800 border border-stone-700 rounded-lg text-stone-200 focus:outline-none focus:ring-1 focus:ring-amber-500">
      <option value="">Select stage...</option>
      {RERUN_STAGES.map(s=><option key={s} value={s}>{SL[s]||s}</option>)}
    </select>
    {stage&&!confirm&&<button onClick={()=>setConfirm(true)} className="w-full px-4 py-2 text-xs font-medium rounded-lg bg-amber-600 text-white hover:bg-amber-500 transition-colors">Clear from &ldquo;{SL[stage]||stage}&rdquo; onward</button>}
    {confirm&&<div className="space-y-2"><p className="text-[11px] text-red-400">This deletes data and requeues jobs. Sure?</p><div className="flex gap-2"><button onClick={go} disabled={busy} className="flex-1 px-4 py-2 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors">{busy?<Loader2 className="w-3 h-3 animate-spin mx-auto"/>:"Yes, clear & requeue"}</button><button onClick={()=>{setConfirm(false);setOpen(false);setStage("");}} className="px-4 py-2 text-xs rounded-lg border border-stone-700 text-stone-400 hover:text-white transition-colors">Cancel</button></div></div>}
    {msg&&<p className="text-[11px] text-emerald-400">{msg}</p>}
  </div>);
};

// ── Last Activity ──
const LastActivity: React.FC<{event?:LastEvent|null;pipelineType?:string}> = ({event,pipelineType}) => {
  if (!event) return null;
  const isErr = event.event_type === "failed" || event.event_type === "error";
  const stageOrder = stagesForPipeline(pipelineType);
  const showStage = !(pipelineType && pipelineType !== "legacy" && event.stage && !stageOrder.includes(event.stage));
  // Extract a clean one-line summary from the message (which can be multi-line log dumps)
  const raw = event.message || "";
  const summary = (() => {
    // If message has actual log lines, grab the last meaningful one
    const lines = raw.split("\n").map(l=>l.trim()).filter(Boolean);
    const meaningful = lines.filter(l=>!l.startsWith("202") || l.includes("ERROR") || l.includes("INFO"));
    if (meaningful.length === 0) return raw.slice(0, 120);
    const last = meaningful[meaningful.length - 1];
    // Strip common log prefixes like "2026-02-12 12:10:03,455 | INFO | module | "
    const cleaned = last.replace(/^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\d]*\s*\|\s*\w+\s*\|\s*\w+\s*\|\s*/, "");
    return cleaned.slice(0, 120);
  })();
  return (<div className="bg-stone-900/50 rounded-lg p-3 space-y-1">
    <div className="flex items-center justify-between">
      <h4 className="text-[10px] font-semibold text-stone-500 uppercase tracking-wider">Last activity</h4>
      <span className="text-[10px] text-stone-600">{fmtTime(event.created_at)}</span>
    </div>
    <div className="flex items-start gap-2">
      {showStage && event.stage && <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${isErr?"bg-red-900/30 text-red-400":"bg-stone-800 text-stone-400"}`}>{SL[event.stage]||event.stage}</span>}
      <p className={`text-[11px] break-all ${isErr?"text-red-400":"text-stone-400"}`}>{summary}</p>
    </div>
  </div>);
};

// ── Comparables Panel ──
interface CompTarget { id:number; title:string; price_eur?:number; bedrooms?:number; bathrooms?:number; m2?:number; property_type?:string; condition?:string; energy_rating?:string; photo_url?:string; }
interface CompItem { casafari_property_id:number; sale_price:number; price_per_sqm:number; m2?:number; bedrooms?:number; bathrooms?:number; condition?:string; distance_km?:number; address?:string; photo_url?:string; is_selected:boolean; }

const CompCard: React.FC<{label:string; price?:number; m2?:number; beds?:number; baths?:number; condition?:string; distance?:number; address?:string; photo?:string; selected?:boolean; isTarget?:boolean; energy?:string}> = ({label,price,m2,beds,baths,condition,distance,address,photo,selected,isTarget,energy}) => {
  const border = isTarget ? "border-blue-600/60" : selected ? "border-emerald-500/60" : "border-stone-800/50";
  const badge = isTarget ? "bg-blue-900/40 text-blue-300 border-blue-800/40" : selected ? "bg-emerald-900/40 text-emerald-300 border-emerald-800/40" : null;
  return (
    <div className={`rounded-lg border ${border} bg-stone-900/60 overflow-hidden flex flex-col min-w-[160px] sm:min-w-[180px] max-w-[200px] sm:max-w-[220px]`}>
      {photo ? (
        <div className="h-24 bg-stone-800 relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photo} alt={label} className="w-full h-full object-cover" loading="lazy" />
          {badge && <span className={`absolute top-1.5 left-1.5 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${badge}`}>{isTarget ? "Target" : "Selected"}</span>}
        </div>
      ) : (
        <div className="h-24 bg-stone-800 flex items-center justify-center relative">
          <Home className="w-6 h-6 text-stone-700" />
          {badge && <span className={`absolute top-1.5 left-1.5 text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border ${badge}`}>{isTarget ? "Target" : "Selected"}</span>}
        </div>
      )}
      <div className="p-2.5 space-y-1.5">
        {price != null && <p className="text-sm font-bold text-white tabular-nums">{price >= 1000 ? `€${(price/1000).toFixed(0)}k` : `€${price}`}</p>}
        <div className="flex flex-wrap gap-x-2.5 gap-y-0.5 text-[10px] text-stone-400">
          {m2 != null && <span className="flex items-center gap-0.5"><Ruler className="w-2.5 h-2.5" />{m2}m²</span>}
          {beds != null && <span className="flex items-center gap-0.5"><BedDouble className="w-2.5 h-2.5" />{beds}</span>}
          {baths != null && <span className="flex items-center gap-0.5"><Bath className="w-2.5 h-2.5" />{baths}</span>}
        </div>
        <div className="flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-stone-500">
          {condition && <span className="flex items-center gap-0.5"><Star className="w-2.5 h-2.5" />{condition}</span>}
          {energy && <span className="flex items-center gap-0.5"><Zap className="w-2.5 h-2.5" />{energy}</span>}
          {distance != null && <span className="flex items-center gap-0.5"><MapPin className="w-2.5 h-2.5" />{Number(distance).toFixed(1)}km</span>}
        </div>
        {address && <p className="text-[10px] text-stone-600 truncate" title={address}>{address}</p>}
      </div>
    </div>
  );
};

const ComparablesPanel: React.FC<{listingId:number}> = ({listingId}) => {
  const [target, setTarget] = useState<CompTarget|null>(null);
  const [comps, setComps] = useState<CompItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`/api/admin/listings/${listingId}/comparables`);
        const d = await r.json();
        if (d.success) { setTarget(d.target); setComps(d.comparables || []); }
      } catch { /* ignore */ }
      finally { setLoading(false); }
    })();
  }, [listingId]);

  if (loading) return <div className="flex items-center gap-2 text-xs text-stone-500 py-4"><Loader2 className="w-3.5 h-3.5 animate-spin" />Loading comparables...</div>;
  if (!target && comps.length === 0) return null;

  return (
    <div className="bg-stone-900/50 rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 border-b border-stone-800/50 flex items-center justify-between">
        <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider">
          Target vs Comparables {comps.length > 0 && <span className="text-stone-600 font-normal normal-case">({comps.length} found{comps.some(c=>c.is_selected) ? ", 1 selected" : ""})</span>}
        </h4>
        {target && <a href={`/listing/${target.id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 transition-colors">Open full <ExternalLink className="w-3 h-3"/></a>}
      </div>
      <div className="p-3 overflow-x-auto">
        <div className="flex gap-2.5">
          {target && (
            <CompCard
              label="Target"
              price={target.price_eur ? Number(target.price_eur) : undefined}
              m2={target.m2 ? Number(target.m2) : undefined}
              beds={target.bedrooms ? Number(target.bedrooms) : undefined}
              baths={target.bathrooms ? Number(target.bathrooms) : undefined}
              condition={target.condition}
              energy={target.energy_rating}
              photo={target.photo_url}
              isTarget
            />
          )}
          {comps.map((c) => (
            <CompCard
              key={c.casafari_property_id}
              label={c.address || `#${c.casafari_property_id}`}
              price={c.sale_price}
              m2={c.m2 ? Number(c.m2) : undefined}
              beds={c.bedrooms ? Number(c.bedrooms) : undefined}
              baths={c.bathrooms ? Number(c.bathrooms) : undefined}
              condition={c.condition}
              distance={c.distance_km ? Number(c.distance_km) : undefined}
              address={c.address}
              photo={c.photo_url}
              selected={c.is_selected}
            />
          ))}
          {comps.length === 0 && <p className="text-xs text-stone-600 py-4 px-2">No comparables found yet.</p>}
        </div>
      </div>
    </div>
  );
};

// ── Detail Panel ──
const Detail: React.FC<{listing:ListingItem;onBack:()=>void;onRefresh:()=>void}> = ({listing,onBack,onRefresh}) => {
  const run=listing.latest_run; const st=describeRun(run); const p=pct(run);
  const stale=listing.stale_stages.length>0; const hasFail=runHasActionableFail(run);
  const[resuming,setResuming]=useState(false);const[deleting,setDeleting]=useState(false);const[delConf,setDelConf]=useState(false);const[stopping,setStopping]=useState(false);
  const isRunning = (run?.jobs_in_progress||0)>0||(run?.jobs_queued||0)>0;
  const isStopped = !isRunning && run && run.jobs_succeeded < run.jobs_total && run.jobs_succeeded > 0;
  const canResume = hasFail || !!isStopped;
  const resume=async()=>{setResuming(true);try{const r=await fetch(`/api/admin/listings/${listing.id}/resume`,{method:"POST"});if(!r.ok)throw new Error(`resume failed: ${r.status}`);onRefresh();}catch(e){console.error(e);}finally{setResuming(false);}};
  const stop=async()=>{setStopping(true);try{const r=await fetch(`/api/admin/listings/${listing.id}/stop`,{method:"POST"});if(!r.ok)throw new Error(`stop failed: ${r.status}`);onRefresh();}catch(e){console.error(e);}finally{setStopping(false);}};
  const del=async()=>{setDeleting(true);try{await fetch(`/api/admin/listings/${listing.id}/delete`,{method:"DELETE"});onBack();onRefresh();}catch{}finally{setDeleting(false);setDelConf(false);}};
  return(<div className="h-full flex flex-col">
    <div className="px-4 sm:px-6 py-3 sm:py-4 border-b border-stone-800/50 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 bg-[#0a0a0a]/95 sticky top-0 z-10 backdrop-blur-sm">
      <div className="flex items-center gap-3 sm:gap-4 min-w-0">
        <button onClick={onBack} className="p-1.5 rounded-lg hover:bg-stone-800 text-stone-400 hover:text-white transition-colors shrink-0" aria-label="Back"><ArrowLeft className="w-5 h-5"/></button>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap"><h2 className="text-base sm:text-lg font-semibold text-white">Listing {listing.id}</h2><div className={`flex items-center gap-1.5 text-xs sm:text-sm ${st.color}`}>{st.icon}<span className="truncate">{st.label}</span></div>{stale&&<span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] sm:text-[11px] font-medium bg-orange-900/30 text-orange-400 border border-orange-800/50"><AlertOctagon className="w-3 h-3"/> Out of date</span>}</div>
          {listing.url&&<p className="text-xs text-stone-500 font-mono mt-0.5 truncate">{domain(listing.url)}</p>}
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-3 shrink-0 pl-10 sm:pl-0">
        {isRunning&&<button onClick={stop} disabled={stopping} className="flex items-center justify-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors" aria-label="Stop pipeline">{stopping?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<Square className="w-3.5 h-3.5"/>} Stop</button>}
        {canResume&&<button onClick={resume} disabled={resuming} className="flex items-center justify-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-50 transition-colors" aria-label="Resume pipeline">{resuming?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<Play className="w-3.5 h-3.5"/>} Resume</button>}
        <a href={`/listing/${listing.id}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs font-medium rounded-lg border border-stone-700 text-stone-400 hover:text-white hover:border-stone-500 transition-colors"><Eye className="w-3.5 h-3.5"/> <span className="hidden sm:inline">View listing</span><span className="sm:hidden">View</span></a>
      </div>
    </div>
    <div className="flex-1 overflow-auto"><div className="flex flex-col lg:flex-row gap-5 lg:gap-6 p-4 sm:p-6 max-w-7xl">
      <div className="w-full lg:w-72 lg:shrink-0 space-y-5">
        {run&&<div className="space-y-2"><div className="flex items-center justify-between text-xs"><span className="text-stone-400">Progress</span><span className="text-stone-300 font-medium">{run.jobs_succeeded}/{run.jobs_total} stages</span></div><div className="h-2 bg-stone-800 rounded-full overflow-hidden"><div className={`h-full rounded-full transition-all duration-500 ${hasFail?"bg-red-500":p===100?"bg-emerald-500":"bg-blue-500"}`} style={{width:`${p}%`}}/></div></div>}
        {run&&<div><h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-3">Pipeline</h4><StageTimeline stages={run.stages||[]} pipelineType={run.pipeline_type}/></div>}
        {run?.last_event&&<LastActivity event={run.last_event} pipelineType={run.pipeline_type}/>}
        {stale&&<div className="bg-orange-950/20 border border-orange-900/30 rounded-lg p-3"><div className="flex items-start gap-2"><AlertOctagon className="w-4 h-4 text-orange-400 shrink-0 mt-0.5"/><div><p className="text-xs text-orange-300 font-medium">Out of date</p><p className="text-[11px] text-orange-400/80 mt-0.5">Changed: {listing.stale_stages.map(s=>s.label).join(", ")}. Clear from &ldquo;{listing.stale_stages[0]?.label}&rdquo; to update.</p></div></div></div>}
        <div className="space-y-2 pt-2">
          <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider">Actions</h4>
          <ClearDropdown listingId={listing.id} onDone={onRefresh}/>
          <div className="pt-3 border-t border-stone-800/30">
            {!delConf?<button onClick={()=>setDelConf(true)} className="w-full flex items-center justify-center gap-2 px-4 py-2 text-xs font-medium rounded-lg border border-red-900/50 text-red-400/70 hover:text-red-400 hover:bg-red-900/10 transition-colors"><Trash2 className="w-3.5 h-3.5"/> Delete listing</button>:(
              <div className="space-y-2"><p className="text-[11px] text-red-400 text-center">Delete listing {listing.id} and ALL data permanently?</p><div className="flex gap-2"><button onClick={del} disabled={deleting} className="flex-1 px-3 py-2 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-500 disabled:opacity-50 transition-colors">{deleting?<Loader2 className="w-3 h-3 animate-spin mx-auto"/>:"Yes, delete"}</button><button onClick={()=>setDelConf(false)} className="px-3 py-2 text-xs rounded-lg border border-stone-700 text-stone-400 hover:text-white transition-colors">Cancel</button></div></div>
            )}
          </div>
        </div>
        {run&&<div className="text-[11px] text-stone-600 space-y-1 pt-2 border-t border-stone-800/30"><p>Run: <span className="text-stone-500 font-mono">{run.run_id}</span></p><p>Started: {fmtFull(run.created_at)}</p>{run.updated_at&&<p>Updated: {fmtFull(run.updated_at)}</p>}</div>}
      </div>
      <div className="flex-1 min-w-0 space-y-5">
        {run&&<CostDetail runId={run.run_id}/>}
        <ComparablesPanel listingId={listing.id} />
        {run&&<div><h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-3">Logs</h4><LogViewer runId={run.run_id}/></div>}
      </div>
    </div></div>
  </div>);
};

// ── Listing Row ──
const Row: React.FC<{listing:ListingItem;onSelect:()=>void}> = ({listing,onSelect}) => {
  const run=listing.latest_run; const st=describeRun(run); const p=pct(run); const stale=listing.stale_stages.length>0;
  const hasFail=runHasActionableFail(run);
  const pipelineType = run?.pipeline_type || "";
  // Use last_event time as "Updated" — more accurate than run.updated_at
  const lastActivityTime = run?.last_event?.created_at || run?.updated_at || listing.updated_at;
  const pipelineBadge = pipelineType === "gla" ? { label: "GLA", cls: "bg-violet-900/30 text-violet-300 border-violet-800/50" }
    : pipelineType === "v5" ? { label: "V5", cls: "bg-blue-900/30 text-blue-300 border-blue-800/50" }
    : pipelineType ? { label: pipelineType.toUpperCase(), cls: "bg-stone-800 text-stone-300 border-stone-700" }
    : null;
  return(<button onClick={onSelect} className="w-full text-left hover:bg-stone-800/30 transition-colors border-b border-stone-800/30 group" aria-label={`Open listing ${listing.id}`}>
    {/* Desktop row */}
    <div className="hidden sm:flex items-center gap-4 px-5 py-3.5">
      <span className="shrink-0 w-10 text-sm font-mono font-bold text-stone-200">{listing.id}</span>
      <span className={`shrink-0 flex items-center gap-1.5 text-xs min-w-[160px] ${st.color}`}>{st.icon}<span className="truncate">{st.label}</span></span>
      {pipelineBadge && <span className={`shrink-0 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${pipelineBadge.cls}`}>{pipelineBadge.label}</span>}
      {stale&&<span className="shrink-0 flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium bg-orange-900/30 text-orange-400 border border-orange-800/50"><AlertOctagon className="w-2.5 h-2.5"/> Stale</span>}
      {run&&<span className="shrink-0 w-24 flex items-center gap-2"><span className="flex-1 h-1.5 bg-stone-800 rounded-full overflow-hidden"><span className={`block h-full rounded-full ${hasFail?"bg-red-500":p===100?"bg-emerald-500":"bg-blue-500"}`} style={{width:`${p}%`}}/></span><span className="text-[10px] text-stone-600 tabular-nums w-7 text-right">{p}%</span></span>}
      <span className="flex-1 min-w-0 truncate text-xs text-stone-600 font-mono">{domain(listing.url)}</span>
      <span className="shrink-0 w-16 text-right text-[11px] text-stone-600">{fmtTime(lastActivityTime)}</span>
      <ChevronRight className="w-4 h-4 text-stone-700 group-hover:text-stone-400 transition-colors shrink-0"/>
    </div>
    {/* Mobile card */}
    <div className="sm:hidden px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-mono font-bold text-stone-200">{listing.id}</span>
          {pipelineBadge && <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${pipelineBadge.cls}`}>{pipelineBadge.label}</span>}
          {stale&&<span className="flex items-center gap-0.5 px-1 py-0.5 rounded text-[9px] font-medium bg-orange-900/30 text-orange-400 border border-orange-800/50"><AlertOctagon className="w-2 h-2"/> Stale</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-stone-600">{fmtTime(lastActivityTime)}</span>
          <ChevronRight className="w-3.5 h-3.5 text-stone-700 group-hover:text-stone-400 transition-colors"/>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={`flex items-center gap-1.5 text-xs ${st.color}`}>{st.icon}<span className="truncate">{st.label}</span></span>
        {run&&<span className="flex items-center gap-1.5 flex-1 max-w-[100px]"><span className="flex-1 h-1 bg-stone-800 rounded-full overflow-hidden"><span className={`block h-full rounded-full ${hasFail?"bg-red-500":p===100?"bg-emerald-500":"bg-blue-500"}`} style={{width:`${p}%`}}/></span><span className="text-[9px] text-stone-600 tabular-nums">{p}%</span></span>}
      </div>
      {listing.url&&<p className="text-[10px] text-stone-600 font-mono truncate">{domain(listing.url)}</p>}
    </div>
  </button>);
};

// ── Main ──
export default function AdminPage() {
  const[listings,setListings]=useState<ListingItem[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState<string|null>(null);const[selId,setSelId]=useState<number|null>(null);const[refreshing,setRefreshing]=useState(false);
  const[isModalOpen,setIsModalOpen]=useState(false);const[pipelineState,setPipelineState]=useState<PipelineState>("idle");const[pipelineError,setPipelineError]=useState<string|null>(null);
  const fetchL=useCallback(async()=>{try{const r=await fetch("/api/admin/listings");const d=await r.json();if(d.success){setListings(d.listings||[]);setError(null);}else setError(d.error||"Failed");}catch{setError("Network error \u2014 is the backend running?");}finally{setLoading(false);setRefreshing(false);}},[]);
  const isProcessing = pipelineState==="scraping"||pipelineState==="creating"||pipelineState==="triggering";
  const pipelineLabel = pipelineState==="scraping"?"Scraping property link...":pipelineState==="creating"?"Creating listing...":pipelineState==="triggering"?"Triggering pipeline..." : pipelineState==="done"?"Listing added!" : "";
  const openNewListingModal = useCallback(()=>{setPipelineError(null);setPipelineState("idle");setIsModalOpen(true);},[]);
  const handleUrlSubmit = useCallback(async (url: string) => {
    setPipelineError(null);
    setPipelineState("scraping");
    try {
      const scrapeResult = await scrapeUrl(url);
      if (!scrapeResult.success || !scrapeResult.data) throw new Error((scrapeResult as any).error || "Failed scraping URL");
      const scrapedData = scrapeResult.data as ScrapedData;
      const photos = scrapedData.image_urls || scrapedData.photo_urls || [];

      setPipelineState("creating");
      const createResult = await createListing({
        title: scrapedData.title || "Propiedad sin título",
        description: scrapedData.description,
        price_eur: scrapedData.price_eur,
        bedrooms: scrapedData.bedrooms,
        bathrooms: scrapedData.bathrooms,
        m2_built: scrapedData.m2_built,
        m2_useful: scrapedData.m2_useful,
        address: scrapedData.address,
        city: scrapedData.city,
        neighborhood: scrapedData.neighborhood,
        lat: scrapedData.lat,
        lng: scrapedData.lng,
        property_subtype: scrapedData.property_subtype,
        condition: scrapedData.condition,
        floor_level: scrapedData.floor_level,
        floor_number: scrapedData.floor_number,
        has_elevator: scrapedData.has_elevator,
        is_exterior: scrapedData.is_exterior,
        has_terrace: scrapedData.has_terrace,
        has_balcony: scrapedData.has_balcony,
        has_pool: scrapedData.has_pool,
        has_garage: scrapedData.has_garage,
        has_garden: scrapedData.has_garden,
        has_storage: scrapedData.has_storage,
        has_air_conditioning: scrapedData.has_air_conditioning,
        source_url: url,
        image_urls: photos,
        scraped_data: scrapedData as unknown as Record<string, unknown>,
      });
      if (!createResult.success || !createResult.data) throw new Error((createResult as any).error || "Failed creating listing");
      const listingId = createResult.data.id;

      setPipelineState("triggering");
      const runResult = await runPipeline(listingId);
      if (!runResult.success) {
        console.warn("Admin new listing pipeline trigger warning:", runResult.error);
      }

      await fetchL();
      setSelId(listingId);
      setPipelineState("done");
      setIsModalOpen(false);
      setTimeout(()=>setPipelineState("idle"), 1000);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Error creating listing";
      setPipelineError(msg);
      setPipelineState("error");
    }
  },[fetchL]);
  useEffect(()=>{fetchL();},[fetchL]);
  useEffect(()=>{const active=listings.some(l=>{const r=l.latest_run;if(!r)return false;return r.jobs_in_progress>0||r.jobs_queued>0;});if(!active)return;const iv=setInterval(fetchL,8000);return()=>clearInterval(iv);},[listings,fetchL]);
  useEffect(()=>{
    const handleGlobalPaste = (e: KeyboardEvent) => {
      if (!((e.metaKey || e.ctrlKey) && e.key === "v")) return;
      if (isModalOpen) return;
      const activeElement = document.activeElement;
      if (activeElement?.tagName === "INPUT" || activeElement?.tagName === "TEXTAREA") return;
      e.preventDefault();
      openNewListingModal();
    };
    window.addEventListener("keydown", handleGlobalPaste);
    return () => window.removeEventListener("keydown", handleGlobalPaste);
  }, [isModalOpen, openNewListingModal]);
  const[stoppingAll,setStoppingAll]=useState(false);const[resumingAll,setResumingAll]=useState(false);
  const refresh=()=>{setRefreshing(true);fetchL();};
  const stopAll=async()=>{setStoppingAll(true);try{await fetch("/api/admin/stop-all",{method:"POST"});fetchL();}catch{}finally{setStoppingAll(false);}};
  const resumeAll=async()=>{setResumingAll(true);try{await fetch("/api/admin/resume-all",{method:"POST"});fetchL();}catch{}finally{setResumingAll(false);}};
  const sel=useMemo(()=>listings.find(l=>l.id===selId)||null,[listings,selId]);
  const stats=useMemo(()=>{
    const t=listings.length;
    const run=listings.filter(l=>{const r=l.latest_run;return r&&(r.jobs_in_progress>0||r.jobs_queued>0);}).length;
    const ok=listings.filter(l=>l.latest_run&&l.latest_run.jobs_succeeded===l.latest_run.jobs_total&&l.latest_run.jobs_total>0).length;
    const fail=listings.filter(l=>l.latest_run&&l.latest_run.jobs_failed>0&&l.latest_run.jobs_in_progress===0).length;
    const stopped=listings.filter(l=>{const r=l.latest_run;return r&&r.jobs_in_progress===0&&r.jobs_queued===0&&r.jobs_succeeded>0&&r.jobs_succeeded<r.jobs_total&&r.jobs_failed===0;}).length;
    const stale=listings.filter(l=>l.stale_stages.length>0).length;
    return{t,run,ok,fail,stopped,stale};
  },[listings]);

  const[sidebarOpen,setSidebarOpen]=useState(false);
  return(<div className="min-h-screen bg-gradient-to-b from-[#0a0a0a] to-[#121212] text-stone-200 flex">
    {/* Mobile header bar — visible only on small screens */}
    <div className="md:hidden fixed top-0 left-0 right-0 z-30 bg-[#0d0d0d] border-b border-[#da654d]/20 px-4 py-2.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button onClick={()=>setSidebarOpen(!sidebarOpen)} className="p-1.5 rounded-lg hover:bg-stone-800 text-stone-400 hover:text-white transition-colors" aria-label="Toggle menu"><LayoutList className="w-5 h-5"/></button>
        <h1 className="text-base font-bold tracking-tight"><span className="text-white">Leo</span><span className="text-[#da654d]">.admin</span></h1>
      </div>
      <button onClick={openNewListingModal} className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-[#da654d] text-white hover:bg-[#c8553d] transition-colors"><Sparkles className="w-3.5 h-3.5"/> New</button>
    </div>
    {/* Sidebar backdrop — mobile only */}
    {sidebarOpen&&<div className="md:hidden fixed inset-0 bg-black/60 z-30" onClick={()=>setSidebarOpen(false)}/>}
    {/* Sidebar */}
    <aside className={`${sidebarOpen?"translate-x-0":"-translate-x-full"} md:translate-x-0 fixed md:sticky top-0 left-0 z-40 md:z-auto w-56 shrink-0 bg-[#0d0d0d] border-r border-[#da654d]/20 flex flex-col h-screen transition-transform duration-200`}>
      <div className="p-4 border-b border-[#da654d]/20"><a href="/listings" className="flex items-center gap-2 text-stone-500 hover:text-white transition-colors text-xs"><ChevronLeft className="w-3.5 h-3.5"/> Back to app</a><h1 className="mt-3 text-lg font-bold tracking-tight"><span className="text-white">Leo</span><span className="text-[#da654d]">.admin</span></h1><p className="mt-1 text-[11px] text-stone-500">Ops & pipeline control</p></div>
      <nav className="flex-1 p-2 space-y-0.5">
        <button onClick={()=>setSidebarOpen(false)} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm bg-[#da654d]/20 text-[#ffd9cf] border border-[#da654d]/40"><LayoutList className="w-4 h-4"/> Listings<span className="ml-auto text-[10px] bg-[#da654d]/30 text-[#ffd9cf] px-1.5 py-0.5 rounded-full tabular-nums">{stats.t}</span></button>
        <button onClick={()=>{openNewListingModal();setSidebarOpen(false);}} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm bg-[#da654d] text-white hover:bg-[#c8553d] transition-colors"><Sparkles className="w-4 h-4"/> New listing</button>
        <div className="pt-4 mt-4 border-t border-stone-800/30"><p className="px-3 text-[10px] uppercase tracking-wider text-stone-700 mb-1">Coming soon</p><div className="flex items-center gap-2.5 px-3 py-2 text-sm text-stone-700"><Users className="w-4 h-4"/> Users</div><div className="flex items-center gap-2.5 px-3 py-2 text-sm text-stone-700"><Settings className="w-4 h-4"/> Settings</div></div>
      </nav>
      <div className="p-3 border-t border-stone-800/50 text-[10px] text-stone-700">V5 pipeline &middot; {STATUS_STAGES.length} stages</div>
    </aside>
    <main className="flex-1 min-w-0 flex flex-col pt-12 md:pt-0">
      {isProcessing&&<div className="fixed top-5 left-1/2 -translate-x-1/2 z-40 bg-[#da654d] text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 text-sm"><Loader2 className="w-4 h-4 animate-spin"/>{pipelineLabel}</div>}
      {pipelineState==="done"&&<div className="fixed top-5 left-1/2 -translate-x-1/2 z-40 bg-emerald-600 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 text-sm"><CheckCircle className="w-4 h-4"/> Listing created</div>}
      {sel ? (
        sel.latest_run?.pipeline_type === "gla" ? (
          <GLADetail listing={sel} onBack={() => setSelId(null)} onRefresh={fetchL} />
        ) : (
          <Detail listing={sel} onBack={()=>setSelId(null)} onRefresh={fetchL}/>
        )
      ) : (<>
        <header className="sticky top-0 z-20 bg-[#0a0a0a]/95 backdrop-blur-sm border-b border-[#da654d]/20">
          <div className="px-4 sm:px-6 py-3 sm:py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"><div><h2 className="text-base font-semibold text-white">Listings</h2><p className="text-xs text-stone-500 mt-0.5 hidden sm:block">Pipeline status, logs, costs, and management</p></div><div className="flex items-center gap-2 flex-wrap">{stats.run>0&&<button onClick={stopAll} disabled={stoppingAll} className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs border border-red-800/60 rounded-lg text-red-400 hover:text-white hover:bg-red-900/30 hover:border-red-700 disabled:opacity-50 transition-colors" aria-label="Stop all running pipelines">{stoppingAll?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<StopCircle className="w-3.5 h-3.5"/>} Stop all</button>}{(stats.fail>0||stats.stopped>0)&&<button onClick={resumeAll} disabled={resumingAll} className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs border border-emerald-800/60 rounded-lg text-emerald-400 hover:text-white hover:bg-emerald-900/30 hover:border-emerald-700 disabled:opacity-50 transition-colors" aria-label="Resume all stopped/failed pipelines">{resumingAll?<Loader2 className="w-3.5 h-3.5 animate-spin"/>:<Play className="w-3.5 h-3.5"/>} Resume all</button>}<button onClick={openNewListingModal} className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-[#da654d] text-white hover:bg-[#c8553d] transition-colors"><Sparkles className="w-3.5 h-3.5"/> New listing</button><button onClick={refresh} disabled={refreshing} className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 text-xs border border-stone-800 rounded-lg text-stone-400 hover:text-white hover:border-stone-600 disabled:opacity-50 transition-colors"><RefreshCw className={`w-3.5 h-3.5 ${refreshing?"animate-spin":""}`}/> <span className="hidden sm:inline">Refresh</span></button></div></div>
          <div className="px-4 sm:px-6 py-2 flex items-center gap-3 sm:gap-5 text-[10px] sm:text-xs border-t border-stone-800/30 overflow-x-auto">
            <span className="text-stone-400 whitespace-nowrap"><strong className="text-stone-200">{stats.t}</strong> listings</span>
            {stats.run>0&&<span className="text-blue-400 flex items-center gap-1 whitespace-nowrap"><Loader2 className="w-3 h-3 animate-spin"/><strong>{stats.run}</strong> running</span>}
            {stats.ok>0&&<span className="text-emerald-400 whitespace-nowrap"><strong>{stats.ok}</strong> complete</span>}
            {stats.stopped>0&&<span className="text-orange-400 flex items-center gap-1 whitespace-nowrap"><Square className="w-3 h-3"/><strong>{stats.stopped}</strong> stopped</span>}
            {stats.fail>0&&<span className="text-red-400 whitespace-nowrap"><strong>{stats.fail}</strong> failed</span>}
            {stats.stale>0&&<span className="text-orange-400 flex items-center gap-1 whitespace-nowrap"><AlertOctagon className="w-3 h-3"/><strong>{stats.stale}</strong> stale</span>}
          </div>
        </header>
        <div className="flex-1 p-3 sm:p-6">
          {loading&&<div className="flex items-center justify-center py-20"><Loader2 className="w-5 h-5 animate-spin text-stone-600"/><span className="ml-3 text-sm text-stone-500">Loading...</span></div>}
          {error&&!loading&&<div className="flex flex-col items-center justify-center py-20 text-center"><XCircle className="w-8 h-8 text-red-500 mb-3"/><p className="text-red-400 text-sm">{error}</p><button onClick={refresh} className="mt-3 text-xs text-stone-500 hover:text-white underline">Try again</button></div>}
          {!loading&&!error&&listings.length===0&&<div className="flex flex-col items-center justify-center py-20 text-center"><LayoutList className="w-8 h-8 text-stone-700 mb-3"/><p className="text-stone-500 text-sm">No listings yet.</p></div>}
          {!loading&&!error&&listings.length>0&&(
            <div className="bg-[#111111] rounded-xl border border-stone-800/50 overflow-hidden">
              <div className="hidden sm:flex items-center gap-4 px-5 py-2 text-[10px] uppercase tracking-wider text-stone-600 border-b border-stone-800/50 font-medium"><span className="w-10">ID</span><span className="min-w-[160px]">Status</span><span className="w-24">Progress</span><span className="flex-1">Source</span><span className="w-16 text-right">Updated</span><span className="w-4"/></div>
              {listings.map(l=><Row key={l.id} listing={l} onSelect={()=>setSelId(l.id)}/>)}
            </div>
          )}
        </div>
      </>)}
    </main>
    <PasteLinkModal
      isOpen={isModalOpen}
      onClose={() => {
        if (!isProcessing) {
          setIsModalOpen(false);
          setPipelineError(null);
          setPipelineState("idle");
        }
      }}
      onSubmit={handleUrlSubmit}
      isLoading={isProcessing}
      error={pipelineError}
    />
  </div>);
}
