# Phase-3 submission checklist — EIGENNEXUS / Track A

Deadline: **Sunday, July 26, 2026, 11:59 PM EST.** Upload one zip named
`EIGENNEXUS_Challenge_Phase3.zip` to Aqora.

## Headline (honest, pre-registered)
A pre-registered, adversarially-controlled study: against strong fair baselines (HAR-X,
recurrent ESN, RFF; HAC-DM; 8 seeds; two windows; Holm) the quantum reservoir shows **no
significant forecasting advantage at simulable scale → H0 refuted**. What survives:
competitiveness, lower seed variance than the ESN, measured kernel distinctness, and
full-rank entanglement (classical-simulation hardness). We report this honestly.

## What's in the package
- `PHASE3_PAPER.pdf` — the **5-page** write-up (11-pt Times New Roman, single-spaced).
  Editable source: `PHASE3_PAPER.md` → `build_paper.py` regenerates the PDF/`.docx`.
- `README.md` — first thing judges read: Launch-on-qBraid button, one-command
  reproduction, honest results, repo layout, data provenance, hardware plan.
- Source code: all `*.py` modules + `cli.py`/`qbraid_skill.yaml`/`SKILL.md` (the
  agent-executable qBraid Skill), `requirements.txt`, `run_all.sh`.
- `data/` (public, bundled), `figures/`, `results/*_findings.md` (all headline numbers).

## Reproduce (two paths)
```bash
pip install -r requirements.txt
python3 cli.py reproduce --quick   # FAST judge verification (~10-15 min); verdicts match the full run
python3 cli.py reproduce           # FULL reproduction (~1 hr; dense n=12 + sparse n=16 are the slow parts)
```
The committed `results/*_findings.md` hold every full-run number; the fast path regenerates
the same verdicts at reduced seeds/sizes.

## Compliance (GIC Phase-3 rules)
- [x] Write-up = 5 pages (excl. references), 11-pt Times New Roman, single-spaced.
- [x] README.md with setup + step-by-step qBraid run instructions + Launch button.
- [x] Source code executable on qBraid without external configuration (pure-NumPy core).
- [x] Common MNIST benchmark implemented (mandatory cross-team task).
- [x] qBraid Skill (agent-executable reproducibility package).
- [x] Classical baselines (HAR, HAR-X, GARCH/GJR, AR(3), persistence, ESN [recurrent], RFF, LSTM).
- [x] Concrete numbers (qubit counts, 2-qubit gate depth, observables, shots, wall-clock, metrics).
- [x] Honest limitations stated prominently (no advantage at simulable scale; H0 refuted; MNIST ≈ ESN).

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
