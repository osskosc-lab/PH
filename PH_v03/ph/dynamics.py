from __future__ import annotations
import numpy as np


def _noise(seeds, T, code, scale):
    out=np.empty((len(seeds),T),dtype=float)
    for i,s in enumerate(seeds):
        r=np.random.default_rng(np.random.SeedSequence([int(s),int(code)]))
        out[i]=r.normal(0.0,scale,T)
    return out


def simulate(U,seeds,cfg,mode,clamp_shared=False,direct_v=None,direct_o=None,noise_code=100):
    U=np.asarray(U,float); seeds=np.asarray(seeds,int); N,T=U.shape
    d=cfg['dynamics']; scale=d['margin_scale']
    nB=_noise(seeds,T,noise_code+1,d['process_noise_B'])
    nB2=_noise(seeds,T,noise_code+2,d['process_noise_B'])
    nV=_noise(seeds,T,noise_code+3,d['process_noise_downstream'])
    nO=_noise(seeds,T,noise_code+4,d['process_noise_downstream'])
    eV=_noise(seeds,T,noise_code+5,d['measurement_noise'])
    eO=_noise(seeds,T,noise_code+6,d['measurement_noise'])
    B=np.zeros(N); BV=np.zeros(N); BO=np.zeros(N); V=np.zeros(N); O=np.zeros(N)
    MV=np.zeros((N,T)); MO=np.zeros((N,T)); latentV=np.zeros((N,T)); latentO=np.zeros((N,T)); Btrace=np.zeros((N,T))
    if direct_v is None: direct_v=np.zeros_like(U)
    if direct_o is None: direct_o=np.zeros_like(U)
    for t in range(T-1):
        if mode in ('shared_boundary','viability_only','observability_only'):
            if clamp_shared:
                Bn=np.zeros(N)
            else:
                Bn=d['rho_B']*B+d['kappa']*U[:,t]+nB[:,t]
            if mode in ('shared_boundary','viability_only'):
                Vn=d['rho_V']*V+d['alpha_V']*B+nV[:,t]+direct_v[:,t]
            else:
                Vn=d['rho_V']*V+nV[:,t]+direct_v[:,t]
            if mode in ('shared_boundary','observability_only'):
                On=d['rho_O']*O+d['alpha_O']*B+nO[:,t]+direct_o[:,t]
            else:
                On=d['rho_O']*O+nO[:,t]+direct_o[:,t]
            B=Bn; Btrace[:,t+1]=B
        elif mode=='separate_boundary':
            BVn=d['separate_rho_BV']*BV+d['kappa']*U[:,t]+nB[:,t]
            BOn=d['separate_rho_BO']*BO+d['kappa']*U[:,t]+nB2[:,t]
            Vn=d['rho_V']*V+d['alpha_V']*BV+nV[:,t]+direct_v[:,t]
            On=d['rho_O']*O+d['alpha_O']*BO+nO[:,t]+direct_o[:,t]
            BV,BO=BVn,BOn
        elif mode=='adversarial_mimic':
            # Deterministic transfer functions match shared_boundary, but boundary noises are independent.
            BVn=d['rho_B']*BV+d['kappa']*U[:,t]+nB[:,t]
            BOn=d['rho_B']*BO+d['kappa']*U[:,t]+nB2[:,t]
            Vn=d['rho_V']*V+d['alpha_V']*BV+nV[:,t]+direct_v[:,t]
            On=d['rho_O']*O+d['alpha_O']*BO+nO[:,t]+direct_o[:,t]
            BV,BO=BVn,BOn
        elif mode=='common_driver':
            Vn=d['rho_V']*V+d['common_beta_V']*U[:,t]+nV[:,t]+direct_v[:,t]
            On=d['rho_O']*O+d['common_beta_O']*U[:,t]+nO[:,t]+direct_o[:,t]
        elif mode=='null':
            Vn=d['rho_V']*V+nV[:,t]+direct_v[:,t]
            On=d['rho_O']*O+nO[:,t]+direct_o[:,t]
        else:
            raise ValueError(mode)
        V,O=Vn,On
        latentV[:,t+1]=np.tanh(V/scale); latentO[:,t+1]=np.tanh(O/scale)
        MV[:,t+1]=latentV[:,t+1]+eV[:,t+1]; MO[:,t+1]=latentO[:,t+1]+eO[:,t+1]
    return {'M_V':MV,'M_O':MO,'latent_V':latentV,'latent_O':latentO,'B':Btrace}
