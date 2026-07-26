# Phase-3 submission checklist — EIGENNEXUS / Track A

Final steps before uploading to Aqora. Deadline: **Sunday, July 26, 2026, 11:59 PM Eastern**.

## 1. Build the submission zip
```bash
bash package_submission.sh      # git archive HEAD → EIGENNEXUS_Challenge_Phase3.zip
```
This packages exactly the committed tree at `HEAD` — no uncommitted or untracked files. Rebuild it
after every commit so the zip never lags the repo.

## 2. Manual steps before upload
1. **Cover page: filled and merged (2026-07-26), kept OUT of the repository by design.** The
   official template was filled in place (never recreated, per its own rule) and merged as page 1
   of `EIGENNEXUS__Phase3_Version1.pdf` — named exactly per the template's file-name requirement
   `TeamName__Phase3_VersionX.pdf`; 7 pages = 1 cover + 5 body + references. Compliance re-checked
   against the template's own disclaimer: max 5 pages excluding cover and references ✓, 11-pt
   Times New Roman ✓, single spacing ✓. **The filled cover and the merged PDF contain personal
   contact data, so both are `.gitignore`d and live only locally — they are uploaded directly to
   Aqora, never committed.** The public repo/zip carry the identical paper as `PHASE3_PAPER.pdf`
   (no cover, no personal data).
   **Still open on the cover: the Aqora Username cell (left blank — fill before upload).**
2. **Confirm the repository is public**, so the qBraid "Launch" button and the committed evidence
   (job IDs, counts, `results/`) are reachable by judges.
3. Upload `EIGENNEXUS__Phase3_Version1.pdf` (and `EIGENNEXUS_Challenge_Phase3.zip` where the
   portal accepts supplementary material) via Aqora.

## 3. Reproduce / verify (for reference)
- `python3 cli.py verify` — one-command **offline** integrity audit (24 engine tests + QASM
  self-test + credit reconciliation + bootstrap CIs + noise fingerprint; ~2-5 min depending on core
  count, no network/credits).
- **End-to-end judge simulation, last run 2026-07-26 16:10 UTC:** the zip was extracted into a
  clean directory and both judge paths executed **with no API key in the environment** —
  `cli.py verify` passed 5/5, and `build_paper.py` regenerated the PDF at the committed pagination
  (5 body pages, References on page 6). What judges receive is what was tested.
- `docs/verify_replay.html` — a self-contained browser replay of that verify run, for a reviewer
  who prefers not to run it, plus the paper's core findings.
- `python3 reproduce.py --quick` — fast full reproduction (~10 min for the headline story).
