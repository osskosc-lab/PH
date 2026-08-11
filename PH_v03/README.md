# PH v0.3 - Frequency-Domain Causal-Specificity Falsification

PH v0.3 tests whether viability-side and observability-side temporal responses require a **shared boundary dynamic**, rather than merely showing correlation, coherence, common forcing, or spectrum similarity.

## Frozen confirmatory result

**Decision: `PH-v0.3 SUPPORTED` for the synthetic falsifier-validation task.**

This does **not** establish that PH exists in nature, biology, humans, AI, or consciousness. The positive control explicitly contains a shared boundary. The result says that the frozen detector can distinguish that known structure from the registered alternatives.

### Confirmatory (N=200 seeds/mode)

- shared `K_V = 0.99653` (95% LCB `0.99643`)
- shared `K_O = 0.99167` (95% LCB `0.99145`)
- shared `R_OOD = 0.94018` (95% UCB `0.94056`)
- core negative-control PH-like rate = `0.00`
- adversarial spectral mimic PH-like rate = `0.00`
- parametric `rho_B = 0.96496`; nonparametric V/O = `0.97335 / 0.97066`
- residual low-frequency coherence = `0.6693`

A key finding is that `separate_boundary` also obtains `R_OOD = 0.94841`, so OOD advantage alone is not causally specific. Boundary Clamp rejects it (`K_V ~ K_O ~ 0`). Likewise, the adversarial mimic has coherence `0.99607 / 0.99561` while the clamp remains ineffective.

## Layout

```text
PH_v03/
├── preregistration/
├── ph/
├── spectral/
├── models/
├── audit/
├── results/
├── reports/
├── tests/
├── run_pilot.py
├── run_confirmatory.py
└── generate_report.py
```

## Reproduce

```bash
pip install -r PH_v03/requirements.txt
cd PH_v03
pytest -q tests/test_v03.py
python run_pilot.py
# freeze before confirmatory; the committed freeze.json is the official snapshot
python run_confirmatory.py
```

The official confirmatory used per-mode chunks only because of the execution window. The external runner preserved every mode's original frozen index/noise-code mapping; frozen source, config, thresholds, stimuli, seeds, and formulas were unchanged. See `results/execution_manifest.json` and the report.
