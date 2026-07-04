"""Consume-by-invocation layer: locate and run the installed Elyon-Sol CLIs.

GLESAC does NOT import Elyon-Sol internals - it runs the real tools, so "no re-implementation"
(the canon rule) holds by construction. This is the ONLY bridge to the core.
"""
from __future__ import annotations
import os, shutil, subprocess, sys
from typing import List, Optional

CORE_HOME_ENV = "ELYON_SOL_HOME"


def _resolve(tool: str) -> List[str]:
    """Return the argv prefix to run `tool` (envelope_inspector | approver_cli).

    Prefers a PATH executable; else ELYON_SOL_HOME/IMPLEMENTATION/<tool>.py via the interpreter.
    """
    exe = shutil.which(tool)
    if exe:
        return [exe]
    home = os.environ.get(CORE_HOME_ENV)
    if home:
        script = os.path.join(home, "IMPLEMENTATION", f"{tool}.py")
        if os.path.exists(script):
            env_py = [sys.executable]
            return env_py + [script]
    raise FileNotFoundError(
        f"cannot find '{tool}'. Install Elyon-Sol on PATH or set {CORE_HOME_ENV}."
    )


def run(tool: str, args: List[str], *, input_text: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a core CLI, returning the CompletedProcess (READ-only tools; approver_cli for HIL).

    PYTHONPATH is set to ELYON_SOL_HOME so the script-form invocation resolves core imports.
    """
    argv = _resolve(tool) + list(args)
    env = dict(os.environ)
    home = os.environ.get(CORE_HOME_ENV)
    if home:
        env["PYTHONPATH"] = home + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(argv, input=input_text, capture_output=True, text=True, env=env)


# NOTE (SoD, [FIX H5]): GLESAC never signs a grant itself. `glesac approve` MUST invoke
# approver_cli, which reads the approver's PRIVATE key from local custody. There is deliberately
# no signing primitive in this package. A revert-catcher test asserts this (tests/).

# P3: the ONLY runbooks GLESAC may trigger - a fixed whitelist of existing Elyon-Sol repo
# scripts, resolved under ELYON_SOL_HOME. GLESAC adds no admin capability of its own.
RUNBOOKS = {
    "rotate-publisher-key": os.path.join("deploy", "rotate_publisher_key.py"),
    "renew-certs": os.path.join("deploy", "tls", "gen_certs.py"),
}


def run_runbook(name: str, args: List[str]) -> subprocess.CompletedProcess:
    """Run a whitelisted Elyon-Sol runbook (mutation - caller must confirm + audit).

    Requires ELYON_SOL_HOME (runbooks are repo files, not PATH tools). Output passes through
    to the operator; GLESAC never captures secrets - the rotation runbook writes the new key
    to a 0600 file and prints only PUBLIC material by design.
    """
    if name not in RUNBOOKS:
        raise ValueError(f"unknown runbook '{name}' (allowed: {', '.join(sorted(RUNBOOKS))})")
    home = os.environ.get(CORE_HOME_ENV)
    if not home:
        raise FileNotFoundError(f"set {CORE_HOME_ENV} to locate the runbooks.")
    script = os.path.join(home, RUNBOOKS[name])
    if not os.path.exists(script):
        raise FileNotFoundError(f"runbook not found: {script}")
    env = dict(os.environ)
    env["PYTHONPATH"] = home + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, script] + list(args),
                          capture_output=True, text=True, env=env)
