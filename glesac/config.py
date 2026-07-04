"""GLESAC configuration - where the operator points the toolkit at its data.

Read-only sources: the JSONL decision logs (pulled to the operator or mounted read-only), the
readiness summary, the signed published record, and optional node URLs for live probes. No
secrets live here. Everything is overridable by env var or CLI flag.
"""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

ENV = {
    "issuance_log": "GLESAC_ISSUANCE_LOG",
    "approval_log": "GLESAC_APPROVAL_LOG",
    "readiness": "GLESAC_READINESS",
    "signed_record": "GLESAC_SIGNED_RECORD",
    "gate_url": "GLESAC_GATE_URL",
    "gate_pending_url": "GLESAC_GATE_PENDING_URL",
    "target_url": "GLESAC_TARGET_URL",
    "authz_url": "GLESAC_AUTHZ_URL",
    "pub_url": "GLESAC_PUB_URL",
}


@dataclass
class Config:
    issuance_log: Optional[str] = None
    approval_log: Optional[str] = None
    readiness: Optional[str] = None
    signed_record: Optional[str] = None
    gate_url: Optional[str] = None
    gate_pending_url: Optional[str] = None
    target_url: Optional[str] = None
    authz_url: Optional[str] = None
    pub_url: Optional[str] = None
    clock_skew_seconds: int = 0
    nodes: Dict[str, Optional[str]] = field(default_factory=dict)

    @classmethod
    def from_env(cls, **overrides) -> "Config":
        vals = {k: os.environ.get(env) for k, env in ENV.items()}
        skew = int(os.environ.get("GLESAC_CLOCK_SKEW_SECONDS", "0") or 0)
        vals["clock_skew_seconds"] = skew
        vals.update({k: v for k, v in overrides.items() if v is not None})
        c = cls(**{k: vals.get(k) for k in
                   ("issuance_log", "approval_log", "readiness", "signed_record",
                    "gate_url", "gate_pending_url", "target_url", "authz_url", "pub_url")},
                clock_skew_seconds=vals["clock_skew_seconds"])
        c.nodes = {
            "gate": c.gate_url, "target": c.target_url,
            "authz": c.authz_url, "publisher": c.pub_url,
        }
        return c
