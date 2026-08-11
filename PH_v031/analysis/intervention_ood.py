from __future__ import annotations
import numpy as np
from models import shared_intervention,separate_intervention

def error_components(KV,KO,lambdas,train_mask,ood_mask):
    sv,so=shared_intervention.predict_ood(KV,KO,lambdas,train_mask,ood_mask)
    dv,do=separate_intervention.predict_ood(KV,KO,lambdas,train_mask,ood_mask)
    yv=np.asarray(KV)[:,ood_mask]; yo=np.asarray(KO)[:,ood_mask]
    shared2=np.mean(np.c_[(yv-sv)**2,(yo-so)**2],axis=1)
    separate2=np.mean(np.c_[(yv-dv)**2,(yo-do)**2],axis=1)
    return shared2,separate2

def causal_intervention_consistency(beta_v,beta_o):
    """Joint intervention consistency as an error ratio.

    For optimal linear cross-output prediction, residual SD / baseline SD is
    sqrt(1-r^2). A Fisher-z lower bound on positive correlation yields a
    conservative UCB for the error ratio. This tests a shared seed-level
    intervention state without requiring K_V(lambda) == K_O(lambda).
    """
    bv=np.asarray(beta_v,float); bo=np.asarray(beta_o,float); n=len(bv)
    if n<5 or np.std(bv)<1e-12 or np.std(bo)<1e-12:
        return {'R_CIC':1.0,'R_CIC_LCB':1.0,'R_CIC_UCB':1.0,'corr':0.0,'corr_LCB':-1.0,'corr_UCB':1.0}
    r=float(np.clip(np.corrcoef(bv,bo)[0,1],-0.999999,0.999999))
    z=np.arctanh(r); se=1.0/np.sqrt(max(n-3,1))
    rl=float(np.tanh(z-1.96*se)); ru=float(np.tanh(z+1.96*se))
    point=float(np.sqrt(max(0.0,1-r*r)))
    # Smaller R_CIC is better. If positive correlation is not established, UCB=1.
    ucb=1.0 if rl<=0 else float(np.sqrt(max(0.0,1-rl*rl)))
    # optimistic lower bound uses the larger positive correlation magnitude
    lcb=float(np.sqrt(max(0.0,1-max(0.0,ru)**2)))
    return {'R_CIC':point,'R_CIC_LCB':lcb,'R_CIC_UCB':ucb,'corr':r,'corr_LCB':rl,'corr_UCB':ru}

def kernel_ratio(KV,KO,lambdas,train_mask,ood_mask,bandwidth=.22):
    lam=np.asarray(lambdas,float); x=lam[train_mask]; xo=lam[ood_mask]
    es=[];ed=[]
    for i in range(len(KV)):
        av=float(KV[i,-1]); ao=float(KO[i,-1])
        if abs(av)<.15 or abs(ao)<.15: continue
        nv=KV[i,train_mask]/av; no=KO[i,train_mask]/ao
        for xx,j in zip(xo,np.where(ood_mask)[0]):
            w=np.exp(-.5*((x-xx)/bandwidth)**2); w/=w.sum()
            pooled=np.dot(w,(nv+no)/2)
            pv=pooled*av; po=pooled*ao
            sv=np.dot(w,nv)*av; so=np.dot(w,no)*ao
            es += [(KV[i,j]-pv)**2,(KO[i,j]-po)**2]
            ed += [(KV[i,j]-sv)**2,(KO[i,j]-so)**2]
    if not es:return float('nan')
    return float(np.sqrt(np.mean(es))/max(np.sqrt(np.mean(ed)),1e-12))
