#!/usr/bin/env python3
"""PH v0.2.1 causal-specificity falsification engine.
Synthetic detector validation only; not evidence that PH exists in nature.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd

VERSION="PH-v0.2.1-causal-specificity-1.1"
MODES=("M0_coupled_PH","M1_split_boundary","M2_common_driver","M3_viability_only","M4_observability_only","M5_sensor_artifact","M6_null")
STAGES={"development":64,"validation":128,"confirmatory":256}
BASE={"development":202651000,"validation":202652000,"confirmatory":202653000}

def sig(x): return 1/(1+np.exp(-np.clip(x,-35,35)))
def logit(p): p=np.clip(p,1e-9,1-1e-9); return np.log(p/(1-p))
def corr(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float); ok=np.isfinite(x)&np.isfinite(y); x=x[ok]; y=y[ok]
    return float(np.corrcoef(x,y)[0,1]) if len(x)>=4 and np.std(x)>1e-10 and np.std(y)>1e-10 else float('nan')
def mean_ci(x,rng,B=400):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if not len(x): return (np.nan,np.nan,np.nan)
    z=np.array([np.mean(x[rng.integers(0,len(x),len(x))]) for _ in range(B)])
    return float(np.mean(x)),float(np.quantile(z,.025)),float(np.quantile(z,.975))
def corr_ci(x,y,rng,B=400):
    r=corr(x,y)
    if not np.isfinite(r): return (r,np.nan,np.nan)
    x=np.asarray(x,float); y=np.asarray(y,float); vals=[]
    for _ in range(B):
        q=rng.integers(0,len(x),len(x)); rr=corr(x[q],y[q]);
        if np.isfinite(rr): vals.append(rr)
    return r,float(np.quantile(vals,.025)),float(np.quantile(vals,.975))
def fit_logistic(D,y,n):
    X=np.c_[np.ones(len(D)),D]; b=np.array([3.,-1.4])
    for _ in range(50):
        p=np.clip(sig(X@b),1e-6,1-1e-6); W=n*p*(1-p); z=X@b+(y-n*p)/np.maximum(W,1e-8)
        nb=np.linalg.solve((X.T*W)@X+1e-6*np.eye(2),(X.T*W)@z)
        if np.max(np.abs(nb-b))<1e-8: b=nb; break
        b=nb
    return b

def js_equal_gauss(distance,sigma,rng,m=192):
    d=abs(distance)/max(sigma,1e-8); z=rng.normal(0,1,m); a=-.5*d*d+d*z
    return float(np.mean(math.log(2)-np.logaddexp(0,a)))

@dataclass(frozen=True)
class Cfg:
    shocks:tuple=(0.,.1,.2,.3,.4,.5); tau:float=.80; d_grid:tuple=tuple(np.round(np.linspace(.4,4.6,15),4)); trials:int=40
    baseline:float=.62; floor:float=.08; ceil:float=.95; repair_rate:float=.20; repair_shock:float=.45; repair_T:int=35
    v_gain:float=1.55; z_v_gain:float=.95; o_gain:float=.74; z_o_gain:float=.25; trait_sd:float=.12; split_sd:float=.09
    slope:float=2.35; obs_noise:float=.12; sensor_sd:float=.10; history_gain:float=.34; history_challenge:float=3.15
    sham_v:float=.055; sham_noise:float=.010; bootstrap_B:int=400
    min_dynamic:float=.90; min_repair:float=.80; min_vdrop:float=.10; min_omega:float=.03; min_gamma:float=.60; min_gamma_lcb:float=.30
    min_sham:float=2.; min_lambda:float=1.10; min_lambda_lcb:float=1.02

class Model:
    def __init__(self,c,mode):
        self.c=c; self.mode=mode
        self.C=np.array([[1.,.1,0,0],[0,.85,.18,0],[0,0,.78,.58]]); self.A=np.array([[.74,.04,0,0],[.03,.72,.04,0],[0,.04,.76,.03],[0,0,.03,.79]])
        self.x1=np.array([0,0,-.06,-.07]); self.x2=-self.x1
    def latent(self,seed):
        r=np.random.default_rng(seed); return r.normal(0,self.c.trait_sd),r.normal(),r.normal(0,self.c.split_sd),r.normal(0,self.c.split_sd),abs(r.normal(0,self.c.sensor_sd))
    def boundaries(self,seed,d):
        c=self.c; t,z,sv,so,sens=self.latent(seed); b=np.clip(c.baseline+.18*t,c.floor,c.ceil)
        if self.mode=="M1_split_boundary": return np.clip(b+sv-d,c.floor,c.ceil),np.clip(b+so,c.floor,c.ceil),z,sens,t
        q=np.clip(b-d,c.floor,c.ceil); return q,q,z,sens,t
    def d50(self,seed,d,sham=False):
        c=self.c; bv,bo,z,sens,t=self.boundaries(seed,d); base=3.05+t
        if sham: return base-c.sham_v*d
        if self.mode in ("M0_coupled_PH","M1_split_boundary","M3_viability_only"): return base+c.v_gain*(bv-c.baseline)
        if self.mode=="M2_common_driver": return base+c.z_v_gain*math.tanh(z)
        return base
    def obs(self,seed,d,sham=False):
        c=self.c; bv,bo,z,sens,t=self.boundaries(seed,d); a=.48; s=c.obs_noise
        if sham: s+=c.sham_noise*d
        elif self.mode in ("M0_coupled_PH","M1_split_boundary","M4_observability_only"): a=np.clip(1-c.o_gain*bo,.08,.95)
        elif self.mode=="M2_common_driver": a=np.clip(.45-c.z_o_gain*math.tanh(z),.08,.95)
        elif self.mode=="M5_sensor_artifact": s+=sens
        C=self.C.copy(); C[:,2]*=a; C[:,3]*=a**1.25; Ak=np.eye(4); blocks=[]
        for _ in range(8): blocks.append(C@Ak); Ak=Ak@self.A
        O=np.vstack(blocks); P=np.linalg.inv(np.eye(4)+O.T@O/(s*s)); omega=float(np.trace(P)/4)
        rng=np.random.default_rng(seed+700000+round(d*1000)+(99999 if sham else 0)); js=js_equal_gauss(np.linalg.norm(C@(self.x2-self.x1)),s,rng)
        return omega,js
    def curve(self,seed,d,sham=False):
        c=self.c; D=np.asarray(c.d_grid); p=sig(c.slope*(self.d50(seed,d,sham)-D)); r=np.random.default_rng(seed+1000000+round(d*10000)+(444444 if sham else 0)); y=r.binomial(c.trials,p)
        b=fit_logistic(D,y,np.full(len(D),c.trials)); ds=(logit(c.tau)-b[0])/b[1] if b[1]<-1e-5 else np.nan; ph=y/c.trials
        return float(ds),bool(np.any((ph>.10)&(ph<.90)))
    def repair(self,seed):
        c=self.c; r=np.random.default_rng(seed+3000000); target=np.clip(c.baseline+r.normal(0,.02),c.floor,c.ceil); b=max(c.floor,target-c.repair_shock); e=abs(b-target)
        for _ in range(c.repair_T): b=float(np.clip(b+c.repair_rate*(target-b)+r.normal(0,.003),c.floor,c.ceil))
        return float(1-abs(b-target)/e)

def history(model,stage,N,c):
    n=max(256,4*N); r=np.random.default_rng(BASE[stage]+9000000); h=r.uniform(0,1,n); t=r.normal(0,c.trait_sd,n); b=np.clip(c.baseline+c.history_gain*(h-.5)+.08*t,c.floor,c.ceil)
    if model.mode in ("M0_coupled_PH","M1_split_boundary","M3_viability_only"): d50=3.05+t+c.v_gain*(b-c.baseline)
    elif model.mode=="M2_common_driver": d50=3.05+t+c.z_v_gain*r.normal(0,1,n)
    else: d50=3.05+t
    y=np.clip(sig(c.slope*(d50-c.history_challenge))+r.normal(0,.035,n),0,1); q=r.permutation(n); nt=max(80,int(.35*n)); te=q[:nt]; tr=q[nt:]
    X=np.c_[np.ones(n),h,h*h,h*h*h]; hs=h[r.permutation(n)]; XS=np.c_[np.ones(n),hs,hs*hs,hs*hs*hs]; lam=1e-4
    bt=np.linalg.solve(X[tr].T@X[tr]+lam*np.eye(4),X[tr].T@y[tr]); bs=np.linalg.solve(XS[tr].T@XS[tr]+lam*np.eye(4),XS[tr].T@y[tr]); et=(y[te]-X[te]@bt)**2; es=(y[te]-XS[te]@bs)**2
    L=float(es.mean()/et.mean()); boots=[]
    for _ in range(c.bootstrap_B):
        ii=r.integers(0,len(te),len(te)); boots.append(es[ii].mean()/et[ii].mean())
    boots=np.asarray(boots)
    if model.mode in ("M0_coupled_PH","M1_split_boundary","M3_viability_only"):
        blo=c.baseline+c.history_gain*(.2-.5); bhi=c.baseline+c.history_gain*(.8-.5); total=float(sig(c.slope*((3.05+c.v_gain*(bhi-c.baseline))-c.history_challenge))-sig(c.slope*((3.05+c.v_gain*(blo-c.baseline))-c.history_challenge)))
    else: total=0.
    return L,float(np.quantile(boots,.025)),float(np.quantile(boots,.975)),total,0.

def run_stage(stage,c,out):
    seeds=range(BASE[stage],BASE[stage]+STAGES[stage]); raw=[]; sums=[]
    for mi,mode in enumerate(MODES):
        m=Model(c,mode)
        for seed in seeds:
            rb=m.repair(seed)
            for d in c.shocks:
                ds,dyn=m.curve(seed,d); om,js=m.obs(seed,d); sd,sdyn=m.curve(seed,d,True); so,sjs=m.obs(seed,d,True)
                raw.append([stage,mode,seed,d,ds,dyn,om,js,rb,sd,so,sjs])
        f=pd.DataFrame([x for x in raw if x[1]==mode],columns=['stage','mode','seed','shock','D_star','dynamic','omega','JS','repair','sham_D','sham_O','sham_JS'])
        b=f[f.shock==0].set_index('seed'); x=f[f.shock==max(c.shocks)].set_index('seed'); p=x.join(b,lsuffix='_x',rsuffix='_b')
        v=(p.D_star_b-p.D_star_x)/p.D_star_b; oe=p.omega_b-p.omega_x; je=p.JS_x-p.JS_b; rng=np.random.default_rng(BASE[stage]+mi*100+77)
        vm,vl,vu=mean_ci(v,rng,c.bootstrap_B); om,ol,ou=mean_ci(oe,rng,c.bootstrap_B); jm,jl,ju=mean_ci(je,rng,c.bootstrap_B)
        b0=f[f.shock==0][['seed','D_star','omega']].rename(columns={'D_star':'D0','omega':'O0'}); z=f[f.shock>0].merge(b0,on='seed'); z['dV']=z.D_star-z.D0; z['dO']=z.omega-z.O0; gi,gil,giu=corr_ci(z.dV,z.dO,rng,c.bootstrap_B); go=corr(b.D_star,b.omega)
        EB=np.sqrt(((p.D_star_x-p.D_star_b)/p.D_star_b)**2+((p.omega_x-p.omega_b)/c.min_omega)**2); ES=np.sqrt(((p.sham_D_x-p.sham_D_b)/p.D_star_b)**2+((p.sham_O_x-p.sham_O_b)/c.min_omega)**2); sr=float(np.median(EB/(ES+1e-6)))
        L,Ll,Lu,ht,hd=history(m,stage,STAGES[stage],c); dynamic=float(f.dynamic.mean()); repair=float(f.groupby('seed').repair.first().mean())
        G=[dynamic>=c.min_dynamic,repair>=c.min_repair,vm>=c.min_vdrop and vl>0,om>=c.min_omega and jm>0 and jl>0,np.isfinite(gi) and gi>=c.min_gamma and gil>c.min_gamma_lcb,np.isfinite(sr) and sr>=c.min_sham,L>=c.min_lambda and Ll>c.min_lambda_lcb]
        complete=all(G); decision=('PH_SIGNATURE_POSITIVE' if complete else 'INCONCLUSIVE') if mode==MODES[0] else ('FALSE_POSITIVE' if complete else 'NEGATIVE_CONTROL_REJECTED')
        sums.append([stage,mode,STAGES[stage],decision,complete,dynamic,repair,vm,vl,vu,om,ol,ou,jm,jl,ju,gi,gil,giu,go,sr,L,Ll,Lu,ht,hd,*G])
    cols=['stage','mode','N','decision','all_primary_gates','dynamic_fraction','repair_mean','viability_drop_mean','viability_drop_LCB','viability_drop_UCB','opacity_effect_mean','opacity_effect_LCB','opacity_effect_UCB','JS_effect_mean','JS_effect_LCB','JS_effect_UCB','Gamma_int','Gamma_int_LCB','Gamma_int_UCB','Gamma_observational','sham_specificity_ratio','Lambda_H','Lambda_H_LCB','Lambda_H_UCB','history_total_effect','history_direct_effect_B_matched','G1_dynamic_range','G2_boundary_repair','G3_viability_sensitivity','G4_observability_sensitivity','G5_interventional_coupling','G6_sham_specificity','G7_history_dependence']
    R=pd.DataFrame(raw,columns=['stage','mode','seed','shock','D_star','dynamic','omega','JS','repair','sham_D','sham_O','sham_JS']); S=pd.DataFrame(sums,columns=cols); R.to_csv(out/f'{stage}_seed_shock_results.csv',index=False); S.to_csv(out/f'{stage}_summary.csv',index=False); return S

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',default='results/v0.2.1'); a=ap.parse_args(); out=Path(a.outdir); out.mkdir(parents=True,exist_ok=True); c=Cfg()
    src=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(); freeze={'version':VERSION,'source_sha256':src,'stages':STAGES,'stage_seed_bases':BASE,'modes':MODES,'config':asdict(c)}; freeze['sha256']=hashlib.sha256(json.dumps(freeze,sort_keys=True,separators=(',',':')).encode()).hexdigest(); (out/'config.freeze.json').write_text(json.dumps(freeze,indent=2))
    A=pd.concat([run_stage(s,c,out) for s in STAGES],ignore_index=True); A.to_csv(out/'all_stage_summary.csv',index=False); C=A[A.stage=='confirmatory']; m0=C[C['mode']==MODES[0]].iloc[0]; controls=C[C['mode']!=MODES[0]]; final='PH_SIGNATURE_SUPPORTED' if m0.all_primary_gates and (~controls.all_primary_gates).all() else 'INCONCLUSIVE'
    d={'version':VERSION,'config_sha256':freeze['sha256'],'final_decision':final,'final_stage':'confirmatory','N_confirmatory':256,'M0_decision':m0.decision,'Gate8_negative_control_specificity':bool((~controls.all_primary_gates).all()),'Gate9_independent_confirmatory_holdout':True,'negative_controls':{r['mode']:r['decision'] for _,r in controls.iterrows()},'interpretation':'Synthetic detector validation only; not evidence that PH exists in nature.'}; (out/'decision.json').write_text(json.dumps(d,indent=2)); print(final,freeze['sha256'])
if __name__=='__main__': main()
