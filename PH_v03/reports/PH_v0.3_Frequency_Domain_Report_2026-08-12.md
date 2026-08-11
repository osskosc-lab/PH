# PH v0.3 Frequency-Domain Causal-Specificity Falsification Report

## Decision

**`PH-v0.3 SUPPORTED` - synthetic detector validation only.**

The experiment validates a falsifier that requires frequency-domain structure, causal boundary knockout, OOD generalization, downstream specificity, negative controls, adversarial spectral mimic rejection, and representation-independent recovery. It does not show that PH exists in natural systems.

## Pilot and freeze

The first pre-freeze implementation used `margin_scale=2.5` and entered a nonlinear tanh regime. The shared positive control then failed the OOD comparison (`R_OOD ~ 1.061`). Before any confirmatory seed was used, `margin_scale` was changed to `8.0` to restore the intended local-linear regime. Thresholds, model capacity, T, burn-in, and stimulus frequencies were unchanged. The official pilot was rerun and then frozen.

Freeze SHA256: `5ba55a72e9148c7c03d0e292db2cd8b78cd9788ac4c3f85a38e082a3f84f0874`.

## Confirmatory result (N=200 seeds/mode)

| Mode | PH-like rate | K_V | K_O | R_OOD | mean coherence V/O | representation |
|---|---:|---:|---:|---:|---:|---|
| shared_boundary | 1.00 | 0.99653 | 0.99167 | 0.94018 | 0.99594 / 0.99536 | PASS |
| separate_boundary | 0.00 | 0.00000 | 0.00000 | 0.94841 | 0.99603 / 0.99560 | FAIL |
| common_driver | 0.00 | 0.00000 | 0.00000 | 1.00494 | 0.98441 / 0.96878 | FAIL |
| viability_only | 0.00 | 0.99664 | 0.00000 | 0.99736 | 0.99627 / 0.00550 | FAIL |
| observability_only | 0.00 | 0.00000 | 0.99168 | 1.00867 | 0.00949 / 0.99560 | FAIL |
| null | 0.00 | 0.00000 | 0.00000 | 1.00002 | 0.00320 / 0.00346 | FAIL |
| adversarial_mimic | 0.00 | 0.00000 | 0.00000 | 0.96101 | 0.99607 / 0.99561 | FAIL |

### Primary endpoint 1 - Dual Boundary Knockout

- `K_V = 0.99653`, 95% CI `[0.99643, 0.99663]`
- `K_O = 0.99167`, 95% CI `[0.99145, 0.99191]`

Both lower bounds exceed the pre-registered 0.30 threshold.

### Primary endpoint 2 - OOD model generalization

- `R_OOD = 0.94018`, 95% CI `[0.93979, 0.94056]`
- pre-registered requirement: UCB < 0.95

The shared and separate reduced-form predictors are capacity matched: 5 coefficients/output, 10 total per model. Training uses multisine, impulse, and PRBS. OOD testing uses unseen frequencies, chirp, and unseen amplitude.

A crucial specificity finding is that `separate_boundary` also yields `R_OOD=0.94841`. Therefore OOD advantage by itself is not sufficient evidence for a common boundary. The Boundary Clamp is what rejects the false causal interpretation.

## Spectral evidence is auxiliary

The adversarial mimic was explicitly designed so that deterministic input-output spectra are almost indistinguishable from the shared-boundary positive control. It achieves coherence `0.99607 / 0.99561`, yet the shared boundary clamp has essentially zero effect. The common-driver control also has high coherence `0.98441 / 0.96878` without boundary knockout.

Thus `high coherence != shared causal boundary` and `spectrum similarity != same cause`.

## Representation-independent check

For the shared positive control:

- parametric `rho_B = 0.96496`, `tau_B = 28.03` steps
- nonparametric impulse-tail `rho_B(V)=0.97335`
- nonparametric impulse-tail `rho_B(O)=0.97066`
- residual low-frequency coherence after removing input-driven components = `0.6693`

The parametric and nonparametric estimates agree within the frozen tolerance.

## Gate decision

All frozen Gates pass: Freeze, dynamic range, saturation, spectral excitation/leakage, pilot positive recovery, negative-control rate, boundary clamp, OOD generalization, adversarial mimic rejection, representation independence, and downstream specificity.

## Execution audit

The full 7-mode confirmatory exceeded the available single-process execution window. The official confirmatory was therefore executed per mode. The external chunk runner preserved each mode's **original frozen mode index**, including the preregistered mode-specific noise-code mapping (`1000+mi*100` through `1500+mi*100`). Frozen source, config, thresholds, stimuli, seed ranges, and formulas were unchanged. Results were recombined with the frozen gate/decision functions.

## Scope and next step

This is still a positive-control detector validation: the shared boundary exists by construction. The next step is PH v0.4 Nonlinear Boundary Generation, with `B_(t+1)=G(B_t,X_t,H_t)` and the same clamp/OOD/adversarial audit retained.

Legacy `D*` and `Omega` were not redefined with incompatible frequency-domain proxies. They remain conceptual secondary endpoints and should be reintroduced only by explicitly reconnecting the older perturbation/reconstruction subsystem.
