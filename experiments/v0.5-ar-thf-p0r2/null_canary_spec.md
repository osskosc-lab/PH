# PH v0.5 AR-THF — Frozen Null Canary Suite (P0-r2)

These are qualification canaries. They do not estimate a universal false-positive rate.

## H1 null
Run G0 with two labels that both use the exact a_mid observation operator and independent MEASUREMENT noise.
Apply the unchanged H1 decision code.
Expected qualification condition: H1 support rule is NOT satisfied.

## H2 null
For each of the three H2 targeted-control slots, compare G0 against a byte-for-byte G0 duplicate with zero parameter change using the registered pair_group.
Apply the unchanged H2 decision code.
Expected: fewer than 2 of 3 targeted controls pass.

## H3 null
Use the balanced G0-HET lattice but fix lambda_I=1.0 for all master indices while preserving lambda_V and lambda_O.
Generate FEATURE and H3_TARGET with independent streams exactly as in the primary H3 protocol.
Expected: H3 support rule is NOT satisfied.

## H4 null
Use G4 historyless with the exact H+/H- reset procedure.
Expected: median d_G4<=0.01 and H4 support rule is NOT satisfied.

## H5 null
Compare G0 to a byte-for-byte G0 duplicate under all three A2 centers with the same paired PLANT streams.
Expected: H5 support rule is NOT satisfied.

Any null canary producing support is Q8 FAIL and hard STOP.
