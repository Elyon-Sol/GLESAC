"""OPT-IN live-node smoke test - NOT part of the hermetic suite.

Runs ONLY when GLESAC_LIVE_NODES=1 (so CI and the default `pytest` stay offline/deterministic).
Points at the four public nodes by default; override any URL via the GLESAC_*_URL env vars.
Read-only: it GETs each node for reachability and pulls the signed record for freshness. Requires
`requests` (pip install -e .[live]).

    GLESAC_LIVE_NODES=1 python -m pytest tests/test_live_nodes.py -v
"""
import json
import os
import tempfile

import pytest

from glesac import status
from glesac.config import Config

pytestmark = pytest.mark.skipif(
    os.environ.get("GLESAC_LIVE_NODES") != "1",
    reason="opt-in: set GLESAC_LIVE_NODES=1 (and optionally GLESAC_*_URL) to run live checks",
)

DEFAULTS = {
    "GLESAC_GATE_URL": "https://gate.elyon-sol.io:8443/governed-call",   # 405 on GET = up
    "GLESAC_TARGET_URL": "https://target.elyon-sol.io:9443/received",
    "GLESAC_AUTHZ_URL": "https://authz.elyon-sol.io:9243/healthz",
    "GLESAC_PUB_URL": "https://pub.elyon-sol.io:9143/published_hashes_signed.json",
}


def _cfg():
    for k, v in DEFAULTS.items():
        os.environ.setdefault(k, v)
    return Config.from_env()


def test_live_nodes_reachable():
    nodes = status.probe_nodes(_cfg())
    bad = {n: i for n, i in nodes.items() if i.get("state") not in ("reachable", "unconfigured")}
    assert not bad, f"nodes not reachable: {bad}"
    assert any(i.get("state") == "reachable" for i in nodes.values()), nodes


def test_live_signed_record_fresh():
    requests = pytest.importorskip("requests")
    url = os.environ.get("GLESAC_PUB_URL", DEFAULTS["GLESAC_PUB_URL"])
    r = requests.get(url, timeout=8, verify=True)
    r.raise_for_status()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(r.json(), f)
        path = f.name
    fr = status.record_freshness(path)
    assert fr["present"], fr
    assert fr["fresh"] is True, f"live signed record is STALE: {fr}"
    assert fr["publisher_key_id"], fr
