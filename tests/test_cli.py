"""Scaffold + P1 CLI tests. The load-bearing one is the SoD no-signing revert-catcher."""
import glob
import os
import subprocess
import sys

import glesac


def test_version_string():
    assert glesac.__version__


def test_cli_parses_help():
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "glesac" in r.stdout


def test_status_and_logs_subcommands_run():
    env = dict(os.environ)
    fix = os.path.join(os.path.dirname(__file__), "fixtures")
    env["GLESAC_ISSUANCE_LOG"] = os.path.join(fix, "issuance.jsonl")
    env["GLESAC_READINESS"] = os.path.join(fix, "readiness.json")
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "status", "--no-probe"],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0 and "DEFAULT_SECURE" in r.stdout
    r2 = subprocess.run([sys.executable, "-m", "glesac.cli", "logs", "--which", "issued", "--tail", "1"],
                        capture_output=True, text=True, env=env)
    assert r2.returncode == 0 and "bbb222" in r2.stdout


def test_no_signing_primitive_anywhere_in_package_REVERT_CATCHER():
    """SoD ([FIX H5]): the ENTIRE glesac package must contain NO grant-signing capability.

    GLESAC may only DELEGATE to approver_cli (the approver's key stays in local custody). If any
    signing primitive is ever added to this package, this test goes RED - blocking a
    self-approval backdoor at CI time. Scans every module in the package.
    """
    pkg_dir = os.path.dirname(glesac.__file__)
    banned = ("sign_grant", "make_grant", "build_grant", "Ed25519PrivateKey", "SigningKey",
              "private_key", "from_private_bytes", "hazmat", "nacl.signing")
    scan = glob.glob(os.path.join(pkg_dir, "*.py")) + \
        glob.glob(os.path.join(pkg_dir, "webui", "*"))    # P2: the web UI is scanned too
    assert any(p.endswith("approvals.py") for p in scan)   # the P2 module IS in scope
    for path in scan:
        src = open(path, encoding="utf-8").read()
        for b in banned:
            assert b not in src, f"{os.path.basename(path)} must not contain '{b}' - GLESAC never signs (SoD)."
    # and no crypto-capable import anywhere in the package: signing is structurally impossible
    for path in glob.glob(os.path.join(pkg_dir, "*.py")):
        src = open(path, encoding="utf-8").read()
        assert "import cryptography" not in src and "from cryptography" not in src
