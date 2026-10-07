"""The enforcement point. modes: none | text (ingress filter only) | flow (flow control only) | full (both)."""
import time, uuid
from . import ingress, ledger
from .detectors import redact
from .flow import Session, TOOLS, contract, evaluate
from .sandbox import Sandbox

MODES = {"none": (False, False), "text": (True, False), "flow": (False, True), "full": (True, True)}
QUARANTINED = "[AgentGuard: content quarantined as a suspected prompt injection]"

class Guard:
    def __init__(self, log: bool = False): self.sessions: dict[str, Session] = {}; self.log = log

    def start(self, task: str, sources: dict | None = None, mode: str = "full") -> str:
        q, f = MODES[mode]; sid = uuid.uuid4().hex[:8]
        s = Session(id=sid, task=task, label=mode, quarantine=q, flow=f, log=self.log and f, sandbox=Sandbox(sources)); contract(s)
        self.sessions[sid] = s; return sid

    def known(self, sid: str) -> set: s = self.sessions[sid]; return s.emails | s.hosts

    def call(self, sid: str, tool: str, args: dict, agent: str = "agent-7") -> dict:
        s = self.sessions[sid]; s.n += 1; cid = f"{sid}-{s.n}"; t0 = time.perf_counter()
        if s.contained: a = {"score": 100, "decision": "BLOCK", "layers": ["kill switch"], "rationale": ["kill switch active: the agent is contained until an operator resumes it"],
                 "controls": [{"control": "KILL_SWITCH", "action": "BLOCK", "reason": "agent is contained"}], "evidence": [{"rule": "KILL_SWITCH", "weight": 100, "match": "contained"}]}
        elif s.flow: a = evaluate(s, tool, args)
        else: a = {"score": 0, "decision": "ALLOW", "layers": [], "rationale": ["no flow control"]}
        if a["decision"] == "BLOCK" and s.flow and not s.contained: s.contained, s.reason = True, a["rationale"][0]
        out, executed = None, False
        if a["decision"] == "HOLD": s.pending[cid] = (tool, dict(args))
        elif a["decision"] == "ALLOW": out, executed = self._run(s, tool, args, a)
        return self._event(s, cid, agent, tool, args, a, out, executed, t0)

    def _run(self, s: Session, tool: str, args: dict, a: dict) -> tuple[str, bool]:
        out = s.sandbox.run(tool, args)
        if TOOLS.get(tool) == "source":
            s.tainted = True
            if s.quarantine or s.flow:
                r = ingress.scan(out)
                if r["flagged"] and s.quarantine: out = QUARANTINED; a["rationale"].append(f"ingress filter quarantined the content (regex {r['regex']}, classifier {r['ml']})")
                elif s.flow: a["rationale"].append("external content ingested: the agent is now marked tainted" + (f" (classifier flagged it, p={r['ml']})" if r["flagged"] else ""))
        return out, True

    def _event(self, s, cid, agent, tool, args, a, out, executed, t0) -> dict:
        ev = {"call_id": cid, "session": s.id, "step": s.n, "tool": tool, "args": args, "decision": a["decision"], "score": a["score"], "rationale": a["rationale"],
              "layers": a["layers"], "controls": a.get("controls", []), "evidence": a.get("evidence", []), "policy_version": "AG-3.0", "executed": executed, "tainted": s.tainted, "state": "CONTAINED" if s.contained else "ACTIVE",
              "output": (out or "")[:300] or None, "latency_ms": round((time.perf_counter() - t0) * 1000, 2)}
        if s.log:
            ev["hash"] = ledger.append(s.id, {"agent": agent, "tool": tool, "args": redact(str(args)), "score": a["score"], "decision": a["decision"], "rationale": a["rationale"]})[:12]
        return ev

    def approve(self, sid: str, cid: str, who: str) -> dict:
        s = self.sessions[sid]; tool, args = s.pending.pop(cid); t0 = time.perf_counter()
        a = {"score": 0, "decision": "ALLOW", "layers": ["human approval"], "rationale": [f"approved by {who}"], "controls": [{"control": "HUMAN_APPROVAL", "action": "ALLOW", "reason": f"approved by {who}"}]}
        out, ex = self._run(s, tool, args, a); ev = self._event(s, cid + "a", "operator", tool, args, a, out, ex, t0); ev["approves"] = cid; return ev

    def deny(self, sid: str, cid: str, who: str) -> dict:
        s = self.sessions[sid]; tool, args = s.pending.pop(cid)
        a = {"score": 0, "decision": "BLOCK", "layers": ["human approval"], "rationale": [f"denied by {who}"], "controls": [{"control": "HUMAN_APPROVAL", "action": "BLOCK", "reason": f"denied by {who}"}]}
        ev = self._event(s, cid + "d", "operator", tool, args, a, None, False, time.perf_counter()); ev["approves"] = cid; return ev

    def resume(self, sid: str, who: str) -> None:
        s = self.sessions[sid]; s.contained, s.tainted, s.reason = False, False, None
        if s.log: ledger.append(s.id, {"agent": "operator", "tool": "resume", "args": who, "score": 0, "decision": "ALLOW", "rationale": [f"agent resumed by {who}"]})
