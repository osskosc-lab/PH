from __future__ import annotations
import math
import numpy as np
from ph.imperfect_clamp import effective_lambda
from ph.latent_driver import clamped_path_fraction


def _stress_values(cfg, factor, strength):
    s=float(strength); st=cfg['stress']['factors']
    vals=dict(leak=0.0, clamp_noise=0.0, meas=0.0, latent=0.0, cvo=0.0, rho=0.0, drift=0.0)
    if factor == 'clamp_leakage': vals['leak']=st[factor]['max_fraction']*s
    elif factor == 'clamp_noise': vals['clamp_noise']=st[factor]['max_sigmaB_ratio']*s
    elif factor == 'measurement_error': vals['meas']=st[factor]['max_K_sd']*s
    elif factor == 'latent_driver': vals['latent']=st[factor]['max_unclamped_to_boundary_ratio']*s
    elif factor == 'weak_vo_coupling': vals['cvo']=st[factor]['max_c_vo']*s
    elif factor == 'colored_noise': vals['rho']=st[factor]['max_rho']*s
    elif factor == 'parameter_drift': vals['drift']=st[factor]['max_curvature_shift']*s
    elif factor == 'compound':
        vals['leak']=st['clamp_leakage']['max_fraction']*s
        vals['latent']=st['latent_driver']['max_unclamped_to_boundary_ratio']*s
        vals['rho']=st['colored_noise']['max_rho']*s
    elif factor in ('none', None): pass
    else: raise ValueError(factor)
    return vals


def simulate_dose_response(seeds, cfg, mode, factor='none', strength=0.0, noise_code=0):
    """Reduced-form local-linear intervention response calibrated to PH v0.3.

    The object under audit is K(lambda), not a new biological model. The free
    frequency-domain causal structure was validated in v0.3; v0.3.1 perturbs
    the intervention layer and asks when that detector loses identifiability.
    """
    seeds=np.asarray(seeds, int); N=len(seeds)
    lam=np.asarray(cfg['lambdas']['all'], float)
    b=cfg['baseline_response']; vals=_stress_values(cfg,factor,strength)
    rng=np.random.default_rng(np.random.SeedSequence([int(seeds[0]),int(noise_code),N]))

    if mode == 'shared_boundary':
        e=rng.normal(1.0,b['efficacy_sd_shared'],N); ev=e; eo=e
        cv=rng.normal(b['curvature_mean'],b['curvature_sd_shared'],N)
        co=cv+rng.normal(0.0,b['output_curvature_jitter'],N)
        pv=clamped_path_fraction(vals['latent'])
        po=clamped_path_fraction(vals['latent']+0.35*vals['cvo'])
    elif mode in ('separate_boundary','viability_only'):
        ev=rng.normal(1.0,b['efficacy_sd_shared'],N); eo=np.zeros(N)
        cv=rng.normal(b['curvature_mean'],b['curvature_sd_shared'],N); co=np.zeros(N)
        pv=clamped_path_fraction(vals['latent']); po=0.0
    elif mode == 'observability_only':
        ev=np.zeros(N); eo=rng.normal(1.0,b['efficacy_sd_shared'],N)
        cv=np.zeros(N); co=rng.normal(b['curvature_mean'],b['curvature_sd_shared'],N)
        pv=0.0; po=clamped_path_fraction(vals['latent'])
    elif mode in ('common_driver','null','adversarial_mimic'):
        ev=eo=cv=co=np.zeros(N); pv=po=0.0
    elif mode == 'adversarial_clamp_mimic':
        # Marginal dose-response is deliberately shared-like, but target-specific
        # intervention efficacy/curvature are independent across V and O.
        ev=rng.normal(1.0,b['efficacy_sd_adversarial'],N)
        eo=rng.normal(1.0,b['efficacy_sd_adversarial'],N)
        cv=rng.normal(b['curvature_mean'],b['curvature_sd_adversarial'],N)
        co=rng.normal(b['curvature_mean'],b['curvature_sd_adversarial'],N)
        pv=po=clamped_path_fraction(vals['latent'])
    else: raise ValueError(mode)

    q=effective_lambda(lam,vals['leak'])
    rho=vals['rho']; inflate=math.sqrt((1.0+rho)/max(1.0-rho,1e-8))
    sd=(b['estimator_noise_sd']+vals['meas']+0.03*vals['clamp_noise'])*inflate

    if mode == 'shared_boundary':
        ce=rng.normal(1.0,0.04*vals['clamp_noise'],N); cev=ceo=ce
    else:
        cev=rng.normal(1.0,0.04*vals['clamp_noise'],N)
        ceo=rng.normal(1.0,0.04*vals['clamp_noise'],N)

    KV=np.zeros((N,len(lam))); KO=np.zeros_like(KV)
    for j,x0 in enumerate(q):
        xv=np.clip(x0*cev,0.0,1.2); xo=np.clip(x0*ceo,0.0,1.2)
        KV[:,j]=ev*pv*(xv-(cv+vals['drift'])*xv*(1.0-np.clip(xv,0,1)))+rng.normal(0.0,sd,N)
        KO[:,j]=eo*po*(xo-(co+vals['drift'])*xo*(1.0-np.clip(xo,0,1)))+rng.normal(0.0,sd,N)
    return {'lambda':lam,'K_V':KV,'K_O':KO,'stress_values':vals}
