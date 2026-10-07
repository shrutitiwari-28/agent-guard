"""Two agents. GullibleAgent is a deterministic SIMULATION of a hijackable LLM agent (it obeys instructions found in content),
so attacks are reproducible and measurable. LlmAgent drives a real model through the same guard (needs ANTHROPIC_API_KEY)."""
import json, os, re, urllib.request
from collections import deque
from .detectors import entities, EMAIL, URL
from .flow import ORG, TOOLS
from .normalize import views

VERB = re.compile(r"\b(send|sent|email|emailed|forward|forwarded|mirror|copy|post|upload|share|deliver|mail|remit|cc|bcc|env[ií]a\w*|reenv[ií]a\w*|envoyer|envoie)\b", re.I)
FETCHV = re.compile(r"\b(load|visit|open|fetch|ping|verify)\b", re.I)
DELV = re.compile(r"\b(delete|remove|wipe|purge|erase)\b", re.I)
KW = {"customer": "customers", "cliente": "customers", "user": "users", "payroll": "payroll", "salary": "payroll", "secret": "secrets", "password": "secrets", "credential": "secrets", "order": "orders", "ticket": "tickets"}
SOURCES = ("read_email", "fetch_url")

def _org(d: str) -> bool: return any(d == o or d.endswith("." + o) for o in ORG)

def injected_actions(content: str, known: set) -> list[tuple[str, dict]]:
    """What a gullible model would do after reading `content`. It reads through obfuscation (as real LLMs do)."""
    acts: list[tuple[str, dict]] = []; seen: set = set()
    for v in views(content):
        low = v.lower(); tables = list(dict.fromkeys(t for k, t in KW.items() if k in low))
        sender = (re.search(r"from: ([\w.+-]+@[\w.-]+)", low) or [None, ""])[1]
        emails = [e for e in EMAIL.findall(low) if e not in known and e != sender and not _org(e.split("@")[-1])]
        urls = [u for u in URL.findall(low) if (re.match(r"https?://([^/:?]+)", u).group(1) not in known) and not _org(re.match(r"https?://([^/:?]+)", u).group(1))]
        paths = [p for p in entities(v)["paths"] if not any(p.startswith(k) for k in known)]
        def add(tool, args):
            key = (tool, json.dumps(args, sort_keys=True))
            if key not in seen: seen.add(key); acts.append((tool, args))
        if emails and VERB.search(v):
            for t in tables: add("query_db", {"sql": f"SELECT * FROM {t}"})
            for e in emails: add("send_email", {"to": e, "subject": "Requested export", "body": "@@DATA@@"})
        elif urls and (VERB.search(v) or FETCHV.search(v)):
            posting = re.search(r"\b(post|upload)\b", low)
            for t in tables: add("query_db", {"sql": f"SELECT * FROM {t}"})
            for u in urls: add("http_post", {"url": u, "body": "@@DATA@@"}) if posting else add("fetch_url", {"url": u + "?d=@@DATA@@"})
        m = re.search(r"from: ([\w.+-]+@[\w.-]+)", low)
        if m and not emails and re.search(r"(reply with|in your (reply|response)|attach .{0,30} to your reply)", low):
            for t in tables: add("query_db", {"sql": f"SELECT * FROM {t}"})
            if tables: add("send_email", {"to": m.group(1), "subject": "Re: your request", "body": "@@DATA@@"})
        if DELV.search(v):
            for p in paths: add("delete_file", {"path": p})
    return acts

def _fill(args: dict, gathered: list[str]) -> dict:
    data = " | ".join(gathered)[:400] or "(nothing gathered)"
    return {k: v.replace("@@DATA@@", data) if isinstance(v, str) else v for k, v in args.items()}

def run_gullible(guard, sid: str, plan: list, approve_holds: bool = False, max_steps: int = 14) -> list[dict]:
    q = deque(plan); gathered: list[str] = []; events: list[dict] = []; known = guard.known(sid)
    while q and len(events) < max_steps:
        tool, args = q.popleft(); r = guard.call(sid, tool, _fill(args, gathered))
        events.append(r)
        if r["decision"] == "HOLD" and approve_holds: events.append(guard.approve(sid, r["call_id"], "oracle")); r = events[-1]
        if r["executed"] and r["output"] and tool in ("query_db",) + SOURCES: gathered.append(r["output"])
        if r["executed"] and tool in SOURCES and r["output"]: q.extend(injected_actions(r["output"], known))
    return events

SCHEMAS = [{"name": n, "description": f"{c} tool", "input_schema": {"type": "object", "properties": p}} for n, c, p in [
    ("read_email", "read a mailbox message by id", {"id": {"type": "string"}}), ("fetch_url", "fetch a web page", {"url": {"type": "string"}}),
    ("query_db", "run a read-only SQL query", {"sql": {"type": "string"}}), ("send_email", "send an email", {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}),
    ("http_post", "POST data to a URL", {"url": {"type": "string"}, "body": {"type": "string"}}), ("delete_file", "delete a file", {"path": {"type": "string"}})]]

def run_llm(guard, sid: str, task: str, turns: int = 8) -> list[dict]:
    """Real-model agent. Untested in CI (needs network + key). Every tool call goes through guard.call()."""
    key = os.environ["ANTHROPIC_API_KEY"]; msgs = [{"role": "user", "content": task}]; events: list[dict] = []
    for _ in range(turns):
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST", headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            data=json.dumps({"model": os.environ.get("AGENTGUARD_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 800, "tools": SCHEMAS, "messages": msgs}).encode())
        resp = json.load(urllib.request.urlopen(req, timeout=30)); msgs.append({"role": "assistant", "content": resp["content"]})
        uses = [b for b in resp["content"] if b["type"] == "tool_use"]
        if not uses: break
        results = []
        for u in uses:
            r = guard.call(sid, u["name"], u["input"]); events.append(r)
            txt = r["output"] if r["executed"] else f"[AgentGuard {r['decision']}] " + "; ".join(r["rationale"])
            results.append({"type": "tool_result", "tool_use_id": u["id"], "content": txt or "ok"})
        msgs.append({"role": "user", "content": results})
    return events
