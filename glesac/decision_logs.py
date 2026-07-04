"""Read the Elyon-Sol JSONL logs as OPA-style 'decision logs' (READ-ONLY).

issuance log: one envelope per line. approval log: {"type": "approval_request"|"grant_consumed",
"decision_sha256", "approval_request_id", ...}. GLESAC never writes these; it reads/joins them
for the action-trace and reconciliation views.
"""
from __future__ import annotations
import json
from typing import Dict, Iterator, List, Optional

STAGE_ORDER = {"issued": 0, "approval_request": 1, "grant_consumed": 2, "executed": 3}


def read_jsonl(path: str) -> Iterator[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def records(path: Optional[str]) -> List[Dict]:
    """All records, tolerant of a missing/None path (returns [])."""
    if not path:
        return []
    try:
        return list(read_jsonl(path))
    except OSError:
        return []


def tail(path: Optional[str], n: int = 50, decision_sha256: Optional[str] = None) -> List[Dict]:
    """Last n records, optionally filtered to one decision_sha256."""
    recs = records(path)
    if decision_sha256:
        recs = [r for r in recs if r.get("decision_sha256") == decision_sha256]
    return recs[-n:] if n and n > 0 else recs


def _decision_of(env: Dict) -> Optional[str]:
    return env.get("decision_sha256") or (env.get("decision") or {}).get("decision_sha256")


def trace_by_decision(issuance_path: Optional[str], approval_path: Optional[str],
                     decision_sha256: str, executed_count: Optional[int] = None) -> List[Dict]:
    """One action's timeline joined on decision_sha256, ordered issued->approval->grant->executed.

    executed_count (from target /received) is surrounding context, not a per-decision join - the
    reference target counts actions but does not key them by decision.
    """
    events: List[Dict] = []
    for rec in records(issuance_path):
        if _decision_of(rec) == decision_sha256:
            events.append({"stage": "issued", **rec})
    for rec in records(approval_path):
        if rec.get("decision_sha256") == decision_sha256:
            events.append({"stage": rec.get("type", "approval"), **rec})
    events.sort(key=lambda e: STAGE_ORDER.get(e.get("stage", ""), 9))
    if executed_count is not None:
        events.append({"stage": "executed_count", "count": executed_count,
                       "note": "target /received total (not per-decision)"})
    return events
