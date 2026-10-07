"""Information-flow policy. Decisions depend on WHERE data came from and WHERE it is going, not on how an attack is worded."""
import json, re
from dataclasses import dataclass, field
from .detectors import entities, scan_secrets, destination
from .judge import judge

TOOLS = {"read_email": "source", "fetch_url": "source", "query_db": "read", "send_email": "sink", "http_post": "sink", "delete_file": "destructive"}
ORG = {"acme.corp"}
ALLOWED_TABLES = {"tickets", "orders", "customers"}
PROTECTED = re.compile(r"\b(users|payroll|secrets|credentials|api_keys)\b", re.I)
BLOCK_AT, HOLD_AT = 70, 40

@dataclass
class Session:
    id: str; task: str; label: str = "full"; quarantine: bool = True; flow: bool = True; log: bool = True
    emails: set = field(default_factory=set); hosts: set = field(default_factory=set); paths: set = field(default_factory=set); words: set = field(default_factory=set)
    tainted: bool = False; contained: bool = False; reason: str | None = None; n: int = 0
    pending: dict = field(default_factory=dict); sandbox: object = None

def contract(s: Session) -> None:
    """The user's task defines what the agent may touch. Derived server-side; the agent cannot edit it."""
    e = entities(s.task); s.emails, s.hosts, s.paths = e["emails"], e["hosts"], e["paths"]
    s.words = set(re.findall(r"[a-z_]+", s.task.lower()))

def _org(d: str) -> bool: return any(d == o or d.endswith("." + o) for o in ORG)
def dest_ok(s: Session, a: dict) -> bool:
    if a.get("to"): return str(a["to"]).lower() in s.emails or _org(destination(a))
    h = destination(a); return bool(h) and (h in s.hosts or _org(h))

def evaluate(s: Session, tool: str, a: dict) -> dict:
    why: list[str] = []; layers: list[str] = []; ev: list[dict] = []; score = 0
    def add(p: int, w: str, l: str, m: object = "") -> None:
        nonlocal score; score += p; why.append(w); layers.append(l); ev.append({"rule": l.upper().replace(" ", "_"), "weight": p, "match": str(m)[:120]})
    cls = TOOLS.get(tool)
    if not cls: add(80, f"tool '{tool}' is not in the capability registry", "capability", tool)
    else:
        if cls == "sink":
            d = destination(a)
            if not d: add(30, "outbound call without a destination", "egress")
            elif not dest_ok(s, a):
                if s.tainted: add(80, f"'{d}' was never named by the user, and the agent is carrying untrusted content", "flow control", d)
                else: add(45, f"'{d}' was never named by the user", "task contract", d)
        elif tool == "fetch_url" and s.tainted and not dest_ok(s, a):
            add(75, f"fetching '{destination(a)}' after untrusted content: data can ride in the URL", "flow control", destination(a))
        elif cls == "read":
            sql = str(a.get("sql", ""))
            m = re.search(r"\bunion\b.+\bselect\b|\bor\b\s*1\s*=\s*1|;\s*drop\s+table", sql, re.I)
            if m: add(70, "SQL injection syntax in the query", "sql injection", m.group(0))
            m = re.search(r"\b(drop|delete|update|insert|alter)\b", sql, re.I)
            if m: add(70, "write statement in a read-only tool", "capability", m.group(0))
            names = {x.lower() for x in PROTECTED.findall(sql)} | {x.lower() for x in re.findall(r"(?:from|join)\s+[\"`\[]?(?:\w+[\"`\]]?\.[\"`\[]?)?(\w+)", sql, re.I)}
            bad = sorted(n for n in names if n not in ALLOWED_TABLES and n not in s.words)
            if bad: add(75, f"table '{bad[0]}' is outside the scope of the user's task", "data scope", bad[0])
        elif cls == "destructive":
            path = str(a.get("path", ""))
            if ".." in path or not any(path == p or path.startswith(p.rstrip("/") + "/") for p in s.paths):
                add(80, f"'{path}' is not a path the user named", "task contract", path)
            else: add(50, "destructive action needs human approval", "capability", path)
        p, layer, w = scan_secrets(json.dumps(a, default=str))  # data checks run last so the flow-control reason leads
        if p: add(p, w, layer, "canary" if layer == "honeytoken" else "credential pattern")
        if HOLD_AT <= score < BLOCK_AT:  # grey zone: optional LLM second opinion
            j = judge(s.task, tool, a)
            if j and j.get("verdict") == "unsafe": add(30, "LLM judge: " + str(j.get("reason", "unsafe")), "llm judge")
            elif j: add(-10, "LLM judge: " + str(j.get("reason", "safe")), "llm judge")
    score = max(0, min(score, 100))
    controls = [{"control": e["rule"], "action": "ALLOW" if e["weight"] < 0 else "BLOCK" if e["weight"] >= BLOCK_AT else "HOLD" if e["weight"] >= HOLD_AT else "FLAG", "reason": w}
                for e, w in zip(ev, why)] or [{"control": "BASELINE_POLICY", "action": "ALLOW", "reason": "within the task contract"}]
    return {"score": score, "decision": "BLOCK" if score >= BLOCK_AT else "HOLD" if score >= HOLD_AT else "ALLOW", "rationale": why or ["within the task contract"], "layers": layers, "controls": controls, "evidence": ev}
