# Phase-3 submission checklist — EIGENNEXUS / Track A

Deadline: **Sunday, July 26, 2026, 11:59 PM EST.** Upload one zip named
`EIGENNEXUS_Challenge_Phase3.zip` to Aqora.

## What's in the package
- `PHASE3_PAPER.pdf` — the 4-page write-up (11-pt Times New Roman, single-spaced).
  Editable source: `PHASE3_PAPER.md` → `build_paper.py` regenerates the PDF/`.docx`.
- `README.md` — first thing judges read: Launch-on-qBraid button, one-command
  reproduction, honest headline results, repo layout, data provenance, hardware plan.
- Source code: all `*.py` modules + `cli.py`/`qbraid_skill.yaml`/`SKILL.md` (the
  agent-executable qBraid Skill), `requirements.txt`, `run_all.sh`.
- `data/` (public, bundled), `figures/`, `results/*_findings.md` (headline numbers).

## Reproduce everything
```bash
pip install -r requirements.txt
python3 cli.py reproduce      # or: python3 cli.py run headline
```

## Compliance (GIC Phase-3 rules)
- [x] Write-up ≤ 5 pages (currently 4), 11-pt Times New Roman, single-spaced.
- [x] README.md with setup + step-by-step qBraid run instructions + Launch button.
- [x] Source code executable on qBraid without external configuration (pure-NumPy core).
- [x] Common MNIST benchmark implemented (mandatory cross-team task).
- [x] qBraid Skill (agent-executable reproducibility package).
- [x] Classical baselines reported (HAR, GARCH/GJR, AR(3), persistence, ESN, LSTM).
- [x] Concrete numbers (qubit count, depth ~380 gates, shots, wall-clock, metrics).
- [x] Honest limitations stated (H0 refuted-as-pre-registered; MNIST ≈ ESN).

## ⚠️ Two manual steps before you submit (only you can do these)
1. **Prepend the official GIC_2026 cover page** (`GIC_2026 Cover Page.docx` from Aqora)
   as **page 1** of the final PDF. Per the rules it may not be recreated/modified, so
   it is intentionally not in this package. Easiest path: open `PHASE3_PAPER.docx`,
   paste the cover page as page 1, export to PDF, replace `PHASE3_PAPER.pdf`, re-zip.
2. **qBraid real-QPU validation (optional, rubric bonus):** once the team qBraid
   credits are live, run the gate-Trotter circuit (`sdk_demo.py`) on IonQ/IQM/IBM and
   add the measured numbers to §5/§6. The submission is complete and reproducible
   without it (simulator-first), but a real hardware result strengthens criterion 6.

## Build the zip
```bash
bash package_submission.sh      # -> EIGENNEXUS_Challenge_Phase3.zip (committed files only)
```
