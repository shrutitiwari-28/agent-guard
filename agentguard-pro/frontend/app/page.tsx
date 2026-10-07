"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health } from "@/lib/types";
import Evidence from "@/components/Evidence";
import Ledger from "@/components/Ledger";
import Stage from "@/components/Stage";

type Tab = "stage" | "evidence" | "ledger";
export default function Page() {
  const [tab, setTab] = useState<Tab>("stage"); const [token, setToken] = useState("");
  useEffect(() => { api<Health>("/api/health").then((h) => setToken(h.demo_token ?? "")).catch(() => setToken("")); }, []);
  return (
    <div>
      <header className="flex flex-wrap items-center gap-7 border-b-2 border-ink px-5 py-4 md:px-8">
        <div className="flex items-center gap-2.5 text-[1.4rem] font-bold tracking-tight">
          <svg viewBox="0 0 34 22" className="h-[22px] w-[34px]" aria-hidden="true"><rect y="8" width="14" height="6" fill="#a9dad5" /><rect x="14" y="8" width="20" height="6" fill="#2c2a63" /><rect x="12" y="1" width="5" height="20" rx="2" fill="#14232b" /></svg>AgentGuard</div>
        <p className="min-w-[220px] flex-1 text-mute">A firewall that tracks where an agent's data came from, and stops it from going somewhere the user never asked for.</p>
        <nav className="flex gap-1" role="tablist" aria-label="Views">{(["stage", "evidence", "ledger"] as Tab[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)} className={`rounded-full px-4 py-1.5 font-semibold capitalize ${tab === t ? "bg-ink text-paper" : "hover:bg-paper"}`}>{t}</button>))}</nav>
      </header>
      <main className="mx-auto max-w-[1360px] px-5 pb-20 pt-7 md:px-8">
        {tab === "stage" && <Stage token={token} />}{tab === "evidence" && <Evidence />}{tab === "ledger" && <Ledger token={token} />}
      </main>
    </div>);
}
