from __future__ import annotations
import numpy as np
from scipy import optimize

def H(w,r1,r2,g):
    z=np.exp(-1j*w); return g*z*z/((1-r1*z)*(1-r2*z))

def fit_shared_factor(freqs,hv,ho):
    w=2*np.pi*np.asarray(freqs)
    def res(x):
        rb,rv,ro,gv,go=x; pv=H(w,rb,rv,gv);po=H(w,rb,ro,go)
        sv=np.maximum(np.abs(hv),0.02);so=np.maximum(np.abs(ho),0.02);d=np.r_[(pv-hv)/sv,(po-ho)/so]
        return np.r_[d.real,d.imag]
    starts=([.96,.82,.62,.03,-.03],[.94,.72,.55,.03,-.03],[.98,.88,.45,.03,-.03]);best=None
    for x0 in starts:
        rr=optimize.least_squares(res,x0,bounds=([.90,.2,.2,-1,-1],[.995,.90,.90,1,1]),max_nfev=300)
        val=float(np.mean(res(rr.x)**2))
        if best is None or val<best[0]: best=(val,rr.x)
    rb=best[1][0]; tau=float(-1/np.log(max(rb,1e-9)))
    return {'rho_B':float(rb),'tau_B':tau,'params':best[1].tolist(),'loss':best[0]}
