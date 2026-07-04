"""Read the Elyon-Sol JSONL logs as OPA-style 'decision logs' (READ-ONLY).

issuance log: one envelope per line. approval log: {"type": "approval_request"|"grant_consumed",
"decision_sha256", "approval_request_id", ...}. GLESAC never writes these; it reads/joins them
for the action-trace and reconciliation views.
"""
from __future__ import annotations
import json
from typing import Dict, Iterator, List


def read_jsonl(path: str) -> Iterator[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def trace_by_decision(issuance_path: str, approval_path: str, decision_sha256: str) -> List[Dict]:
    """Assemble one action's timeline joined on decision_sha256 (TODO P1: + target /received)."""
    events: List[Dict] = []
    for rec in read_jsonl(issuance_path):
        if rec.get("decision_sha256") == decision_sha256:
            events.append({"stage": "issued", **rec})
    for rec in read_jsonl(approval_path):
        if rec.get("decision_sha256") == decision_sha256:
            events.append({"stage": rec.get("type", "approval"), **rec})
    return events
