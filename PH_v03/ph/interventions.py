from __future__ import annotations
import numpy as np
from .dynamics import simulate
from .stimuli import direct_prbs


def boundary_clamp_pair(U,seeds,cfg,mode,noise_code):
    free=simulate(U,seeds,cfg,mode,False,noise_code=noise_code)
    clamp=simulate(U,seeds,cfg,mode,True,noise_code=noise_code)
    return free,clamp


def downstream_specificity(seeds,cfg,mode):
    T=cfg['time']['T']; burn=cfg['time']['burn_in']; U=np.zeros((len(seeds),T))
    dv=direct_prbs(seeds,T,burn,amplitude=0.12,block=16,code=71); z=np.zeros_like(U)
    base=simulate(U,seeds,cfg,mode,False,z,z,noise_code=910)
    vdo=simulate(U,seeds,cfg,mode,False,dv,z,noise_code=910)
    odo=simulate(U,seeds,cfg,mode,False,z,dv,noise_code=910)
    sl=slice(burn,None)
    def rms(x): return np.sqrt(np.mean(x[:,sl]**2,axis=1))
    v_own=rms(vdo['M_V']-base['M_V']); v_cross=rms(vdo['M_O']-base['M_O'])
    o_own=rms(odo['M_O']-base['M_O']); o_cross=rms(odo['M_V']-base['M_V'])
    eps=1e-12
    return {'V_cross_ratio':v_cross/(v_own+eps),'O_cross_ratio':o_cross/(o_own+eps),'V_own':v_own,'O_own':o_own}
