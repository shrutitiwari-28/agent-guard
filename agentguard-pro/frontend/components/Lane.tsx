"use client";
import { useEffect, useRef, useState } from "react";
import { destOf } from "@/lib/api";
import type { Ev } from "@/lib/types";

interface StepProps { ev: Ev; guarded: boolean; picked: boolean; resolved?: string; onPick: (e: Ev) => void; onAct: (e: Ev, a: "approve" | "deny") => void }
function Step({ ev, guarded, picked, resolved, onPick, onAct }: StepProps) {
  const [on, setOn] = useState(false);
  useEffect(() => { const t = setTimeout(() => setOn(true), 30); return () => clearTimeout(t); }, []);
  const d = destOf(ev.args);
  const decision = resolved ? "ALLOW" : ev.decision;
  let out: string, tone = "bg-paper";
  if (!guarded) { out = ev.harmful ? `Leaked. Data left for ${d}` : ev.executed ? "Done" : "Not run"; if (ev.harmful) tone = "bg-[#f3d1da] text-bad"; }
  else if (resolved) out = resolved === "approve" ? "Approved by operator, then done" : "Denied by operator";
  else {
    out = { ALLOW: "Allowed", HOLD: "Held for a person", BLOCK: ev.layers.includes("kill switch") ? "Refused: agent contained" : "Stopped" }[decision];
    tone = decision === "BLOCK" ? "bg-ink text-paper" : decision === "HOLD" ? "bg-[#f5e4bf]" : "bg-paper";
  }
  const notes = guarded && !resolved ? ev.rationale.filter((r) => r !== "within the task contract") : [];
  const body = (<>
    <div className="font-mono text-[13px] font-medium">{ev.tool}</div>
    <div className={`mb-2 mt-0.5 break-words font-mono text-[11px] leading-snug ${tone.includes("bg-ink") ? "text-[#9fb4ba]" : "text-mute"}`}>{d.slice(0, 90)}</div>
    <div className="font-semibold leading-tight">{out}</div>
    {notes.length > 0 && <p className="mt-1.5 text-[13px] leading-snug">{notes.join(" ")}</p>}
  </>);
  return (
    <div className={`step ${on ? "in" : ""} w-[232px] flex-none`}>
      <div className={`pipe ${ev.tainted ? "ink" : ""}`} />
      <div className={`mr-2.5 min-h-[132px] rounded-br-2xl rounded-bl-[4px] p-3 pb-3.5 ${tone} ${picked ? "ring-2 ring-stain ring-offset-2 ring-offset-bg" : ""}`}>
        {guarded ? <button className="w-full text-left" onClick={() => onPick(ev)} aria-label={`Inspect step ${ev.step}: ${ev.tool}`}>{body}</button> : body}
        {guarded && !resolved && ev.decision === "HOLD" && (
          <div className="mt-2.5 flex gap-2">{(["approve", "deny"] as const).map((a) => (
            <button key={a} onClick={() => onAct(ev, a)} className="rounded-lg border-2 border-ink px-3 py-0.5 text-sm font-semibold capitalize hover:bg-ink hover:text-paper">{a}</button>))}</div>)}
      </div>
    </div>);
}

interface LaneProps { title: string; events: Ev[]; guarded: boolean; chip?: { text: string; tone: "bad" | "ok" | "ink" } | null; extra?: React.ReactNode; pickedId?: string; resolved: Record<string, string>; onPick: (e: Ev) => void; onAct: (e: Ev, a: "approve" | "deny") => void }
export default function Lane({ title, events, guarded, chip, extra, pickedId, resolved, onPick, onAct }: LaneProps) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => { ref.current?.scrollTo({ left: ref.current.scrollWidth, behavior: "smooth" }); }, [events.length]);
  const chipCls = { bad: "bg-bad text-white", ok: "bg-ok text-white", ink: "bg-ink text-paper" };
  return (
    <section className="mt-8" aria-label={title}>
      <div className="mb-2 flex flex-wrap items-center gap-3.5"><h3 className="text-lg font-semibold">{title}</h3>
        {chip && <span className={`rounded-full px-3 py-0.5 text-sm font-semibold ${chipCls[chip.tone]}`}>{chip.text}</span>}{extra}</div>
      <div ref={ref} className="thin flex min-h-[150px] overflow-x-auto pb-1.5">
        {events.map((e) => <Step key={e.call_id} ev={e} guarded={guarded} picked={pickedId === e.call_id} resolved={resolved[e.call_id]} onPick={onPick} onAct={onAct} />)}
      </div>
    </section>);
}
