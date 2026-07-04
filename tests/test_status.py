import os
from glesac import status
from glesac.config import Config

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def test_readiness_summary_tolerant():
    r = status.readiness_summary(os.path.join(FIX, "readiness.json"))
    assert r["DEFAULT_SECURE"] is True and r["REAL_TRANSPORT"] is False
    # missing file -> all None, no crash
    assert status.readiness_summary("/no/such")["ROOT_RECOVERY"] is None


def test_record_freshness_fresh_and_stale():
    fresh = status.record_freshness(os.path.join(FIX, "signed_record_fresh.json"))
    assert fresh["present"] and fresh["fresh"] is True and fresh["publisher_key_id"] == "pub-2026-06-18"
    stale = status.record_freshness(os.path.join(FIX, "signed_record_stale.json"))
    assert stale["present"] and stale["fresh"] is False
    assert status.record_freshness(None)["present"] is False


def test_gather_offline_no_probe():
    cfg = Config(readiness=os.path.join(FIX, "readiness.json"),
                 signed_record=os.path.join(FIX, "signed_record_fresh.json"))
    s = status.gather(cfg, probe=False)
    assert s["readiness"]["DEFAULT_SECURE"] is True
    assert s["signed_record"]["fresh"] is True
    assert s["nodes"] == {}


def test_probe_unconfigured_nodes_do_not_crash():
    nodes = status.probe_nodes(Config())   # no URLs
    assert all(v["state"] == "unconfigured" for v in nodes.values())
