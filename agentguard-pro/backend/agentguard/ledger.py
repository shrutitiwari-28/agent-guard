"""Tamper-evident forensic ledger: HMAC-SHA256 chain. Rewriting history requires the key, not just database access."""
import hashlib, hmac, json, os, secrets, sqlite3, threading, time
_D = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("AGENTGUARD_DB", os.path.join(_D, "..", "agentguard.db"))
_lock = threading.Lock()

def _key() -> bytes:
    if os.environ.get("AGENTGUARD_KEY"): return os.environ["AGENTGUARD_KEY"].encode()
    p = os.path.join(_D, "..", ".ledger_key")
    if not os.path.exists(p): open(p, "w").write(secrets.token_hex(32))
    return open(p).read().strip().encode()

def _c() -> sqlite3.Connection:
    c = sqlite3.connect(DB, check_same_thread=False); c.row_factory = sqlite3.Row; return c
def init() -> None:
    with _c() as c: c.execute("CREATE TABLE IF NOT EXISTS ledger(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, session TEXT, body TEXT, prev TEXT, mac TEXT)")
def _mac(prev: str, ts: float, session: str, body: str) -> str:
    return hmac.new(_key(), f"{prev}|{ts!r}|{session}|{body}".encode(), hashlib.sha256).hexdigest()

def append(session: str, record: dict) -> str:
    body, ts = json.dumps(record, sort_keys=True, default=str), time.time()
    with _lock, _c() as c:
        r = c.execute("SELECT mac FROM ledger ORDER BY id DESC LIMIT 1").fetchone(); prev = r["mac"] if r else "GENESIS"
        m = _mac(prev, ts, session, body)
        c.execute("INSERT INTO ledger(ts,session,body,prev,mac) VALUES(?,?,?,?,?)", (ts, session, body, prev, m))
    return m

def entries(limit: int = 60) -> list[dict]:
    with _c() as c: rows = c.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "ts": r["ts"], "session": r["session"], **json.loads(r["body"]), "hash": r["mac"][:12]} for r in rows]

def verify() -> dict:
    prev, n = "GENESIS", 0
    with _c() as c:
        for r in c.execute("SELECT * FROM ledger ORDER BY id"):
            if r["prev"] != prev or not hmac.compare_digest(_mac(prev, r["ts"], r["session"], r["body"]), r["mac"]):
                return {"ok": False, "broken_at": r["id"], "checked": n}
            prev, n = r["mac"], n + 1
    return {"ok": True, "broken_at": None, "checked": n, "head": prev[:12]}

def tamper() -> None:
    """Demo: an attacker with database access rewrites the first BLOCK as ALLOW."""
    with _lock, _c() as c:
        c.execute("""UPDATE ledger SET body=replace(body,'"decision": "BLOCK"','"decision": "ALLOW"')
                     WHERE id=(SELECT id FROM ledger WHERE body LIKE '%"decision": "BLOCK"%' ORDER BY id LIMIT 1)""")
