from __future__ import annotations
import numpy as np

def predict_ood(KV,KO,lambdas,train_mask,ood_mask):
    x=np.asarray(lambdas)[train_mask]; xo=np.asarray(lambdas)[ood_mask]
    b2=x*(1-x); b3=x*(1-x)*(1-2*x)
    B2=xo*(1-xo); B3=xo*(1-xo)*(1-2*xo)
    Z=np.zeros((2*len(x),4)); Zo=np.zeros((2*len(xo),4))
    Z[:len(x),0]=x; Z[:len(x),2]=b2; Z[:len(x),3]=b3
    Z[len(x):,1]=x; Z[len(x):,2]=b2; Z[len(x):,3]=b3
    Zo[:len(xo),0]=xo; Zo[:len(xo),2]=B2; Zo[:len(xo),3]=B3
    Zo[len(xo):,1]=xo; Zo[len(xo):,2]=B2; Zo[len(xo):,3]=B3
    N=KV.shape[0]; pv=np.zeros((N,len(xo))); po=np.zeros_like(pv)
    for i in range(N):
        y=np.r_[KV[i,train_mask],KO[i,train_mask]]
        b=np.linalg.lstsq(Z,y,rcond=None)[0]; p=Zo@b
        pv[i]=p[:len(xo)]; po[i]=p[len(xo):]
    return pv,po
