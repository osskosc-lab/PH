# PH v0.3.2-r1 Python Structure

```text
experiments/
├─ v0.3.2/
│  └─ ph_v032_pilot.py
│     ├─ intervention()
│     ├─ simulate()                 # M0-M10 dynamics
│     ├─ features()                 # frozen 35 raw dynamic features
│     ├─ raw_row()
│     ├─ M10_GRID                   # frozen 36-point adversarial grid
│     └─ optimize_m10()
│
└─ v0.3.2-r1/
   ├─ preregistration.md
   ├─ config.json
   ├─ ph_v032_r1_pilot.py
   │  ├─ import v0.3.2 core directly
   │  ├─ set fresh RNG namespace PH-v0.3.2-r1
   │  ├─ aggregate_row()            # 35 raw -> mean/std across 3 interventions -> 70D
   │  ├─ build_aggregate_dataset()
   │  ├─ balanced_weights()
   │  ├─ BalancedLogistic
   │  ├─ BalancedRidge
   │  ├─ ShrinkageDiagonalLDA
   │  ├─ BalancedCentroid
   │  ├─ BalancedNonparametricDistance
   │  ├─ calibrate_threshold()      # calibration split only
   │  ├─ seed_integrity()
   │  ├─ raw_dynamic_range()
   │  └─ run_pilot()               # fresh held-out G0-G7
   └─ artifacts/pilot/
      ├─ pilot_result.json
      ├─ m10_frozen_from_fresh_tuning.json
      ├─ standardization.json
      ├─ calibrated_thresholds.json
      ├─ representation_confusion.csv
      └─ python_structure.json
```

## Data separation

```text
0-19   -> M10 tuning only
20-39  -> representation fit only
40-59  -> threshold calibration only
60-79  -> G0-G7 evaluation only
```

## Scientific invariant

The r1 entrypoint imports the original v0.3.2 simulator, raw feature extractor and M10 grid rather than copying them. Therefore the next-stage experiment changes the representation layer while preserving the mechanism layer being challenged.
