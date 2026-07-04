"""Gargoyles Ledge (GLESAC) - the Elyon-Sol Administrative Console.

An OPA-style, LOCAL-FIRST operator toolkit. Security invariants (docs/SECURITY.md):
localhost-only; mutations run locally via the installed Elyon-Sol tools; the approver key
never leaves the operator machine; GLESAC can never mint an approval grant on its own.
"""
__version__ = "0.0.1"
