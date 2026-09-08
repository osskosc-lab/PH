# PH v0.5 AR-THF — Frozen Metrics

## H_V — viability horizon

At t=20.0 s apply v <- v-D.
D_grid={0.00,0.15,0.30,...,3.00}.
For each master seed and D use 64 stochastic replicates with common random numbers against a no-disturbance reference.

Recovery is TRUE iff for every sample in [28.0,30.0] s:
1. RMS over canonical surface coordinates of s_disturbed-s_reference <=0.20, and
2. v>0.25, and
3. no divergence/finite failure occurred.

P_recovery(D)=mean of 64 replicate indicators.
tauV=0.80.
H_V=D*=max{D in D_grid:P_recovery(D)>=0.80}.
If no D passes, D*=0. If all pass, D*=3.0 and Q9 ceiling audit applies.

## H_O — access-relative opacity

Use an Extended Kalman Filter on the full internal model state excluding environment e1..e8 and deterministic input filter.
- initial mean: generator initial state
- P0=0.25*I_n
- process covariance Q=diag(diffusion^2)*dt
- observation R exactly as access_operator_spec.md
- nonlinear Jacobians: central finite difference step 1e-5
- covariance update: Joseph form
- run 30.0 s
- first 20.0 s ignored
- convergence: ||Ppost_k-Ppost_(k-1)||_F<1e-8 for 100 consecutive observation updates
- failure to converge by end of run => EKF_CONVERGENCE_FAIL

Per converged run:
Omega_a=median over final 500 available updates of tr(Ppost)/tr(Pprior).
For access streams with fewer than 500 final updates, use all updates after 20.0 s.

H1 primary contrast:
Delta_O=Omega_low-Omega_high.
Support direction requires median |Delta_O|>=0.05 and two-sided paired Wilcoxon p<0.002.

## H_I — influence horizon

For each master seed use 64 stochastic replicates under A3 intervention and 64 paired control replicates.
For each environment node k and sample j:
t_j=0.1*j seconds after intervention start, j=1..50.
w_j=exp(-0.5*t_j)/SUM_{q=1..50} exp(-0.5*0.1*q).

W1 is the exact 1D empirical Wasserstein-1 distance between the 64 intervention and 64 control samples for e_k at t_j, computed from sorted samples with equal weights.

H_I=(1/8)*SUM_k SUM_j w_j*W1_kj.

## History effect Delta_H

After the frozen observed-state reset, flatten the canonical surface samples from [15,20] s at 0.10 s resolution.
Delta_H is the empirical energy distance between the H+ and H- future trajectory-signature distributions across master seeds.
For per-seed diagnostics use normalized RMS paired trajectory difference.
G4 null median per-seed RMS must be <=0.01 at Qualification.
H4 Pilot support requires G5 median normalized RMS >=0.05 and paired/permutation p<0.002 versus the G4 null distribution.

## H3 H_I non-redundancy

For each P3 Pilot master seed build:
Base X0=[H_V,Omega_high,Omega_mid,Omega_low].
Full X1=[H_V,Omega_high,Omega_mid,Omega_low,H_I].

Prediction target Y is the integrated environment response energy to an unseen Fast chirp:
uF(t)=1.5*sin(2*pi*(0.15*t+0.5*(0.30/5.0)*t^2)) for five seconds after t=20; uS=0.
Y=(1/8)*SUM_k integral_20^25 |e_k(t)-e_k_control(t)| dt using common random numbers.

P3 indices 2000..2139 are training; 2140..2199 are test. No shuffle.
Feature standardization uses training mean/std only.
Predictor: sklearn-compatible Ridge(alpha=1.0,fit_intercept=True), no tuning.
Loss: test mean squared error.
R_I=MSE_full/MSE_base.
Bootstrap the 60 paired test squared-error differences with B=2000 using frozen bootstrap substreams.
H3 support requires point R_I<0.85 AND 95% bootstrap upper bound <0.85.

## H2 directional separability

Compare G7,G8,G9 to paired G0.
Target metrics:
G7 -> H_I
G8 -> H_V
G9 -> Omega_low

For each generator compute absolute standardized median change for target T and the two non-target primary horizons, where standardization divisor is the paired G0 MAD+1e-8.

Selectivity ratio S=|Delta_T|/(max(|Delta_nonT1|,|Delta_nonT2|)+1e-8).
A targeted control passes if |Delta_T|>=0.20 and S>2.0.
H2 directional-separation support requires at least 2 of 3 targeted controls pass.
A reducibility red flag is raised if across all registered intervention cells every pairwise horizon correlation exceeds 0.90 AND PC1 explained variance >0.90.

## H5 identifiability under enriched access

A0 equivalence is analytic by G6 construction and must additionally satisfy numerical replay:
max absolute difference of paired noiseless A0 yV/yO trajectories between G0 and G6 <=1e-10 for every Q4 seed/profile.

For A2, form noiseless physical outcome vector (v,o,e1..e8) sampled every 0.10 s over [20,25] s.
For each center compute normalized RMS paired G0-vs-G6 difference with denominator RMS(G0)+1e-8.
D_A2 is arithmetic mean over the three centers.
H5 enriched-access support requires median D_A2>=0.05 and paired Wilcoxon p<0.002.
Failure at effect threshold yields NON_IDENTIFIABLE_UNDER_TESTED_ACCESS, not support for a shared node.
