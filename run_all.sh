#!/usr/bin/env bash
# Reproduce the headline results of the CHIMERA-QRC Phase-2 submission.
# Usage:  bash run_all.sh     (after: pip install -r requirements.txt)
set -e
cd "$(dirname "$0")"

echo "================================================================"
echo " 1/4  Headline benchmark - calm window (Table 1 + Model Conf. Set)"
echo "================================================================"
python3 vol_fair_benchmark.py

echo "================================================================"
echo " 2/4  Crisis benchmark - regime-transition tracking (GFC in test)"
echo "      Expect: CHIMERA-3scale MZ R^2 = 0.591 > HAR 0.559 >> ESN 0.09/0.23"
echo "================================================================"
python3 vol_crisis_benchmark.py

echo "================================================================"
echo " 3/4  Kernel geometry - distinctness + nonlinearity beyond HAR"
echo "      Expect: g(ESN->CHIMERA) ~62 vs ~4 control; residual-KTA ~13x ESN"
echo "================================================================"
python3 kernel_analysis.py

echo "================================================================"
echo " 4/4  Quantum-SDK reproduction - explicit PennyLane circuit"
echo "      Expect: engine vs PennyLane max|d| ~5e-16; ~380-gate Trotter circuit"
echo "================================================================"
python3 sdk_demo.py

echo "================================================================"
echo " (optional) current-window Garman-Klass validation (2022-2026 SPY)"
echo "================================================================"
python3 gk_validation.py || echo "(skipped/optional)"

echo
echo "All headline experiments complete."
