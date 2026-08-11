from __future__ import annotations
import numpy as np

def _features(u,v,o,burn):
    idx=np.arange(burn+4,len(u))
    XV=np.c_[v[idx-1],v[idx-2],v[idx-3],u[idx-1],np.ones(len(idx))]
    XO=np.c_[o[idx-1],o[idx-2],o[idx-3],u[idx-1],np.ones(len(idx))]
    return XV,v[idx],XO,o[idx]

def fit(train_triplets,burn,stride=8,lam=1e-3):
    Xv=[];yv=[];Xo=[];yo=[]
    for u,v,o in train_triplets:
        a,b,c,d=_features(u,v,o,burn);Xv.append(a[::stride]);yv.append(b[::stride]);Xo.append(c[::stride]);yo.append(d[::stride])
    Xv=np.vstack(Xv);yv=np.concatenate(yv);Xo=np.vstack(Xo);yo=np.concatenate(yo)
    bv=np.linalg.solve(Xv.T@Xv+lam*np.eye(Xv.shape[1]),Xv.T@yv)
    bo=np.linalg.solve(Xo.T@Xo+lam*np.eye(Xo.shape[1]),Xo.T@yo)
    return bv,bo

def rmse(model,triplets,burn):
    bv,bo=model; se=[]
    for u,v,o in triplets:
        Xv,yv,Xo,yo=_features(u,v,o,burn);pv=Xv@bv;po=Xo@bo;se.extend([(yv-pv)**2,(yo-po)**2])
    return float(np.sqrt(np.mean(np.concatenate(se))))
