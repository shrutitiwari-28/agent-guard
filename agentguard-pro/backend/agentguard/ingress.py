"""Scan untrusted content as it enters the agent: normalisation + regex + trained classifier."""
from . import ml
from .detectors import scan_injection

def scan(text: str) -> dict:
    rx, why = scan_injection(text); p = ml.prob_injection(text)
    return {"regex": rx, "ml": round(p, 3), "flagged": rx >= 40 or p >= .5, "why": why}
