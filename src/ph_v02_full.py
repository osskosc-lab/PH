#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Tuple
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

VERSION='PH-v0.2-toy-0.1'

def sigmoid(x): return 1/(1+np.exp(-x))
def safe_corr(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    if x.size<3 or np.std(x)<1e-12 or np.std(y)<1e-12: return float('nan')
    return float(np.corrcoef(x,y)[0,1])
def ridge_fit_predict(xtr,ytr,xte,lam):
    return xte @ np.linalg.solve(xtr.T@xtr + lam*np.eye(xtr.shape[1]), xtr.T@ytr)

def sha256_json(obj):
    p=json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(p).hexdigest()

@dataclass(frozen=True)
class PHConfig:
    seed:int=20260811; n_state:int=4; n_obs:int=3
    process_noise:float=.015; boundary_noise:float=.004; observation_noise:float=.08
    boundary_floor:float=.05; boundary_ceil:float=.98; boundary_baseline:float=.55
    boundary_repair_rate:float=.20; boundary_history_gain:float=3.2; boundary_target_bias:float=.15
    history_decay:float=.92; history_input_gain:float=.08
    feedback_base:float=.10; feedback_boundary_gain:float=.34
    fail_radius:float=3.; recovery_radius:float=.30; recovery_horizon:int=55
    viability_trials:int=80; viability_tau:float=.80
    disturbance_grid_min:float=0.; disturbance_grid_max:float=4.; disturbance_grid_n:int=21
    observability_horizon:int=8; prior_variance:float=1.; opacity_strength:float=.92
    boundary_shocks:Tuple[float,...]=(0.,.1,.2,.3,.4,.5)
    repair_shock:float=.45; repair_horizon:int=35; repair_fraction_required:float=.80
    history_samples:int=700; history_warmup:int=10; history_test_fraction:float=.35
    history_disturbance:float=1.85; ridge_lambda:float=1e-3
    min_viability_drop_fraction:float=.10; min_opacity_drop_absolute:float=.04
    min_coupling_corr:float=.60; min_history_ratio:float=1.10
    coupling_gray_low:float=.30; history_gray_low:float=1.02

class PHToySystem:
    MODES=('coupled','viability_only','observability_only','null')
    def __init__(self,cfg,mode='coupled'):
        if mode not in self.MODES: raise ValueError(mode)
        self.cfg=cfg; self.mode=mode
        self.A=np.array([[.965,.020,0,0],[.015,.955,.018,0],[0,.018,.970,.020],[0,0,.018,.975]],float)
        self.K=np.diag([1,.9,.85,1.05])
        self.dp=np.array([.60,.75,1.,1.20],float); self.dp/=np.linalg.norm(self.dp)
        self.C0=np.array([[1,.15,0,0],[0,.85,.20,0],[0,0,.80,.55]],float)
    def boundary_target(self,h):
        c=self.cfg; raw=sigmoid(c.boundary_target_bias+c.boundary_history_gain*(h-.5))
        return float(np.clip(.25+.65*raw,c.boundary_floor,c.boundary_ceil))
    def update_history(self,h,d):
        c=self.cfg; return float(np.clip(c.history_decay*h+c.history_input_gain*math.tanh(max(0,d)/2),0,1))
    def update_boundary(self,b,h,rng):
        c=self.cfg; x=b+c.boundary_repair_rate*(self.boundary_target(h)-b)+rng.normal(0,c.boundary_noise)
        return float(np.clip(x,c.boundary_floor,c.boundary_ceil))
    def feedback_gain(self,b):
        c=self.cfg; be=b if self.mode in ('coupled','viability_only') else c.boundary_baseline
        return c.feedback_base+c.feedback_boundary_gain*be
    def acl(self,b): return self.A-self.feedback_gain(b)*self.K
    def step(self,x,b,dv,rng):
        noise=rng.normal(0,self.cfg.process_noise,self.cfg.n_state)
        return self.acl(b)@x - .018*np.tanh(x)*np.abs(x) + dv + noise
    def obs_matrix(self,b):
        c=self.cfg; be=b if self.mode in ('coupled','observability_only') else c.boundary_baseline
        a=max(.02,1-c.opacity_strength*be); C=self.C0.copy(); C[:,2]*=a; C[:,3]*=a**1.35; return C
    def observability_opacity(self,b):
        c=self.cfg; A=self.acl(b); C=self.obs_matrix(b); blocks=[]; Ak=np.eye(c.n_state)
        for _ in range(c.observability_horizon): blocks.append(C@Ak); Ak=Ak@A
        O=np.vstack(blocks); p0i=np.eye(c.n_state)/c.prior_variance; ri=np.eye(O.shape[0])/(c.observation_noise**2)
        P=np.linalg.inv(p0i+O.T@ri@O); omega=float(np.trace(P)/(c.n_state*c.prior_variance))
        s=np.linalg.svd(O,compute_uv=False); p=s/max(np.sum(s),1e-15); er=float(np.exp(-np.sum(p*np.log(p+1e-15))))
        return dict(omega=omega,effective_rank=er,sigma_min=float(s.min()),condition_number=float(s.max()/max(s.min(),1e-15)))
    def episode(self,amp,b,h,seed):
        c=self.cfg; rng=np.random.default_rng(seed); x=np.zeros(c.n_state)
        direction=self.dp+rng.normal(0,.08,c.n_state); direction/=max(np.linalg.norm(direction),1e-12); impulse=amp*direction; failed=False
        for t in range(c.recovery_horizon):
            x=self.step(x,b,impulse if t==0 else np.zeros(c.n_state),rng)
            failed |= np.linalg.norm(x)>c.fail_radius
            h=self.update_history(h,amp if t==0 else 0); b=self.update_boundary(b,h,rng)
        return (not failed) and np.linalg.norm(x)<=c.recovery_radius
    def viability(self,b,h,seed_offset=0):
        c=self.cfg; amps=np.linspace(c.disturbance_grid_min,c.disturbance_grid_max,c.disturbance_grid_n); rows=[]
        for i,a in enumerate(amps):
            n=sum(self.episode(float(a),b,h,c.seed+seed_offset+i*10000+j) for j in range(c.viability_trials))
            rows.append((float(a),n/c.viability_trials))
        df=pd.DataFrame(rows,columns=['disturbance','p_recovery']); ok=df[df.p_recovery>=c.viability_tau]
        return (float(ok.disturbance.max()) if len(ok) else 0.),df
    def repair_audit(self,seed):
        c=self.cfg; rng=np.random.default_rng(seed); h=.5; target=self.boundary_target(h); b=max(c.boundary_floor,target-c.repair_shock); start=b; rows=[]
        for t in range(c.repair_horizon+1):
            rows.append((t,b,target,abs(b-target)))
            if t<c.repair_horizon: b=self.update_boundary(b,h,rng)
        df=pd.DataFrame(rows,columns=['t','boundary','target','abs_error']); frac=1-df.iloc[-1].abs_error/max(abs(start-target),1e-12)
        return float(frac),df
    def history_audit(self,seed):
        c=self.cfg; rng=np.random.default_rng(seed); n=c.history_samples; hs=rng.uniform(0,1,n); ys=np.zeros(n); ba=np.zeros(n)
        for i,h0 in enumerate(hs):
            b=c.boundary_baseline; h=float(h0); lr=np.random.default_rng(seed+100000+i)
            for _ in range(c.history_warmup): h=self.update_history(h,0); b=self.update_boundary(b,h,lr)
            ba[i]=b; ys[i]=self.episode(c.history_disturbance,b,h,seed+200000+i)
        idx=rng.permutation(n); nt=round(c.history_test_fraction*n); te=idx[:nt]; tr=idx[nt:]
        X=np.c_[np.ones(n),hs,hs**2,hs**3]; sh=hs[rng.permutation(n)]; XS=np.c_[np.ones(n),sh,sh**2,sh**3]
        pt=ridge_fit_predict(X[tr],ys[tr],X[te],c.ridge_lambda); ps=ridge_fit_predict(XS[tr],ys[tr],XS[te],c.ridge_lambda)
        et=float(np.mean((ys[te]-pt)**2)); es=float(np.mean((ys[te]-ps)**2))
        return dict(E_true=et,E_shuffled=es,Lambda_H=es/max(et,1e-12),success_rate=float(ys.mean()),data=pd.DataFrame({'history_init':hs,'boundary_after_warmup':ba,'recovered':ys.astype(int)}))

def run_mode(c,mode,out):
    s=PHToySystem(c,mode); h=.5; b0=s.boundary_target(h); repair,rep=s.repair_audit(c.seed+11); rows=[]; curves=[]
    for j,shock in enumerate(c.boundary_shocks):
        b=float(np.clip(b0-shock,c.boundary_floor,c.boundary_ceil)); ds,curve=s.viability(b,h,500000*(j+1)); ob=s.observability_opacity(b)
        rows.append(dict(mode=mode,shock=shock,boundary=b,D_star=ds,**ob)); curve['mode']=mode; curve['shock']=shock; curve['boundary']=b; curves.append(curve)
    scan=pd.DataFrame(rows); gamma=safe_corr(scan.D_star,scan.omega); base=scan.iloc[0]; strong=scan.iloc[-1]
    vdrop=float(base.D_star-strong.D_star)/max(float(base.D_star),1e-12); odrop=float(base.omega-strong.omega); hist=s.history_audit(c.seed+21)
    crit=dict(boundary_self_repair=repair>=c.repair_fraction_required,viability_boundary_effect=vdrop>=c.min_viability_drop_fraction,observability_boundary_effect=odrop>=c.min_opacity_drop_absolute,vo_coupling=(not math.isnan(gamma)) and gamma>=c.min_coupling_corr,history_dependence=hist['Lambda_H']>=c.min_history_ratio)
    hard=(crit['viability_boundary_effect'] and crit['observability_boundary_effect'] and (math.isnan(gamma) or gamma<c.coupling_gray_low)) or (crit['boundary_self_repair'] and hist['Lambda_H']<c.history_gray_low)
    decision='SUPPORTED' if all(crit.values()) else ('FALSIFIED' if hard else 'INCONCLUSIVE')
    summary=dict(version=VERSION,mode=mode,decision=decision,baseline_boundary=b0,repair_fraction=repair,D_star_baseline=float(base.D_star),D_star_max_shock=float(strong.D_star),viability_drop_fraction=vdrop,omega_baseline=float(base.omega),omega_max_shock=float(strong.omega),opacity_drop_absolute=odrop,Gamma_VO=gamma,E_true_history=hist['E_true'],E_shuffled_history=hist['E_shuffled'],Lambda_H=hist['Lambda_H'],history_success_rate=hist['success_rate'],**{f'criterion_{k}':v for k,v in crit.items()})
    scan.to_csv(out/f'boundary_shock_scan_{mode}.csv',index=False); pd.concat(curves).to_csv(out/f'viability_curves_{mode}.csv',index=False); rep.assign(mode=mode).to_csv(out/f'boundary_repair_{mode}.csv',index=False); hist['data'].assign(mode=mode).to_csv(out/f'history_test_{mode}.csv',index=False)
    return summary,scan,rep

def main():
    c=PHConfig(); out=Path('ph_v02_results'); out.mkdir(exist_ok=True); freeze={'version':VERSION,'config':asdict(c)}; freeze['sha256']=sha256_json(freeze); json.dump(freeze,open(out/'config.freeze.json','w'),indent=2)
    sums=[]; scans=[]; reps=[]
    for m in PHToySystem.MODES:
        sm,sc,rp=run_mode(c,m,out); sums.append(sm); scans.append(sc); rp=rp.copy(); rp['mode']=m; reps.append(rp); print(m,sm['decision'])
    sdf=pd.DataFrame(sums); sdf.to_csv(out/'summary.csv',index=False)
    plt.figure(figsize=(9,6));
    for m,g in pd.concat(scans).groupby('mode'): plt.plot(g.omega,g.D_star,marker='o',label=m)
    plt.xlabel('Observability opacity Ω'); plt.ylabel('Viability horizon D*'); plt.legend(); plt.tight_layout(); plt.savefig(out/'horizon_scan.png',dpi=180); plt.close()
    plt.figure(figsize=(9,6));
    for m,g in pd.concat(reps).groupby('mode'): plt.plot(g.t,g.boundary,label=m)
    plt.xlabel('Time'); plt.ylabel('Boundary B_t'); plt.legend(); plt.tight_layout(); plt.savefig(out/'boundary_repair.png',dpi=180); plt.close()
    dec={'version':VERSION,'config_sha256':freeze['sha256'],'primary_mode':'coupled','primary_decision':sdf.loc[sdf['mode']=='coupled','decision'].iloc[0],'negative_controls':{r['mode']:r['decision'] for _,r in sdf.iterrows() if r['mode']!='coupled'}}
    json.dump(dec,open(out/'decision.json','w'),indent=2)

if __name__=='__main__': main()
