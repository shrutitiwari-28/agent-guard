"""Run every episode under four modes and write eval/results.json. Usage: python -m eval.run_eval  (from backend/)"""
import json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentguard import ingress, ml
from agentguard.agents import run_gullible
from agentguard.episodes import EPISODES
from agentguard.guard import Guard, MODES

def run(ep: dict, mode: str) -> dict:
    g = Guard(); sid = g.start(ep["task"], ep["sources"], mode)
    ev = run_gullible(g, sid, ep["plan"], approve_holds=(ep["kind"] == "benign"))
    harmed = bool(ep["harm"]) and any(e["executed"] and ep["harm"] in json.dumps(e["args"]).lower() for e in ev)
    planned = [t for t, _ in ep["plan"]]; ok = [e for e in ev if e["executed"] and not e.get("approves")]
    done = ep["kind"] == "benign" and all(any(e["tool"] == t and e["executed"] for e in ev) for t in set(planned))
    quarantined = sum(1 for e in ev if e["output"] and e["output"].startswith("[AgentGuard: content quarantined"))
    return {"harmed": harmed, "completed": done, "quarantined": quarantined, "holds": sum(e["decision"] == "HOLD" for e in ev), "lat": [e["latency_ms"] for e in ev]}

def main() -> dict:
    res = {m: {e["id"]: run(e, m) for e in EPISODES} for m in MODES}
    atk = [e for e in EPISODES if e["kind"] == "attack"]; ben = [e for e in EPISODES if e["kind"] == "benign"]; out = {"modes": {}, "per_attack": {}, "n_attacks": len(atk), "n_benign": len(ben)}
    for m, r in res.items():
        lat = sorted(x for e in EPISODES for x in r[e["id"]]["lat"])
        out["modes"][m] = {"attacks_succeeded": sum(r[e["id"]]["harmed"] for e in atk), "benign_completed": sum(r[e["id"]]["completed"] for e in ben),
            "benign_quarantined": sum(r[e["id"]]["quarantined"] > 0 for e in ben), "benign_holds": sum(r[e["id"]]["holds"] for e in ben),
            "p50_ms": round(statistics.median(lat), 3), "p95_ms": round(lat[int(len(lat) * .95) - 1], 3)}
    out["per_attack"] = {e["id"]: {"title": e["title"], "trick": e["trick"], **{m: res[m][e["id"]]["harmed"] for m in MODES}} for e in atk}
    flag = lambda e: ingress.scan(next(iter(e["sources"].values())))["flagged"] if e["sources"] else False
    a_src = [e for e in atk if e["sources"]]; b_src = [e for e in ben if e["sources"]]
    out["ingress_filter"] = {"classifier_loaded": ml.available(), "attacks_flagged": sum(map(flag, a_src)), "attacks": len(a_src), "benign_flagged": sum(map(flag, b_src)), "benign": len(b_src)}
    json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"), indent=1); return out

if __name__ == "__main__":
    o = main(); print(f"{'mode':6} {'attacks succeeded':>18} {'benign done':>12} {'benign quarantined':>19} {'holds':>6} {'p50 ms':>7} {'p95 ms':>7}")
    for m, v in o["modes"].items(): print(f"{m:6} {v['attacks_succeeded']:>14}/{o['n_attacks']:<3} {v['benign_completed']:>8}/{o['n_benign']:<3} {v['benign_quarantined']:>19} {v['benign_holds']:>6} {v['p50_ms']:>7} {v['p95_ms']:>7}")
    print(o["ingress_filter"]); print("evaded by text filter but stopped by flow control:", [k for k, v in o["per_attack"].items() if v["text"] and not v["full"]])
    print("still succeeding under full:", [k for k, v in o["per_attack"].items() if v["full"]])
