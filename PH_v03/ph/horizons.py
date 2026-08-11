from __future__ import annotations
import numpy as np


def margin_audit(sim,burn,saturation_abs=0.98):
    sl=slice(burn,None)
    mv=sim['M_V'][:,sl]; mo=sim['M_O'][:,sl]
    lv=sim['latent_V'][:,sl]; lo=sim['latent_O'][:,sl]
    return {
        'sd_V':np.std(mv,axis=1),'sd_O':np.std(mo,axis=1),
        'sat_V':np.mean(np.abs(lv)>=saturation_abs,axis=1),
        'sat_O':np.mean(np.abs(lo)>=saturation_abs,axis=1),
    }
