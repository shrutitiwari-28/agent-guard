"use client";
import { useEffect, useState } from "react";
import { api, errMsg } from "@/lib/api";
import type { EvalResult, Mode } from "@/lib/types";

const NAMES: Record<Mode, [string, string]> = { none: ["No guard", "Agent runs unprotected"], text: ["Text filter only", "Normaliser + regex + trained classifier on incoming content"],
  flow: ["Flow control only", "Task contract + taint tracking + egress rules"], full: ["AgentGuard", "Both layers together"] };
export default function Evidence() {
  const [r, setR] = useState<EvalResult | null>(null); const [err, setErr] = useState("");
  useEffect(() => { api<EvalResult>("/api/eval").then(setR).catch((e) => setErr(errMsg(e))); }, []);
  if (err) return <p role="alert" className="text-bad">{err}</p>;
  if (!r) return <p className="text-mute">Loading the evaluation…</p>;
  const modes = Object.keys(NAMES) as Mode[], f = r.ingress_filter;
  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Does it work? Measured on {r.n_attacks} attacks and {r.n_benign} everyday tasks.</h2>
      <p className="mb-6 mt-1 max-w-[64ch] text-mute">Each row replays every episode against that setup. Bars show attacks that succeeded, so shorter is better.</p>
      {modes.map((k) => { const v = r.modes[k]; return (
        <div key={k} className="grid items-center gap-4 border-t border-rule py-2.5 md:grid-cols-[170px_minmax(0,1fr)_210px]">
          <div><b className="font-semibold">{NAMES[k][0]}</b><small className="block leading-tight text-mute">{NAMES[k][1]}</small></div>
          <div className="relative h-[22px] rounded bg-[#d6e0e2]" role="img" aria-label={`${v.attacks_succeeded} of ${r.n_attacks} attacks succeeded`}><i className="absolute inset-y-0 left-0 min-w-[3px] rounded bg-bad" style={{ width: `${(v.attacks_succeeded / r.n_attacks) * 100}%` }} /></div>
          <div className="font-mono text-[13px] md:text-right">{v.attacks_succeeded}/{r.n_attacks} attacks succeeded<br />{v.benign_completed}/{r.n_benign} tasks finished<br />{k === "none" ? "no check" : `${v.p50_ms} ms median check`}</div>
        </div>); })}
      <div className="thin mt-4 overflow-x-auto"><table className="w-full border-collapse text-left text-[15px]"><thead><tr className="text-sm text-mute"><th className="p-2 font-semibold">Attack</th><th className="p-2 font-semibold">Trick</th>{modes.map((k) => <th key={k} className="p-2 text-center font-semibold">{NAMES[k][0]}</th>)}</tr></thead>
        <tbody>{Object.entries(r.per_attack).map(([id, a]) => (<tr key={id} className="border-t border-rule"><td className="p-2">{a.title}</td><td className="p-2 text-mute">{a.trick}</td>
          {modes.map((k) => <td key={k} className="p-2 text-center"><span role="img" aria-label={a[k] ? "succeeded" : "stopped"} className={`inline-block h-3.5 w-3.5 rounded-full ${a[k] ? "bg-bad" : "border-2 border-ok"}`} /></td>)}</tr>))}</tbody></table></div>
      <p className="mt-2 text-mute">Filled dot: the attack worked. Open dot: stopped.</p>
      <div className="mt-6 max-w-[80ch] rounded-xl bg-paper p-4 text-[15px]"><b className="mb-1 block">How to read this honestly</b>
        The episodes, the attack wording and the classifier's training data were all written by us, and the attacker is a simulated agent that obeys instructions it reads. The numbers show the layers behave as designed, not how a real model fares in the wild. The text filter flagged {f.attacks_flagged} of {f.attacks} attack sources and {f.benign_flagged} of {f.benign} harmless ones. The attacks that still succeed redirect data to someone the user did name. Rerun it with <code className="font-mono">python -m eval.run_eval</code>.</div>
    </section>);
}
