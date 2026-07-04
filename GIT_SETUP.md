# Pushing GLESAC to its own repo

1. Create an empty repo on GitHub named `glesac` (public, since the license is Apache-2.0).
2. From this unzipped folder:

```
git init
git add .
git commit -m "GLESAC scaffold: OPA-style local-first operator toolkit (CLI + localhost console); Apache-2.0; consumes Elyon-Sol by invocation"
git branch -M main
git remote add origin https://github.com/Elyon-Sol/glesac.git   # adjust owner if needed
git push -u origin main
```

3. Dev install + smoke test:
```
pip install -e .
glesac --help
ELYON_SOL_HOME=/path/to/Elyon-Sol glesac inspect token.json
```

Build order is in docs/DESIGN.md (P0 spec -> P1 read-only console -> P2 HIL -> P3 admin).
Keep docs/SECURITY.md as design law. This is a SEPARATE repo from Elyon-Sol by decision.
