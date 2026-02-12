# Reproducible Release Checklist

## Source Control
- [ ] Release branch is up to date with `main`.
- [ ] Working tree is clean.
- [ ] Version/release metadata updated.

## Environment
- [ ] Python version pinned to 3.10.x.
- [ ] Fresh virtual environment created.
- [ ] `pip install -r requirements-dev.txt` completed successfully.

## Quality Gates
- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `mypy`
- [ ] `pytest -q tests`

## Build
- [ ] `tools/build.bat` completed without errors.
- [ ] Artifact present at `tools/Built/MLHD2-Launcher.exe`.

## Verification
- [ ] App launches and saves settings.
- [ ] Mission append path works with local Excel.
- [ ] Discord webhook send path works (or expected failure is actionable).
- [ ] Dynamic icon cache initializes and updates.
- [ ] Log rotation works (`app.log`, backups when size limit reached).

## Diagnostics and Supportability
- [ ] Optional diagnostics dump can be generated for issue reports.
- [ ] No secrets/webhook tokens in logs, code, or docs.

## Release Artifacts
- [ ] Checksums generated and recorded.
- [ ] Release notes include key changes + known issues.
- [ ] Distribution package uploaded.
