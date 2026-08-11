from __future__ import annotations
import numpy as np

def predict_ood(KV,KO,lambdas,train_mask,ood_mask):
    x=np.asarray(lambdas)[train_mask]; xo=np.asarray(lambdas)[ood_mask]
    X=np.c_[x,x*(1-x),x*(1-x)*(1-2*x)]
    XO=np.c_[xo,xo*(1-xo),xo*(1-xo)*(1-2*xo)]
    N=KV.shape[0]; pv=np.zeros((N,len(xo))); po=np.zeros_like(pv)
    for i in range(N):
        bv=np.linalg.lstsq(X,KV[i,train_mask],rcond=None)[0]
        bo=np.linalg.lstsq(X,KO[i,train_mask],rcond=None)[0]
        pv[i]=XO@bv; po[i]=XO@bo
    return pv,po
