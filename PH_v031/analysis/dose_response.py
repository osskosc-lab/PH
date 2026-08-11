from __future__ import annotations
import numpy as np

def slopes(K,lambdas,train_mask):
    x=np.asarray(lambdas)[train_mask]
    return np.asarray([np.polyfit(x,row[train_mask],1)[0] for row in np.asarray(K)],float)

def value_at(K,lambdas,target):
    j=int(np.argmin(np.abs(np.asarray(lambdas)-float(target))))
    return np.asarray(K)[:,j]

def monotonic_fraction(K):
    d=np.diff(np.asarray(K),axis=1)
    return float(np.mean(np.mean(d>=-0.03,axis=1)>=0.80))
