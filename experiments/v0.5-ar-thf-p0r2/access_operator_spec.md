# PH v0.5 AR-THF — Frozen Access Operators (P0-r2)

## Canonical physical surface

s=(x1,x2,v,etaO*o,mB,r).
etaO=1.0 except where explicitly registered.

A0 and A1 act only on this physical surface and never receive model identity or latent-node names.

## A0 — external-only coarse access

Inputs: uF,uS.
Observation interval: 0.10 s.
Delay: 0.
yV=v+0.25*r+measurement_noise_V
yO=etaO*o+0.20*x2+measurement_noise_O
R=diag(0.05,0.05).

All registered A0 input profiles are zero before t=20.0 s and after t=25.0 s.

1. zero:
   uF=uS=0 always.

2. Fast finite pulse:
   uF=1.0 on [20.0,21.0), otherwise 0; uS=0.

3. Slow finite pulse:
   uS=1.0 on [20.0,21.0), otherwise 0; uF=0.

4. Fast multisine:
   tau=t-20.0.
   On [20.0,25.0):
   uF=0.5*sin(2*pi*0.20*tau)+0.5*sin(2*pi*0.37*tau).
   Otherwise uF=0; uS=0.

5. Slow deterministic PRBS-like dwell sequence:
   dwell=0.5 s, ten dwells on [20.0,25.0).
   signs=[+1,-1,+1,+1,-1,-1,+1,-1,-1,+1].
   For dwell j=0..9, uS=0.7*signs[j].
   Outside [20.0,25.0), uS=0; uF=0.
   No random PRBS generator is permitted.

## A1 — multi-resolution observation

a_high:
- sample interval 0.01 s
- delay 0
- observe all six canonical surface coordinates
- R=0.01*I6

a_mid:
- sample interval 0.05 s
- delay 0.05 s
- observe (v,etaO*o,mB)
- R=0.05*I3

a_low:
- sample interval 0.20 s
- delay 0.20 s
- observe (v+0.25*r,etaO*o+0.20*x2)
- R=0.20*I2

G3 artifact operator:
Only for G3 under a_low:
yO_artifact=(etaO*o+0.20*x2)+0.40*(v+0.25*r).
No plant coefficient changes.

H1 uses the SAME paired plant path across high/mid/low.
Measurement-noise streams are independent across access labels.

## A2 — model-independent spatial local intervention

A2 may not address x5, zV or zO by name.

K(r;r_c)=exp(-(r-r_c)^2/(2*sigma_loc^2)), sigma_loc=0.20.
Registered centers r_c={-0.50,0.00,+0.50}.

u_loc(t)=2.0 on [20.0,21.0), otherwise 0.
For every mediator node j at preregistered physical position r_j:
q_local,j(t)=u_loc(t)*K(r_j;r_c).

The actuator equation is identical for all models.
Model identity is not an argument.
H5 aggregates all three centers by arithmetic mean; no best-center selection.

## A3 — environment reach probe

uF=2.0 on [20.0,21.0), otherwise 0.
uS=0.
Observe e1..e8 every 0.10 s from 20.1 through 25.0 inclusive (50 samples).
Counterfactual control uses uF=0 with paired PLANT common random numbers.

## H4 synthetic matched-observed-state reset

History +: uF=+0.8 on [5.0,15.0).
History -: uF=-0.8 on [5.0,15.0).

At t=15.0 both trajectories have canonical surface s and e1..e8 overwritten to the exact same baseline-reference values from the paired zero-input path at t=15.0.
G5 hidden h is NOT reset.
G4 has no hidden h.
Immediate post-reset canonical max absolute mismatch must be <=1e-10.
Future window [15.0,20.0], uF=uS=0.

## H3 unseen target chirp

This is a TARGET-only protocol and uses the H3_TARGET stochastic stream, never the feature-measurement stream.

tau=t-20.0.
On [20.0,25.0):
uF=1.5*sin(2*pi*(0.15*tau+0.5*0.06*tau^2)).
Outside this window uF=0.
uS=0.
Instantaneous frequency therefore sweeps from 0.15 Hz at tau=0 to 0.45 Hz at tau=5.
