@echo off
rem GLESAC live console - PUBLIC nodes + local-demo decision logs. Binds 127.0.0.1 only.
rem Untracked convenience launcher; safe to delete.
set "ELYON_SOL_HOME=C:\Users\assist\Elyon-Sol"
set "R=%ELYON_SOL_HOME%\deploy\governance\local_demo\runtime"
set "GLESAC_ISSUANCE_LOG=%R%\issuance.log"
set "GLESAC_APPROVAL_LOG=%R%\approval.log"
set "GLESAC_READINESS=%ELYON_SOL_HOME%\EVIDENCE\readiness.json"

rem -- the four public nodes (read-only probes from the status card) --
set "GLESAC_GATE_URL=https://gate.elyon-sol.io:8443/governed-call"
set "GLESAC_TARGET_URL=https://target.elyon-sol.io:9443/received"
set "GLESAC_AUTHZ_URL=https://authz.elyon-sol.io:9243/healthz"
set "GLESAC_PUB_URL=https://pub.elyon-sol.io:9143/published_hashes_signed.json"
rem live HIL detail if the gate ever enables its read-endpoints (default off -> log fallback)
set "GLESAC_GATE_PENDING_URL=https://gate.elyon-sol.io:8443/pending"

rem -- pull the live signed record so the freshness card evaluates it (5-min TTL) --
curl -s --max-time 8 "%GLESAC_PUB_URL%" -o "%TEMP%\elyon_signed_record.json" && set "GLESAC_SIGNED_RECORD=%TEMP%\elyon_signed_record.json"

echo GLESAC live console (public nodes) -^> http://127.0.0.1:8181  (Ctrl+C to stop)
start "" http://127.0.0.1:8181
python -m glesac.cli run --port 8181
