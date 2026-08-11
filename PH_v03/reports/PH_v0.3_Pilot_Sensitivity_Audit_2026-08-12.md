# PH v0.3 Pilot Sensitivity Audit

## Pre-freeze diagnostic

The first implementation trial used `margin_scale = 2.5`. Under the shared-boundary positive control the continuous margin entered a noticeably nonlinear tanh regime and the capacity-matched OOD comparison failed (`R_OOD ~= 1.061`, positive-seed rate 0.00). This was treated as an estimability/local-linearity failure, not a PH falsification.

## Pre-registered-style correction before confirmatory freeze

- `margin_scale`: 2.5 -> 8.0
- Gate thresholds: unchanged
- model capacity: unchanged (5 coefficients/output in both reduced-form competitors; 10 total each)
- stimulus frequencies, T=8192, burn-in=1024: unchanged
- Confirmatory seeds: untouched
- nonparametric impulse-tail window was tightened from 35..150 to 10..60 lags because the later tail was noise-floor biased; this affects only the representation-independent diagnostic, not K_V/K_O or R_OOD.

## Official Pilot result (N=30 seeds/mode)

- shared_boundary positive-seed rate: 1.00
- separate_boundary: 0.00
- common_driver: 0.00
- null: 0.00
- adversarial_mimic: 0.00
- shared mean R_OOD: 0.9397; 95% bootstrap UCB: 0.9406
- shared K_V/K_O lower bounds both >0.99

The analysis was then frozen before any confirmatory seed was executed.
