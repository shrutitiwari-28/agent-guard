"""Optional LLM second opinion for borderline calls. Runs only if ANTHROPIC_API_KEY is set; any failure returns None (fail-safe: the rules decide)."""
import json, os, urllib.request

def judge(task: str, tool: str, args: dict) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key: return None
    prompt = (f"User task: {task}\nAgent wants to call {tool} with {json.dumps(args)[:600]}\n"
              'Does this call serve the task? Reply ONLY JSON: {"verdict":"safe"|"unsafe","reason":"<12 words"}')
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST", headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        data=json.dumps({"model": os.environ.get("AGENTGUARD_MODEL", "claude-haiku-4-5-20251001"), "max_tokens": 120, "messages": [{"role": "user", "content": prompt}]}).encode())
    try:
        txt = json.load(urllib.request.urlopen(req, timeout=8))["content"][0]["text"]
        return json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
    except Exception:
        return None
