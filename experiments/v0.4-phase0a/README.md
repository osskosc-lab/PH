# PH v0.4 Phase 0A

This directory contains the fresh Pilot for **Targeted-Access Identifiability Falsification**.

The prior PH v0.3.3-r1 result is frozen: under A0 (Fast/Slow external inputs and V/O observations), the single shared-boundary node identity is structurally `NON_IDENTIFIABLE` against the exact oracle duplicated-state construction. This experiment does not revisit that result and does not tune the old classifier.

Phase 0A adds A1 local interventions `J_V` and `J_O`. The local actuator is calibrated in a model-independent plant before the PH evaluation split. `M11-C` is the primary adversary: two latent states are allowed bounded local leakage, shared innovation, and cross-output coupling. The bounds and capacity ladder are fixed in `config.json` and are not selected from evaluation outcomes. `M11-U` is an unrestricted oracle canary; its equivalence to `M0` is expected and cannot support global identifiability.

Run the Pilot with:

```bash
python run_phase0a.py --outdir artifacts/pilot
```

Exit code `0` means all Pilot gates allow a freeze; exit code `2` means the preregistered Pilot STOP. Neither outcome authorizes Confirmatory data unless every mandatory gate passes and a separate frozen Confirmatory protocol is created.

The generated machine-readable artifacts separate calibration, quality, model-fit, gate, capacity-ladder, replay, and claim-firewall evidence. A Pilot STOP is not evidence that PH does or does not exist in nature.
