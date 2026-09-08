# PH v0.5 AR-THF — Frozen Metrics (P0-r2)

## H_V

At t=20.0 s apply v <- v-D.
D_grid={0.00,0.15,0.30,...,3.00}.
For each master seed and D use 64 stochastic replicates paired against a no-disturbance reference.

Recovery TRUE iff for every 0.10 s sample in [28.0,30.0]:
1. RMS over the six canonical surface coordinates of s_disturbed-s_reference <=0.20,
2. v>0.25,
3. no divergence/finite failure.

P_recovery(D)=mean of 64 replicate indicators.
tauV=0.80.
H_V=D*=max{D in D_grid:P_recovery(D)>=0.80}.
If no D passes, D*=0. If all pass, D*=3.0 and Q9 ceiling audit applies.

## H_O

Extended Kalman Filter on the full internal model state excluding environment e1..e8 and deterministic input-filter state.

- initial mean = generator initial state
- P0=0.25*I_n
- Q=diag(diffusion^2)*dt
- R exactly as access_operator_spec.md
- nonlinear Jacobians: central finite difference step 1e-5
- Joseph covariance update
- run 30.0 s
- first 20.0 s ignored
- convergence: ||Ppost_k-Ppost_(k-1)||_F<1e-8 for 100 consecutive observation updates
- no convergence by 30.0 s => EKF_CONVERGENCE_FAIL

Omega_a=median over the final 500 available post-burn-in updates of tr(Ppost)/tr(Pprior).
If fewer than 500 updates exist, use all post-burn-in updates.

H1:
Delta_O=Omega_low-Omega_high.
Primary access-relativity rule:
median |Delta_O|>=0.05 AND two-sided paired Wilcoxon p<0.002.
Wilcoxon implementation is scipy.stats.wilcoxon with zero_method="wilcox", correction=False, alternative="two-sided", method="auto".
Direction Omega_low>Omega_high is descriptive, not required by the H1 claim.

## H_I

For each master seed use 64 intervention replicates and 64 paired controls.
For node k and j=1..50:
t_j=0.1*j seconds after intervention start.
w_j=exp(-0.5*t_j)/SUM_{q=1..50}exp(-0.5*0.1*q).

W1 is exact equal-weight 1D empirical Wasserstein-1 distance between the sorted 64 intervention and 64 control samples of e_k at t_j.

H_I=(1/8)*SUM_k SUM_j w_j*W1_kj.

## H4 history effect

After the exact observed-state reset, sample canonical surface every 0.10 s over [15.0,20.0].
For each master seed compute normalized paired RMS future difference:
d_g = RMS(signature_Hplus-signature_Hminus)/(RMS(signature_zero)+1e-8).

Qualification null requires median d_G4<=0.01.

Pilot H4 uses paired differences q_i=d_G5_i-d_G4_i.
Primary statistic T=median(q_i).
Permutation test: B=20000 Rademacher sign flips of q_i using the frozen H4 permutation seed; p=(1+#{T_b>=T_obs})/(B+1).
H4 support requires median d_G5>=0.05 AND T>0 AND p<0.002.
No other permutation scheme is allowed.

## H3 H_I non-redundancy

Use G0-HET from synthetic_generator_spec.md.

For each Pilot master seed build features from FEATURE streams:
X0=[H_V,Omega_high,Omega_mid,Omega_low].
X1=[H_V,Omega_high,Omega_mid,Omega_low,H_I].

Target Y uses the independent H3_TARGET stream and the frozen unseen chirp:
Y=(1/8)*SUM_k integral_20^25 |e_k(t)-e_k_control(t)| dt.

The same G0-HET structural parameters are used for feature and target runs, but stochastic streams are independent between FEATURE and H3_TARGET.
Within the H3_TARGET intervention/control pair, common random numbers are used.

Balanced split:
- train master indices 2000..2119 (120; first 3 complete lattice repeats)
- test master indices 2120..2199 (80; final 2 complete repeats)
- no shuffle

Standardize features with training mean/std only.
Predictor: Ridge(alpha=1.0,fit_intercept=True), no tuning.
Loss: test MSE.
R_I=MSE_full/MSE_base.
Bootstrap 80 paired test squared-error differences with B=2000 using the frozen H3 bootstrap stream.
H3 support requires R_I<0.85 AND 95% bootstrap upper bound <0.85.

H3 null canary fixes lambda_I=1.0 while preserving the lambda_V/lambda_O lattice and all analysis code; it must NOT satisfy the H3 support rule.

## H2 directional separability

Compare G7,G8,G9 to paired G0.
Targets:
G7 -> H_I
G8 -> H_V
G9 -> Omega_low

For each metric M define robust scale:
scale_M=max(MAD_G0(M),0.05*abs(median_G0(M)),1e-3).

Standardized change Delta_M=median(M_target-M_G0)/scale_M.

Selectivity ratio S=|Delta_target|/(max(|Delta_non1|,|Delta_non2|)+1e-8).
A targeted control passes if |Delta_target|>=0.20 and S>2.0.
H2 support requires at least 2 of 3 targeted controls pass.

Reducibility red flag:
all three pairwise horizon correlations >0.90 AND PC1 explained variance >0.90 across all registered H2 cells.

## H5 enriched-access identifiability

A0 analytic equivalence must be numerically replayed:
max absolute paired noiseless A0 yV/yO difference G0 vs G6 <=1e-10 for every Q4 seed/profile.

A2 outcome vector=(v,o,e1..e8), sampled every 0.10 s over [20.0,25.0].
For each center compute normalized RMS paired G0-vs-G6 difference:
D_center=RMS(Y_G0-Y_G6)/(RMS(Y_G0)+1e-8).
Per seed D_A2=mean over the three centers.

Primary H5 rule:
median D_A2>=0.05 AND one-sample Wilcoxon of D_A2 against zero gives p<0.002.
Wilcoxon settings: zero_method="wilcox", correction=False, alternative="greater", method="auto".

Failure yields NON_IDENTIFIABLE_UNDER_TESTED_ACCESS, not support for a shared node.
H5 null canary is G0 versus a byte-for-byte G0 duplicate under A2 with the exact same paired PLANT stream; it must NOT satisfy H5 support.
