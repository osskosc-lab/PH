# PH v0.3.2-r1 Pilot Result

## Experiment
Representation-Stability Falsification

GitHub Actions run: `31565040981`
Commit: `c3fdc214674dfc92ee43235cff3af648c40502f0`
Artifact: `ph-v0.3.2-r1-pilot-g0-g7`
Artifact ID: `9129144063`
Artifact SHA256: `08914a11edd9ec56d6a21e480024d8374eeb12d1d7e8e3d9f899aa8c5f7c9075`

## Decision

`PILOT_PASS_FREEZE_ALLOWED`

All preregistered Pilot gates G0-G7 passed.

| Gate | Result |
|---|---|
| G0 Seed integrity | PASS |
| G1 Dynamic range | PASS |
| G2 Excitation | PASS |
| G3 Positive recoverability | PASS |
| G4 Maximal adversarial specificity | PASS |
| G5 Basic negative specificity | PASS |
| G6 Representation consensus | PASS |
| G7 Numerical integrity | PASS |

## Primary representation

Primary: `balanced_logistic`

Calibration threshold: `1.1891711734690704`
Calibration feasible: `true`
Calibration TPR(M0): `1.00`
Calibration worst FP across M10/M1/M2/M5: `0.10`

Fresh held-out Gate evaluation:

- TPR(M0): `1.00`
- FP(M10): `0.05`
- FP(M1): `0.05`
- FP(M2): `0.05`
- FP(M5): `0.05`

Thus G3, G4 and G5 all passed at the preregistered boundary.

## Representation consensus

Four of five preregistered representation families independently satisfied the G6 rule:

1. balanced_logistic
2. balanced_ridge
3. shrinkage_diagonal_lda
4. balanced_nonparametric_distance

Evaluation highlights:

| Representation | TPR M0 | FP M10 | G6-family criterion |
|---|---:|---:|---|
| balanced logistic | 1.00 | 0.05 | PASS |
| balanced ridge | 1.00 | 0.05 | PASS |
| shrinkage diagonal LDA | 1.00 | 0.05 | PASS |
| balanced centroid | 0.85 | 0.10 | FAIL |
| balanced nonparametric distance | 0.85 | 0.00 | PASS |

The failure is therefore no longer a representation-wide shared-vs-mimic collapse. One geometry family remains fragile, but four distinct families reproduce the required direction.

## M10 challenge

The maximal adversary was not weakened.

The exact v0.3.2 36-point M10 grid and objective were imported from the parent implementation. Fresh r1 tuning selected:

- av = `0.88`
- ao = `0.87`
- gv = `0.36`
- go = `0.34`
- tuning objective = `0.1921466813636111`

This is the same parameter corner selected in v0.3.2, under fresh RNG.

## Fresh-data separation

N = 80 per mode/condition, with disjoint roles:

- 0-19: M10 tuning only
- 20-39: representation fitting only
- 40-59: threshold calibration only
- 60-79: Gate evaluation only

Legacy v0.3.2 seed overlap: `0`
Paired RNG integrity: PASS

## Dynamic feature structure

The original 35 raw dynamic features were unchanged.

r1 formed a 70-dimensional intervention-set fingerprint by computing, feature by feature, the mean and standard deviation across:

- multisine
- impulse
- PRBS

No new raw measurement was added.

Raw evaluation dynamic range:

- minimum feature std: `0.0934634509670313`
- maximum feature std: `8.769277946858445`

Minimum intervention variance: `0.08207958984375`

## Interpretation

The v0.3.2 failure is consistent with a representation/training pathology rather than immediate dynamic non-identifiability. Correcting class imbalance, aggregating the same raw dynamic information at the intervention-set level, and separating fit/calibration/evaluation restored positive recoverability while retaining maximal-adversary specificity on fresh held-out Pilot data.

This does **not** establish PH identifiability. It establishes that a frozen Confirmatory test is now scientifically permissible.

The next valid step is to freeze the r1 configuration, selected M10 parameters, standardization, calibrated thresholds and code hashes, then run a fresh Confirmatory experiment without any further estimator selection.
