"""Canonicalise text the way an LLM would read it: undo homoglyphs, zero-width splits, URL-encoding and base64."""
import base64, re, unicodedata, urllib.parse
_ZW = {ord(c): None for c in "\u200b\u200c\u200d\u2060\ufeff\u00ad\u202e"}
_PAIRS = {"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ѕ": "s", "ј": "j", "ο": "o", "ι": "i", "ν": "v"}
_HOMO = {ord(k): v for k, v in _PAIRS.items()}
_B64 = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")

def clean(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).translate(_ZW).translate(_HOMO)
    return re.sub(r"\s+", " ", t)

def views(text: str) -> list[str]:
    base = clean(text); out = [base]
    un = urllib.parse.unquote(base)
    if un != base: out.append(un)
    for m in _B64.findall(base):
        try: d = base64.b64decode(m + "=" * (-len(m) % 4)).decode("utf-8")
        except Exception: continue
        if d and sum(c.isprintable() for c in d) / len(d) > .95: out.append(clean(d))
    return out
