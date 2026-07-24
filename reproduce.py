#!/usr/bin/env python3
"""
reproduce.py - one-command reproduction entry point for judges.

Thin, discoverable wrapper over the Skill driver (`cli.py`). Everything runs
offline on the committed data (no qBraid account, credits, or network needed);
the QPU campaigns are committed evidence verified via platform job records, not
re-executed here (see results/CREDIT_BUDGET.md, results/qpu_hardware_findings.md).

Usage:
  python3 reproduce.py                 # FULL reproduction (~1-2 h)   == cli.py reproduce
  python3 reproduce.py --quick         # fast full pass (reduced seeds/sizes)
  python3 reproduce.py headline --quick   # ~10-min judge verification (recommended first run)
  python3 reproduce.py <anything>      # passthrough to cli.py (e.g. `list`, `run mnist`)

Authoritative full-run numbers live in results/*_findings.md regardless of --quick.
"""
import os
import sys
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "cli.py")

args = sys.argv[1:]
# default target is the full `reproduce` group; a leading flag (e.g. --quick)
# still means "reproduce", so inject the group before it.
if not args or args[0].startswith("-"):
    args = ["reproduce"] + args

print(f"[reproduce.py] -> {os.path.basename(sys.executable)} cli.py {' '.join(args)}\n", flush=True)
sys.exit(subprocess.run([sys.executable, CLI] + args).returncode)
