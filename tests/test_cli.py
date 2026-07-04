"""Scaffold tests. The load-bearing one is the SoD revert-catcher (P2)."""
import subprocess, sys, glesac
from glesac import cli, invoke


def test_version_string():
    assert glesac.__version__


def test_cli_parses_help():
    r = subprocess.run([sys.executable, "-m", "glesac.cli", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "glesac" in r.stdout


def test_no_signing_primitive_in_package():
    """SoD revert-catcher ([FIX H5]): GLESAC must contain NO grant-signing capability.

    It may only DELEGATE to approver_cli (local key custody). If a future change adds a signing
    primitive to this package, this test must fail. Guards against a self-approval backdoor.
    """
    import glesac.invoke as inv, glesac.cli as c, glesac.server as s
    banned = ("sign_grant", "make_grant", "Ed25519PrivateKey", "SigningKey", "private_key")
    for mod in (inv, c, s):
        src = open(mod.__file__, encoding="utf-8").read()
        for b in banned:
            assert b not in src, f"{mod.__name__} must not contain '{b}' - GLESAC never signs (SoD)."
