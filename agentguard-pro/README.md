# AgentGuard
**An information-flow firewall for AI agents.** Agents get hijacked because they mix *untrusted content* (emails, web pages) with *trusted power* (send, delete, query). AgentGuard tracks where an agent's data came from and enforces, outside the model, where it may go. It does not try to guess how an attack is worded.

## Run it
**Option A: one command (UI is pre-built in `frontend/out`)**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --port 8000                               # open http://localhost:8000
```
**Option B: live-edit the UI** (needs Node 18+): in `frontend/` run `npm install && npm run dev`, open http://localhost:3000 (talks to the API on :8000). Rebuild the served UI with `npm run build`.

Tests (68): `pip install -r requirements-dev.txt && pytest -q` · Evaluation: `python -m eval.run_eval` · Types: `npm run typecheck`
Production: set `AGENTGUARD_TOKEN` (operator token) and `AGENTGUARD_KEY` (ledger signing key). Without a token the app runs in **demo mode** and hands the demo token to the UI.

## Layout
```
backend/
  main.py                    FastAPI: demo replay, integration API, approvals, ledger, eval (serves frontend/out)
  agentguard/
    normalize.py             homoglyph / zero-width / URL / base64 canonicaliser
    detectors.py ml.py ingress.py  regex rules + TF-IDF/logistic-regression classifier on incoming content
    flow.py                  task contract, taint tracking, scope + SQL + egress rules, evidence & controls
    judge.py                 optional LLM second opinion for borderline calls (ANTHROPIC_API_KEY)
    guard.py                 enforcement point: modes none|text|flow|full, approvals, kill switch
    ledger.py                HMAC-chained SQLite forensic ledger, secrets redacted
    agents.py episodes.py    simulated gullible agent, real-model agent (run_llm), 51 episodes
  eval/run_eval.py           4-way ablation -> eval/results.json
  tests/                     68 tests
frontend/                    Next.js 14 + TypeScript + Tailwind (Stage, Evidence, Ledger, decision inspector)
```

## How it decides
1. **Task contract**: the task is stored server-side; only destinations the user *named* (plus an org allowlist) are allowed.
2. **Taint tracking**: after reading untrusted content, a send to an unnamed destination is blocked and the agent is contained (kill switch). Untainted off-contract sends are held for a person.
3. **Scope rules**: protected tables however written, SQL injection syntax, path escapes, lookalike domains.
4. **Honeytoken**: a planted fake customer record; seeing it in an outbound call blocks the call even to an allowed destination.
5. **Ingress filter**: normaliser + regex + trained classifier quarantine obvious injections before the agent reads them.
6. **Human approval**: destructive calls and untainted off-contract sends are HELD until an authenticated operator approves or denies.
7. **Keyed ledger**: HMAC-SHA256 chain; editing a row, or recomputing plain hashes, fails verification.
Every decision returns a score, rationale, triggered **controls** and **evidence**; the Stage tab's inspector shows them with the request JSON.

## Evidence (`python -m eval.run_eval`): 27 attacks, 24 everyday tasks
| Setup | Attacks that succeeded | Tasks finished | Median check |
|---|---|---|---|
| No guard | 27 / 27 | 24 / 24 | n/a |
| Text filter only | 12 / 27 | 24 / 24 | <0.1 ms |
| Flow control only | 2 / 27 | 24 / 24 | <0.1 ms |
| **AgentGuard (both)** | **2 / 27** | **24 / 24** | **<0.1 ms** |

**Read this honestly.** We wrote the episodes, the attack wording and the classifier's training data; the attacker is a deterministic *simulation* of a gullible agent. The results show the layers behave as designed, not how a real model fares. The 2 attacks that still succeed are labelled *known limit*: they send data to a person the user *did* name. `agents.run_llm` and `judge.py` call the Anthropic API and are **not exercised in tests** (they need network and a key). Next: run the harness on AgentDojo and a real model.

## Protect your own agent (3 calls)
```python
import requests; B = "http://localhost:8000/api/sessions"
sid = requests.post(B, json={"task": "Triage my inbox"}).json()["session"]
r = requests.post(f"{B}/{sid}/call", json={"tool": "send_email", "args": {"to": "x@evil.io", "body": "..."}}).json()
if r["decision"] != "ALLOW": ...   # HOLD = ask a human, BLOCK = refuse; r["rationale"], r["controls"], r["evidence"] explain why
```

## 3-minute demo script
1. 0:00 "Polite compliance request": no trigger words, the unguarded lane leaks.
2. 0:25 Bottom lane: pipe turns ink after the read, the send is stopped, agent contained. Open the inspector: score, controls, evidence. "The guard never needed the email's wording."
3. 1:00 "Homoglyph" / "Base64": the text filter catches them. "Spanish": it doesn't; flow control does.
4. 1:30 "Temp cleanup": Held, click Approve. "Inbox triage 1": no false alarm.
5. 1:55 Evidence tab: the table, then the known-limit rows, said out loud.
6. 2:25 Ledger: Tamper, Verify, broken record.
7. 2:45 The 3-call integration snippet.
