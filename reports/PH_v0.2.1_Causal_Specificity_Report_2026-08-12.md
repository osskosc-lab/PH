# PH v0.2.1 Causal-Specificity Falsification - Result

Date: 2026-08-12 JST  
Version: `PH-v0.2.1-causal-specificity-1.1`  
Final decision: **PH_SIGNATURE_SUPPORTED**

## Executive finding
In the independent confirmatory holdout (N=256), **M0 coupled-PH passed all primary Gates**, while M1-M6 each failed at least one required Gate. Gate 8 and Gate 9 therefore passed. This validates the causal-specificity detector on the synthetic control suite only; it is not evidence that PH exists in nature.

## M0 confirmatory
- Dynamic-range fraction: `1.000`
- Boundary repair: `0.9910`
- Viability-horizon relative drop: `0.3147` (95% CI `0.3096` to `0.3200`)
- Opacity effect: `0.03470` (95% CI `0.03465` to `0.03475`)
- JS distinguishability effect: `0.1119` (95% CI `0.1067` to `0.1162`)
- Gamma_int: `0.9102` (95% CI `0.9016` to `0.9185`)
- Sham specificity ratio: `8.260`
- Lambda_H: `1.9287` (95% CI `1.6274` to `2.2457`)
- History total effect: `0.1812`; direct effect after B matching: `0.0000`

## Critical adversary: common driver
M2 common-driver produced a strong baseline observational correlation `Gamma_obs=0.9005` while having no causal B -> V/O route. Under `do(B)` it failed the PH profile and was rejected. This is the main advance over v0.2: **co-movement alone no longer counts as a PH signature**.

## Confirmatory matrix
| Mode | Complete | Gamma_obs | Gamma_int | Lambda_H | Decision |
|---|---:|---:|---:|---:|---|
| M0_coupled_PH | True | 0.916 | 0.910 | 1.929 | PH_SIGNATURE_POSITIVE |
| M1_split_boundary | False | 0.168 | NA | 1.929 | NEGATIVE_CONTROL_REJECTED |
| M2_common_driver | False | 0.901 | NA | 0.996 | NEGATIVE_CONTROL_REJECTED |
| M3_viability_only | False | NA | NA | 1.929 | NEGATIVE_CONTROL_REJECTED |
| M4_observability_only | False | 0.867 | -0.008 | 0.999 | NEGATIVE_CONTROL_REJECTED |
| M5_sensor_artifact | False | -0.068 | NA | 0.999 | NEGATIVE_CONTROL_REJECTED |
| M6_null | False | NA | NA | 0.999 | NEGATIVE_CONTROL_REJECTED |

## Interpretation
The maximum justified claim is: **the v0.2.1 falsifier can distinguish a deliberately shared-boundary synthetic mechanism from split-boundary, common-driver, one-sided, sensor-artifact, and null alternatives under the frozen test suite.**

It does not establish PH in biology, humans, AI, consciousness, or nature. PH v0.3 should remove the explicit generator-level shared-boundary construction and test for spontaneous co-emergence in an adaptive agent or artificial-life system.

## Reproducibility
- Source SHA256: `f25081f222ad991a2d18df59547c16f322e403d551d8c3bbbc080d331517c89a`
- Freeze SHA256: `cb14c9abcae421ec25341b8e251a3f3a76002f0bb64e515a6f0a09f283cd17af`
- Final: `PH_SIGNATURE_SUPPORTED`
