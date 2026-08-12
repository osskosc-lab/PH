# PH v0.3.2-r1 Confirmatory Preregistration

## Status

This document defines the frozen Confirmatory stage authorized by the PH v0.3.2-r1 Pilot result `PILOT_PASS_FREEZE_ALLOWED`.

No estimator selection is permitted after this point.

## Primary question

Can the frozen r1 dynamic-intervention fingerprint distinguish the shared-boundary model M0 from the maximal dynamic mimic M10 on fresh Confirmatory seeds, including unseen interventions?

## Frozen inheritance

The Confirmatory stage inherits without modification:

- M0-M10 dynamics from `experiments/v0.3.2/ph_v032_pilot.py`
- the original 35 raw dynamic features
- the 70D feature-wise mean/std aggregation from v0.3.2-r1
- the exact 36-point M10 search family and the Pilot-selected M10 parameters
- all five preregistered representation families
- Pilot-fitted standardization
- Pilot-calibrated thresholds

The frozen values are recorded in `freeze.json`.

## Fresh Confirmatory sampling

`N = 256` per model.

Fresh namespace:

`PH-v0.3.2-r1|confirmatory|...`

The Confirmatory audit must show zero overlap with Pilot audit seeds.

### Core intervention set

- multisine
- impulse
- PRBS

### OOD intervention set

- chirp
- unseen_frequencies
- unseen_amplitudes
- burst
- reversed_sequence

For each model/seed and each intervention set, the same 35 raw features are computed and aggregated feature-wise into mean + standard deviation, producing the same frozen 70D representation.

## Primary representation

`balanced_logistic`

Frozen threshold:

`1.1891711734690704`

No threshold calibration is allowed on Confirmatory data.

## Confirmatory gates

All confidence bounds are Wilson 95% intervals.

- C0 Freeze integrity: parent source blobs, Pilot artifact-derived objects, and Confirmatory protocol hash match the freeze.
- C1 Core positive identification: `LCB95(TPR_M0) > 0.80`.
- C2 Core maximal-adversary specificity: `UCB95(FP_M10) < 0.05`.
- C3 Core basic-negative specificity: M1, M2, M5 each satisfy `UCB95(FP) < 0.05`.
- C4 OOD positive identification: `LCB95(TPR_M0) > 0.80`.
- C5 OOD maximal-adversary specificity: `UCB95(FP_M10) < 0.05`.
- C6 OOD basic-negative specificity: M1, M2, M5 each satisfy `UCB95(FP) < 0.05`.
- C7 Representation independence: at least three preregistered representation families independently satisfy the M0/M10 core and OOD confidence-bound rules.
- C8 Numerical/seed integrity: finite outputs, unique Confirmatory audit seeds, paired RNG integrity, and zero Pilot overlap.

## Decision map

### IDENTIFIABLE

All C0-C8 pass.

### FRAGILE_IDENTIFIABLE

Frozen core identification survives but OOD or representation-independence is insufficient.

### NON_IDENTIFIABLE

With valid freeze/numerics, shared and mimic fail to separate in a representation-consistent way.

### INCONCLUSIVE

Freeze integrity, numerical integrity, or another technical condition prevents the scientific hypothesis from being evaluated.

## Diagnostics

`DIS_core` and `DIS_OOD` are reported as non-gating diagnostics:

distance between M0 and M10 standardized mean fingerprints divided by the within-M0 RMS radius.

They may not be used to change the Confirmatory decision.

## Absolute prohibitions

After Confirmatory data are generated, the following are prohibited for this version:

- M10 re-optimization
- threshold recalibration
- representation selection or removal
- feature addition/removal
- standardization refit
- seed replacement
- changing confidence thresholds

Any methodological change requires a new revision and fresh Pilot.
