"use client";
import { useCallback, useEffect, useState } from "react";
import { api, errMsg, operator } from "@/lib/api";
import type { LedgerRow, Verify } from "@/lib/types";

export default function Ledger({ token }: { token: string }) {
  const [rows, setRows] = useState<LedgerRow[]>([]); const [v, setV] = useState<Verify | null>(null); const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  const load = useCallback(async () => { try { const [r, x] = await Promise.all([api<LedgerRow[]>("/api/ledger"), api<Verify>("/api/ledger/verify")]); setRows(r); setV(x); setErr(""); } catch (e) { setErr(errMsg(e)); } }, []);
  useEffect(() => { void load(); }, [load]);
  const tamper = async () => { try { await api("/api/ledger/tamper", operator(token)); setMsg("A BLOCK was rewritten as ALLOW. Now verify."); await load(); setV((x) => x); } catch (e) { setErr(errMsg(e)); } };
  return (
    <section>
      <h2 className="text-2xl font-semibold tracking-tight">Forensic ledger</h2>
      <p className="mb-4 mt-1 max-w-[64ch] text-mute">Every decision is chained with a keyed hash. Edit one record, even by recomputing the hashes, and verification fails, because rewriting history needs the key and not just database access. Secrets are redacted before they are written.</p>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <button onClick={tamper} className="rounded-full border-2 border-ink px-5 py-1.5 font-semibold hover:bg-ink hover:text-paper">Tamper with a record</button>
        <button onClick={() => { setMsg(""); void load(); }} className="rounded-full border-2 border-ink px-5 py-1.5 font-semibold hover:bg-ink hover:text-paper">Verify the chain</button>
        {v && <span role="status" className={`font-semibold ${v.ok ? "text-ok" : "text-bad"}`}>{msg && v.ok ? msg : v.ok ? `Chain intact. ${v.checked} records.` : `Chain broken at record #${v.broken_at}.`}</span>}
      </div>
      {err && <p role="alert" className="text-bad">{err}</p>}
      {rows.length === 0 ? <p className="text-mute">No records yet. Run an episode on the Stage tab.</p> : <div className="thin overflow-x-auto">{rows.map((r) => (
        <div key={r.id} className={`grid min-w-[560px] grid-cols-[50px_90px_1fr_70px_110px] gap-2.5 border-t border-rule py-1.5 font-mono text-xs ${v && !v.ok && r.id === v.broken_at ? "bg-[#f3d1da] text-bad" : ""}`}>
          <span>#{r.id}</span><span>{r.session}</span><span className="truncate">{r.tool} {String(r.args).slice(0, 60)}</span>
          <span className={r.decision === "BLOCK" ? "font-medium text-bad" : r.decision === "HOLD" ? "text-hold" : ""}>{r.decision}</span><span>{r.hash}</span></div>))}</div>}
    </section>);
}
