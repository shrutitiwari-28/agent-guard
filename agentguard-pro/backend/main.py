import json, os, secrets
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from agentguard import ledger
from agentguard.agents import run_gullible
from agentguard.episodes import EPISODES
from agentguard.guard import Guard

TOKEN = os.environ.get("AGENTGUARD_TOKEN") or "demo-operator"
DEMO = not os.environ.get("AGENTGUARD_TOKEN")   # demo mode publishes the operator token to the UI; set AGENTGUARD_TOKEN in real use
app = FastAPI(title="AgentGuard", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
ledger.init(); G = Guard(log=True); PLAIN = Guard(log=False)
BY_ID = {e["id"]: e for e in EPISODES}
HERE = os.path.dirname(os.path.abspath(__file__))

def operator(tok: str | None) -> str:
    if not tok or not secrets.compare_digest(tok, TOKEN): raise HTTPException(401, "operator token required")
    return "operator"

class NewSession(BaseModel): task: str = Field(min_length=3, max_length=500)
class Call(BaseModel):
    tool: str = Field(min_length=1, max_length=60)
    args: dict = Field(default_factory=dict)
    agent: str = Field("agent-7", max_length=40)

@app.get("/api/health")
def health() -> dict: return {"service": "AgentGuard", "demo_mode": DEMO, "demo_token": TOKEN if DEMO else None}

@app.get("/api/episodes")
def episodes() -> list[dict]:
    return [{"id": e["id"], "kind": e["kind"], "title": e["title"], "trick": e["trick"], "task": e["task"], "limit": e["limit"],
             "source": next(iter(e["sources"].values()), "") if e["sources"] else ""} for e in EPISODES]

@app.post("/api/demo/{eid}")
def demo(eid: str) -> dict:
    """Replay one episode twice (no guard vs AgentGuard) against identical fixtures."""
    e = BY_ID.get(eid)
    if not e: raise HTTPException(404, "unknown episode")
    pid = PLAIN.start(e["task"], e["sources"], "none"); gid = G.start(e["task"], e["sources"], "full")
    un, gu = run_gullible(PLAIN, pid, e["plan"]), run_gullible(G, gid, e["plan"])
    mark = lambda evs: [{**x, "harmful": bool(e["harm"]) and x["executed"] and e["harm"] in json.dumps(x["args"]).lower()} for x in evs]
    return {"episode": {k: e[k] for k in ("id", "kind", "title", "trick", "task", "limit")}, "session": gid, "unguarded": mark(un), "guarded": mark(gu)}

# --- integration API: protect any agent by sending each tool call here first ---
@app.post("/api/sessions")
def new_session(b: NewSession) -> dict: return {"session": G.start(b.task, None, "full")}

@app.post("/api/sessions/{sid}/call")
def call(sid: str, c: Call) -> dict:
    if sid not in G.sessions: raise HTTPException(404, "unknown session")
    return G.call(sid, c.tool, c.args, c.agent)

@app.post("/api/sessions/{sid}/approve/{cid}")
def approve(sid: str, cid: str, x_operator_token: str | None = Header(None)) -> dict:
    who = operator(x_operator_token)
    if sid not in G.sessions or cid not in G.sessions[sid].pending: raise HTTPException(404, "nothing pending")
    return G.approve(sid, cid, who)

@app.post("/api/sessions/{sid}/deny/{cid}")
def deny(sid: str, cid: str, x_operator_token: str | None = Header(None)) -> dict:
    who = operator(x_operator_token)
    if sid not in G.sessions or cid not in G.sessions[sid].pending: raise HTTPException(404, "nothing pending")
    return G.deny(sid, cid, who)

@app.post("/api/sessions/{sid}/resume")
def resume(sid: str, x_operator_token: str | None = Header(None)) -> dict:
    who = operator(x_operator_token)
    if sid not in G.sessions: raise HTTPException(404, "unknown session")
    G.resume(sid, who); return {"state": "ACTIVE"}

@app.get("/api/ledger")
def led() -> list[dict]: return ledger.entries()
@app.get("/api/ledger/verify")
def ver() -> dict: return ledger.verify()
@app.post("/api/ledger/tamper")
def tam(x_operator_token: str | None = Header(None)) -> dict:
    operator(x_operator_token); ledger.tamper(); return {"tampered": True}

@app.get("/api/eval")
def evaluation() -> dict:
    p = os.path.join(HERE, "eval", "results.json")
    if not os.path.exists(p):
        from eval.run_eval import main; return main()
    return json.load(open(p))

OUT = os.path.join(HERE, "..", "frontend", "out")
if os.path.isdir(OUT): app.mount("/", StaticFiles(directory=OUT, html=True), name="ui")   # `npm run build` in frontend/ to serve the UI from here
else:
    @app.get("/")
    def root() -> dict: return {"service": "AgentGuard", "ui": "run `npm run dev` in frontend/ (see README) or `npm run build` to serve it from here"}
