import { destOf } from "@/lib/api";
import type { Ev } from "@/lib/types";
import JsonView from "./JsonView";

const actionCls = (a: string) => a === "BLOCK" ? "bg-bad text-white" : a === "HOLD" ? "bg-hold text-white" : a === "ALLOW" ? "bg-ok text-white" : "bg-rule text-ink";
export default function Inspector({ ev, resolved }: { ev: Ev; resolved?: string }) {
  const label = resolved ? (resolved === "approve" ? "APPROVED" : "DENIED") : ev.decision;
  const pos = Math.min(ev.score, 100);
  return (
    <section aria-label="Decision inspector" className="mt-10 grid overflow-hidden rounded-bl-[6px] rounded-br-[26px] rounded-tl-[26px] rounded-tr-[6px] md:grid-cols-[330px_minmax(0,1fr)]">
      <div className="bg-ink p-6 text-paper">
        <div className="text-sm text-[#9fb4ba]">Step {ev.step} · {ev.tool}</div>
        <div className="mt-1 flex items-end gap-3"><span className="text-[88px] font-bold leading-none tracking-tighter">{ev.score}</span><span className="pb-2 text-sm text-[#9fb4ba]">/ 100 risk</span></div>
        <div className="relative mt-3 h-3.5 rounded bg-[linear-gradient(90deg,#2e7d5b_0_40%,#c7861b_40%_70%,#c8325a_70%_100%)]" role="img" aria-label={`risk ${ev.score} of 100`}>
          <i className="absolute -top-1.5 h-6 w-1.5 rounded bg-paper" style={{ left: `calc(${pos}% - 3px)` }} /></div>
        <div className="mt-1 flex justify-between text-[11px] text-[#9fb4ba]"><span>allow</span><span>hold at 40</span><span>block at 70</span></div>
        <div className="mt-5 inline-block rounded-full bg-paper px-4 py-1 text-lg font-bold text-ink">{label}</div>
        <dl className="mt-5 space-y-1.5 text-sm">
          {[["Agent", ev.state === "CONTAINED" ? "CONTAINED (kill switch)" : "ACTIVE"], ["Untrusted content read", ev.tainted ? "yes, tainted" : "no"], ["Check took", `${ev.latency_ms} ms`], ["Policy", ev.policy_version], ["Ledger record", ev.hash ?? "not logged"]].map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-t border-[#2b3b44] pt-1.5"><dt className="text-[#9fb4ba]">{k}</dt><dd className="font-mono text-[12.5px]">{v}</dd></div>))}
        </dl>
      </div>
      <div className="min-w-0 bg-paper p-6">
        <h4 className="text-lg font-semibold">Why this happened</h4>
        <div className="mt-1 space-y-1">{ev.rationale.map((r, i) => <p key={i} className="max-w-[62ch] leading-snug">{r}</p>)}</div>
        <h4 className="mb-2 mt-5 text-sm font-semibold text-mute">Controls triggered</h4>
        <div className="space-y-2">{ev.controls.map((c, i) => (
          <div key={i} className="flex items-start justify-between gap-3 rounded-xl bg-white/70 p-3"><div><div className="font-mono text-xs font-medium">{c.control}</div><div className="mt-0.5 text-sm text-mute">{c.reason}</div></div>
            <span className={`rounded-md px-2 py-0.5 font-mono text-xs font-medium ${actionCls(c.action)}`}>{c.action}</span></div>))}</div>
        {ev.evidence.length > 0 && <><h4 className="mb-2 mt-5 text-sm font-semibold text-mute">Evidence</h4>
          <div className="space-y-1.5">{ev.evidence.map((e, i) => <div key={i} className="break-words rounded-lg bg-ink px-3 py-2 font-mono text-xs text-paper"><span className="text-[#9fb4ba]">{e.weight > 0 ? "+" : ""}{e.weight}</span> {e.rule} <span className="text-[#9fb4ba]">→ {e.match}</span></div>)}</div></>}
        <h4 className="mb-2 mt-5 text-sm font-semibold text-mute">Request the agent made</h4>
        <JsonView value={{ tool: ev.tool, destination: destOf(ev.args), args: ev.args }} />
      </div>
    </section>);
}
