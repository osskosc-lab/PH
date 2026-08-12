# PH v0.3.2-r1 — Representation-Stability Falsification

## Rationale
PH v0.3.2 Pilot stopped at G3 (positive recoverability) and G6 (representation consensus) while G4 maximal-adversary specificity passed. The observed pattern was compatible with a representation/training failure: class-imbalanced discriminative models under-recovered M0, while unbalanced geometric models recovered M0 but over-accepted M10.

This revision tests that explanation without weakening the adversary.

## Locked carry-over from v0.3.2
- M0–M10 dynamics: unchanged, imported directly from `../v0.3.2/ph_v032_pilot.py`.
- M10 grid: unchanged 36-point grid.
- Raw dynamic features: unchanged 35-feature extractor.
- Train interventions: multisine, impulse, PRBS.
- Pilot-only M10 optimization: unchanged objective structure.
- Confirmatory data: forbidden.

## Fresh Pilot namespace
All stochastic tokens use `PH-v0.3.2-r1` and therefore do not reuse v0.3.2 Pilot RNG streams.

## N and split
N = 80 per mode/condition.

- indices 0–19: M10 tuning only
- indices 20–39: representation fitting only
- indices 40–59: threshold calibration only
- indices 60–79: Gate evaluation only

No sample may cross these roles.

## Representation change
Each seed is represented at the intervention-set level by the same 35 raw features extracted separately from multisine, impulse and PRBS, then summarized by feature-wise mean and standard deviation across the three train interventions. This produces a fixed 70-dimensional representation without introducing new raw measurements.

Five preregistered families are evaluated:
1. class-balanced logistic
2. class-balanced ridge
3. shrinkage diagonal LDA
4. balanced centroid geometry
5. class-balanced nonparametric distance

All discriminative fits use equal total weight for M0 and the pooled negative class.

## Threshold calibration
Each representation returns a continuous M0 score. Thresholds are selected only on indices 40–59. Candidate thresholds are deterministic midpoints of calibration scores. The selected threshold minimizes the worst false-positive rate across M10, M1, M2 and M5 subject to TPR(M0) >= 0.80. Ties prefer lower worst-FP, then higher TPR, then the higher threshold. If no candidate satisfies TPR >= 0.80, calibration is marked infeasible and the threshold maximizing TPR - worst-FP is used diagnostically; it cannot rescue a failed Gate.

## Gates
G0 Seed integrity: unique audit seeds, paired RNG integrity, fresh namespace.

G1 Dynamic range: all raw primary features finite and non-degenerate on fresh evaluation M0/M10 data.

G2 Excitation: all train interventions have variance > 0.02 on evaluation indices.

G3 Positive recoverability: primary balanced-logistic TPR(M0) >= 0.80 on indices 60–79.

G4 Maximal adversarial specificity: primary FP(M10) <= 0.05.

G5 Basic negative specificity: primary FP(M1), FP(M2), FP(M5) <= 0.05 each.

G6 Representation consensus: at least 3 of 5 preregistered families independently satisfy TPR(M0) >= 0.80, FP(M10) <= 0.05, and TPR(M0) > FP(M10) on evaluation data.

G7 Numerical integrity: finite matrices/scores/thresholds, 35 raw features, 70 aggregate features, no degenerate fitted representation.

## Stop rule
Any Gate failure => STOP. No Confirmatory run is allowed. Any estimator, threshold rule, feature aggregation, adversarial range or gate change requires `v0.3.2-r2` and another fresh Pilot.

## Interpretation
- PASS does not establish PH; it only establishes a stable detector candidate for later frozen Confirmatory testing.
- Failure of G3/G6 again, despite class balancing and isolated threshold calibration, strengthens the case that the current dynamic fingerprint is not stably identifiable rather than merely suffering from the original classifier implementation.
