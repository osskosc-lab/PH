# PH v0.3.1-r2

Paired-Stress & Representation-Repair Confirmatory Experiment.

This is a synthetic robustness / identifiability audit of the PH v0.3.1 detector. It does **not** establish PH in nature.

The two intended decisive endpoints are:

1. `R_kernel < 1.00` after Pilot-only deterministic RBF kernel selection.
2. `P_correct(compound, s=0.50) >= 0.80` with completely paired nuisance RNG and unchanged threshold.

Technical repairs relative to v0.3.1 are limited to raw-margin saturation auditing, generate-first/transform-later paired RNG, and the preregistered kernel-selection procedure.

## Official R2 status

The Pilot Kernel Gate did **not** validate the representation method. The selected kernel was `h=0.50, alpha=0.01`; point-estimate `R_kernel=0.98655`, but paired-bootstrap shared recovery was `0.675 < 0.80`. Critical-negative kernel FP remained controlled at `0.04333 <= 0.05`.

Per preregistration, Confirmatory was **not started**, no Confirmatory freeze was created, and the official decision is `INCONCLUSIVE (PILOT_STOP)`.