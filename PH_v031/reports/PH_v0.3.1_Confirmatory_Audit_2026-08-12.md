# PH v0.3.1 - Imperfect-Intervention Identifiability Stress Test

## Official decision

**INCONCLUSIVE**

This is a robustness / identifiability audit of the PH v0.3 synthetic detector. It is not evidence for PH in biology, AI, consciousness, or nature.

## Why the result is not ROBUST or FRAGILE

The preregistered core causal detector performed strongly, but Gate 10 (representation independence) did not reproduce the shared-boundary conclusion in the intervention-kernel estimator. Because v0.3.1 explicitly requires parametric, nonparametric, and intervention-kernel agreement, this disagreement forces `INCONCLUSIVE`. A second technical gate, saturation, also failed for the intentionally wide adversarial clamp mimic and is preserved because it was frozen before confirmatory execution.

If Gate 10 were ignored post hoc, the operating-envelope result would be `FRAGILE`, not `ROBUST`, because compound stress at the preregistered `s=0.50` point produced `P_correct=0.75 < 0.80`. That sensitivity interpretation is not the official decision.

## Confirmatory core - shared boundary

- beta_V: 1.0035, 95% bootstrap CI [0.9920, 1.0150]
- beta_O: 1.0070, 95% bootstrap CI [0.9973, 1.0171]
- K_V(0.8): 0.7808
- K_O(0.8): 0.7764
- R_lambda_OOD: 0.9069, UCB95 0.9294
- R_CIC: 0.4951, UCB95 0.5575
- intervention-kernel ratio: 1.0082
- shared bootstrap positive recovery: 1.000

The first two primary causal endpoints therefore survived imperfect intervention at baseline, but the third representation did not.

## Negative-control specificity

Bootstrap false-positive probabilities in the confirmatory core:

- separate_boundary: 0.000
- common_driver: 0.000
- adversarial_clamp_mimic: 0.000

This is an important positive result. `R_lambda_OOD` alone remains non-specific: common-driver and other negatives can also achieve low OOD ratios. The detector rejects them because dose response and shared intervention consistency do not jointly survive.

## Operating envelope

Estimated normalized breakpoints s* at P_correct >= 0.80:

- clamp leakage: 0.50
- clamp noise: 1.00
- measurement error: 1.00
- latent driver: 0.75
- weak V-O coupling: 1.00
- colored noise: 1.00 (descriptive only; curve was non-monotone)
- parameter drift: 1.00
- compound leakage + latent driver + colored noise: 0.25

At the preregistered compound checkpoint s=0.50, `P_correct=0.75`. The shared condition itself becomes negative there because K_V(0.8) and K_O(0.8) fall to approximately 0.44, below the substantive 0.50 gate.

## Technical audit

### G2 saturation

The frozen saturation rule was applied directly to K(lambda). The only core failure was `adversarial_clamp_mimic`, where deliberately wide independent target efficacy caused 6-7% of values to exceed the frozen absolute bound. In retrospect, saturation is more naturally a raw-margin gate inherited from v0.3, not a clamp-response bound. This was discovered after freeze, so the rule was not changed.

### G10 representation independence

For the shared positive control:

- parametric: pass
- nonparametric monotonic response: pass
- intervention kernel: fail (`ratio=1.0082`)

By preregistration, model disagreement is `INCONCLUSIVE`, not a permission to select the favorable representations.

### Robustness-curve pairing

The same seed identities were used across stress strengths, but the frozen implementation changed nuisance-noise codes by stress level. This can produce non-monotone `P_correct(s)` values (notably colored noise). The current s* values are therefore descriptive operating-envelope estimates, not final monotone breakpoints.

## Scientific interpretation

v0.3.1 supports a narrower statement than v0.3: the core shared-boundary detector remains causally specific under imperfect intervention at low stress, and the new clamp-dose mimic can be rejected. However, the detector is not yet representation-independent and its compound-stress operating envelope is narrow. A clean v0.3.1-r2 should repair the Gate-2 semantics, pair nuisance noise across stress strength, preregister a stable intervention-kernel estimator, and use completely fresh holdout seeds.

**v0.4 Nonlinear Boundary Generation should not be treated as confirmatorily authorized by this run.**
