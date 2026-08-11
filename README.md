# PH - Personal Horizon falsification experiments

## Experiment series

### PH v0.2 - implementation feasibility
Result: **INCONCLUSIVE**. The discrete viability horizon plateaued and the history endpoint saturated. Frozen v0.2 artifacts remain under `results/phase1/`.

### PH v0.2.1 - causal-specificity falsification
Result: **PH_SIGNATURE_SUPPORTED** for the synthetic detector-validation task.

The v0.2.1 evaluator requires selective `do(B)` effects on viability and observability, reciprocal posterior-opacity / JS-distinguishability movement, paired interventional coupling, sham specificity, history dependence with bootstrap CI, and rejection of six adversarial controls.

In Confirmatory N=256, only M0 coupled-PH passed every primary Gate. M2 common-driver was deliberately adversarial: it produced strong observational correlation (`Gamma_obs=0.901`) but failed under boundary intervention. Correlation alone therefore does not count as PH-positive.

This result does **not** demonstrate PH in nature. It validates the causal-specificity falsifier on the frozen synthetic suite.

## Layout
```text
PH/
├─ src/
│  ├─ ph_v02_full.py
│  └─ ph_v021_causal_specificity.py
├─ protocol/
│  ├─ PH_v0.2_Phase1_protocol.md
│  └─ PH_v0.2.1_Causal_Specificity_protocol.md
├─ results/
│  ├─ phase1/
│  └─ v0.2.1/
│     ├─ config.freeze.json
│     ├─ decision.json
│     ├─ all_stage_summary.csv
│     └─ confirmatory_summary.csv
├─ reports/
│  └─ PH_v0.2.1_Causal_Specificity_Report_2026-08-12.md
└─ tests/
   └─ test_v021.py
```

## Reproduce
```bash
pip install -r requirements.txt
python src/ph_v021_causal_specificity.py --outdir results/v0.2.1-reproduction
```

Source SHA256: `f25081f222ad991a2d18df59547c16f322e403d551d8c3bbbc080d331517c89a`  
Freeze SHA256: `cb14c9abcae421ec25341b8e251a3f3a76002f0bb64e515a6f0a09f283cd17af`

## Next
PH v0.3: remove explicit `B -> (V,O)` construction and test whether the two horizons emerge together in an adaptive agent / artificial-life system.
