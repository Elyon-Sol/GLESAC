"""`glesac status` - node health + record freshness + readiness. READ-ONLY.

Works offline from pulled files (readiness summary, signed record). Live node probes are
best-effort. GLESAC never writes to a node here.
"""
from __future__ import annotations
import datetime as _dt
import json
from typing import Any, Dict, Optional

from .config import Config

PREDICATES = ("DEFAULT_SECURE", "END_TO_END_NO_SHORTCUT", "ROOT_RECOVERY", "REAL_TRANSPORT")
_CAP_FLAGS = ("built", "wired_to_default", "exercised_e2e", "transported")


def _now(now: Optional[_dt.datetime]) -> _dt.datetime:
    return now or _dt.datetime.now(_dt.timezone.utc)


def _parse_dt(s: Any) -> Optional[_dt.datetime]:
    if not isinstance(s, str):
        return None
    try:
        d = _dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def _load_json(path: Optional[str]) -> Optional[Dict]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def readiness_summary(path: Optional[str]) -> Dict[str, Optional[bool]]:
    """Tolerant read of the readiness predicates -> {predicate: green|None}.

    Handles the real Elyon-Sol readiness.json (`deployment_predicates` with a `green` flag) and
    the simpler `predicates`/top-level shapes.
    """
    data = _load_json(path) or {}
    preds = data.get("deployment_predicates") or data.get("predicates") or data
    out: Dict[str, Optional[bool]] = {}
    for name in PREDICATES:
        entry = preds.get(name) if isinstance(preds, dict) else None
        if isinstance(entry, dict):
            v = entry.get("green")
            out[name] = v if v is not None else entry.get("value")
        elif isinstance(entry, bool):
            out[name] = entry
        else:
            out[name] = None
    return out


def capabilities_summary(path: Optional[str]) -> Dict[str, Dict[str, Optional[bool]]]:
    """The Elyon-Sol readiness `capabilities` block -> {name: {flag: value}}. {} if absent."""
    caps = (_load_json(path) or {}).get("capabilities")
    if not isinstance(caps, dict):
        return {}
    out: Dict[str, Dict[str, Optional[bool]]] = {}
    for name, cap in caps.items():
        if isinstance(cap, dict):
            out[name] = {f: (cap.get(f) or {}).get("value") if isinstance(cap.get(f), dict)
                         else None for f in _CAP_FLAGS}
    return out


def record_freshness(path: Optional[str], now: Optional[_dt.datetime] = None,
                     clock_skew_seconds: int = 0) -> Dict[str, Any]:
    """Read the signed published record and compute freshness (now < not_after + skew)."""
    rec = _load_json(path)
    if not rec:
        return {"present": False}
    na = _parse_dt(rec.get("not_after"))
    fresh = None
    if na is not None:
        fresh = _now(now) < na + _dt.timedelta(seconds=clock_skew_seconds)
    return {
        "present": True,
        "publisher_key_id": rec.get("publisher_key_id"),
        "serial": rec.get("serial"),
        "issued_at": rec.get("issued_at"),
        "not_after": rec.get("not_after"),
        "fresh": fresh,
    }


def probe_nodes(config: Config, timeout: float = 3.0) -> Dict[str, Dict[str, Any]]:
    """Best-effort reachability of configured node URLs. No probe if requests is unavailable."""
    out: Dict[str, Dict[str, Any]] = {}
    try:
        import requests
    except Exception:
        requests = None
    for name, url in config.nodes.items():
        if not url:
            out[name] = {"url": None, "state": "unconfigured"}
            continue
        if requests is None:
            out[name] = {"url": url, "state": "unknown (install requests to probe)"}
            continue
        try:
            r = requests.get(url, timeout=timeout, verify=True)
            out[name] = {"url": url, "state": "reachable", "http": r.status_code}
        except Exception as e:
            out[name] = {"url": url, "state": "unreachable", "error": type(e).__name__}
    return out


def gather(config: Config, now: Optional[_dt.datetime] = None, probe: bool = True) -> Dict[str, Any]:
    return {
        "readiness": readiness_summary(config.readiness),
        "capabilities": capabilities_summary(config.readiness),
        "signed_record": record_freshness(config.signed_record, now, config.clock_skew_seconds),
        "nodes": probe_nodes(config) if probe else {},
    }
