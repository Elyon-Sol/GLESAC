import os
from glesac import decision_logs as dl

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
ISS = os.path.join(FIX, "issuance.jsonl")
APP = os.path.join(FIX, "approvals.jsonl")


def test_records_and_tail():
    assert len(dl.records(ISS)) == 2
    assert dl.tail(ISS, 1)[0]["decision_sha256"] == "bbb222"
    assert dl.records(None) == []          # tolerant of missing path
    assert dl.tail("/no/such/file", 5) == []


def test_tail_filter_by_decision():
    recs = dl.tail(APP, 50, decision_sha256="aaa111")
    assert len(recs) == 2 and all(r["decision_sha256"] == "aaa111" for r in recs)


def test_trace_orders_the_timeline():
    tl = dl.trace_by_decision(ISS, APP, "aaa111")
    stages = [e["stage"] for e in tl]
    assert stages == ["issued", "approval_request", "grant_consumed"]
    # a decision with no approval leg shows only issuance
    assert [e["stage"] for e in dl.trace_by_decision(ISS, APP, "bbb222")] == ["issued"]


def test_trace_executed_count_is_context_not_a_join():
    tl = dl.trace_by_decision(ISS, APP, "aaa111", executed_count=7)
    assert tl[-1]["stage"] == "executed_count" and tl[-1]["count"] == 7
