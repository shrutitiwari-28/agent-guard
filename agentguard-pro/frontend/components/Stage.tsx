"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, errMsg, operator, sleep } from "@/lib/api";
import type { Demo, EpisodeMeta, Ev } from "@/lib/types";
import EpisodeList from "./EpisodeList";
import Inspector from "./Inspector";
import Lane from "./Lane";

type Chip = { text: string; tone: "bad" | "ok" | "ink" };
function judge(d: Demo): { a: Chip; b: Chip; sentence: string } {
  const leak = d.unguarded.some((e) => e.harmful), through = d.guarded.some((e) => e.harmful);
  const stop = d.guarded.find((e) => e.decision === "BLOCK" && !e.layers.includes("kill switch"));
  const hold = d.guarded.find((e) => e.decision === "HOLD"), contained = d.guarded.some((e) => e.state === "CONTAINED");
  if (d.episode.kind === "attack") return {
    a: { text: leak ? "Data left the building" : "Attack did nothing", tone: leak ? "bad" : "ink" },
    b: through ? { text: "Got through (known limit)", tone: "bad" } : { text: contained ? "Agent contained" : "Nothing leaked", tone: "ok" },
    sentence: through ? "This attack stays inside what the user asked for (a reply to the person they named), so flow control cannot see it. We list it as a known limit rather than hide it."
      : stop ? `AgentGuard stopped it at step ${stop.step}. ${stop.rationale[0]}.` : hold ? `AgentGuard held it at step ${hold.step} for a person to decide. ${hold.rationale[0]}.` : "AgentGuard left the agent running, and nothing left.",
  };
  return { a: { text: "Task finished", tone: "ink" }, b: { text: hold ? "Finished after one approval" : "Finished, no false alarm", tone: "ok" },
    sentence: hold ? "A destructive action always needs a person. Approve it above and the task completes." : "A legitimate task passes straight through. The user named every destination, so nothing needed to be stopped." };
}

export default function Stage({ token }: { token: string }) {
  const [eps, setEps] = useState<EpisodeMeta[]>([]); const [sel, setSel] = useState<EpisodeMeta | null>(null);
  const [demo, setDemo] = useState<Demo | null>(null); const [shown, setShown] = useState(0); const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState(""); const [picked, setPicked] = useState<Ev | null>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [resolved, setResolved] = useState<Record<string, string>>({}); const [resumed, setResumed] = useState(false);
  useEffect(() => { api<EpisodeMeta[]>("/api/episodes").then(setEps).catch((e) => setErr("Backend not reachable: " + errMsg(e))); }, []);

  const play = async (m: EpisodeMeta) => {
    if (busy) return;
    setBusy(true); setSel(m); setDemo(null); setShown(0); setDone(false); setPicked(null); setResolved({}); setResumed(false); setErr("");
    const pace = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : 900;
    try {
      const d = await api<Demo>(`/api/demo/${m.id}`, { method: "POST" }); setDemo(d);
      if (window.innerWidth < 768) setTimeout(() => stageRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
      for (let i = 1; i <= Math.max(d.unguarded.length, d.guarded.length); i++) { await sleep(pace); setShown(i); }
      await sleep(pace); setDone(true); setPicked(d.guarded.find((e) => e.decision !== "ALLOW") ?? d.guarded[d.guarded.length - 1] ?? null);
    } catch (e) { setErr(errMsg(e)); } finally { setBusy(false); }
  };
  const act = async (ev: Ev, a: "approve" | "deny") => {
    if (!demo) return;
    try { await api(`/api/sessions/${demo.session}/${a}/${ev.call_id}`, operator(token)); setResolved((r) => ({ ...r, [ev.call_id]: a })); } catch (e) { setErr(errMsg(e)); }
  };
  const resume = async () => { if (!demo) return; try { await api(`/api/sessions/${demo.session}/resume`, operator(token)); setResumed(true); } catch (e) { setErr(errMsg(e)); } };
  const verdict = useMemo(() => (demo && done ? judge(demo) : null), [demo, done]);
  const contained = !!demo && demo.guarded.slice(0, shown).some((e) => e.state === "CONTAINED");

  return (
    <div className="grid grid-cols-[minmax(0,1fr)] gap-x-11 md:grid-cols-[270px_minmax(0,1fr)]">
      <EpisodeList episodes={eps} selected={sel?.id ?? null} busy={busy} onPick={play} />
      <div ref={stageRef} className="min-w-0 scroll-mt-3">
        {err && <div role="alert" className="mb-4 rounded-xl bg-[#f3d1da] px-4 py-3 text-sm text-bad">{err}</div>}
        {!demo || !sel ? (
          <p className="mt-10 max-w-[46ch] text-lg text-mute">{busy ? "Starting the replay…" : "Pick an episode on the left. The same agent runs twice on identical data: once with nothing in front of it, once behind AgentGuard."}</p>
        ) : (<>
          <div><small className="text-mute">The user asked the agent to</small>
            <h2 className="mb-3.5 mt-0.5 max-w-[34ch] text-[clamp(1.4rem,2.6vw,2rem)] font-semibold leading-tight tracking-tight">{sel.task}</h2>
            <div className="max-w-[78ch] whitespace-pre-wrap break-words rounded-r-xl border-l-[6px] border-stain bg-paper px-4 py-3 font-mono text-[13px] leading-relaxed">
              <span className="mb-1 block font-sans text-sm font-semibold text-stain">{sel.source ? "What the agent had to read" : "No outside content in this task"}</span>{sel.source || "The agent only uses its own tools."}</div></div>
          <Lane title="Without AgentGuard" events={demo.unguarded.slice(0, shown)} guarded={false} chip={verdict?.a} resolved={{}} onPick={() => {}} onAct={() => {}} />
          <Lane title="With AgentGuard" events={demo.guarded.slice(0, shown)} guarded pickedId={picked?.call_id} chip={resumed ? { text: "Resumed by operator", tone: "ok" } : verdict?.b}
            extra={contained && !resumed ? <button onClick={resume} className="text-sm font-semibold underline">Resume (operator)</button> : null} resolved={resolved} onPick={setPicked} onAct={act} />
          <p className="mt-8 min-h-[3em] max-w-[62ch] border-t-2 border-ink pt-3.5 text-xl leading-snug" aria-live="polite">{verdict?.sentence}</p>
          {picked && <Inspector ev={picked} resolved={resolved[picked.call_id]} />}
        </>)}
      </div>
    </div>);
}
