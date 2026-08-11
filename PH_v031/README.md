# PH v0.3.1 - Imperfect-Intervention Identifiability Stress Test

This package audits the robustness and operating envelope of the PH v0.3 synthetic causal-specificity detector under imperfect boundary intervention. It does **not** test whether PH exists in nature.

## Key idea

The ideal `do(B=0)` of v0.3 is replaced by a dose intervention `do_lambda(B)` with leakage, clamp noise, measurement error, latent common drivers, weak V-O coupling, colored noise, and parameter drift. Training clamp strengths are `{0, 0.4, 0.8, 1.0}` and intervention-OOD strengths are `{0.2, 0.6}` plus extreme OOD `0.9`.

The critical identification set is restricted to `shared_boundary`, `separate_boundary`, `common_driver`, and `adversarial_clamp_mimic` so trivial negative controls cannot inflate `P_correct`.

## Run

```bash
pip install -r PH_v031/requirements.txt
cd PH_v031
python run_pilot.py
python freeze_confirmatory.py
python run_confirmatory.py
python generate_report.py
```

The Confirmatory run must only be executed after `freeze.json` exists.
