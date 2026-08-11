from __future__ import annotations
import numpy as np
from scipy import signal


def _rng(seed: int, code: int) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([int(seed), int(code)]))


def multisine(seeds, T, burn, freqs, amplitude, code=11):
    seeds=np.asarray(seeds,dtype=int); L=T-burn; t=np.arange(L,dtype=float)
    U=np.zeros((len(seeds),T),dtype=float)
    phases=np.zeros((len(seeds),len(freqs)),dtype=float)
    norm=np.sqrt(len(freqs))
    for i,s in enumerate(seeds):
        r=_rng(int(s),code); ph=r.uniform(0,2*np.pi,len(freqs)); phases[i]=ph
        x=np.zeros(L)
        for f,p in zip(freqs,ph): x += np.sin(2*np.pi*f*t+p)
        U[i,burn:]=amplitude*x/norm
    return U, phases


def prbs(seeds,T,burn,amplitude,block=8,code=23):
    seeds=np.asarray(seeds,dtype=int); L=T-burn; U=np.zeros((len(seeds),T))
    nblocks=(L+block-1)//block
    for i,s in enumerate(seeds):
        vals=_rng(int(s),code).choice([-amplitude,amplitude],nblocks)
        U[i,burn:]=np.repeat(vals,block)[:L]
    return U


def impulse(seeds,T,burn,amplitude,offset=64):
    U=np.zeros((len(seeds),T)); U[:,burn+offset]=amplitude; return U


def unseen_frequency(seeds,T,burn,freqs,amplitude,code=31):
    return multisine(seeds,T,burn,freqs,amplitude,code=code)[0]


def unseen_amplitude(seeds,T,burn,freqs,amplitude,code=37):
    return multisine(seeds,T,burn,freqs,amplitude,code=code)[0]


def chirp(seeds,T,burn,f0,f1,amplitude,code=41):
    seeds=np.asarray(seeds,dtype=int); L=T-burn; t=np.arange(L,dtype=float); U=np.zeros((len(seeds),T))
    for i,s in enumerate(seeds):
        r=_rng(int(s),code)
        x=signal.chirp(t,f0=f0,f1=f1,t1=L-1,method='logarithmic',phi=float(r.uniform(0,360)))
        x += 0.35*np.sin(2*np.pi*(1/48)*t+r.uniform(0,2*np.pi))
        U[i,burn:]=amplitude*x
    return U


def direct_prbs(seeds,T,burn,amplitude=0.12,block=16,code=53):
    return prbs(seeds,T,burn,amplitude,block,code)
