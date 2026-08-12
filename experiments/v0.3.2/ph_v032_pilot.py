from __future__ import annotations
import argparse, csv, hashlib, json, math
from dataclasses import dataclass
from pathlib import Path
import numpy as np

VERSION = "PH-v0.3.2"
MODES = ["M0","M1","M2","M3","M4","M5","M6","M7","M8","M9","M10"]
TRAIN_CONDITIONS = ["multisine","impulse","PRBS"]
OOD_CONDITIONS = ["chirp","unseen_frequencies","unseen_amplitudes","burst","reversed_sequence"]
EXTRA_CONDITIONS = ["dual_timescale"]
ALL_CONDITIONS = TRAIN_CONDITIONS + OOD_CONDITIONS + EXTRA_CONDITIONS
N_DEFAULT, T = 60, 320
TUNE, TRAIN, EVAL = range(0,20), range(20,40), range(40,60)
TARGET_FREQS = np.array([0.03125,0.0625,0.125])
EPS=1e-9

def h32(token): return int.from_bytes(hashlib.sha256(token.encode()).digest()[:4],"big")
def audit_seed(mode,condition,index): return h32(f"{VERSION}|pilot|{mode}|{condition}|{index}")
def pair_seed(condition,index): return h32(f"{VERSION}|pilot|paired|{condition}|{index}")
def rng_for(*parts): return np.random.default_rng(h32("|".join(map(str,parts))))

def intervention(condition,index):
    t=np.arange(T); r=np.random.default_rng(pair_seed(condition,index))
    if condition=="multisine": u=.65*np.sin(2*np.pi*.03125*t)+.45*np.sin(2*np.pi*.0625*t+.4)+.30*np.sin(2*np.pi*.125*t+1.0)
    elif condition=="dual_timescale": u=.75*np.sin(2*np.pi*.025*t)+.35*np.sin(2*np.pi*.16*t+.7)
    elif condition=="impulse":
        u=np.zeros(T); u[40:45]=1.7; u[150:153]=-1.2; u[245:249]=1.4
    elif condition=="PRBS": u=.9*np.repeat(r.choice([-1.,1.],size=math.ceil(T/8)),8)[:T]
    elif condition=="chirp":
        f0,f1=.015,.18; phase=2*np.pi*(f0*t+(f1-f0)/(2*T)*t*t); u=.8*np.sin(phase)
    elif condition=="unseen_frequencies": u=.65*np.sin(2*np.pi*.046875*t+.2)+.45*np.sin(2*np.pi*.09375*t+.9)
    elif condition=="unseen_amplitudes": u=1.35*(.65*np.sin(2*np.pi*.03125*t)+.45*np.sin(2*np.pi*.0625*t+.4))
    elif condition=="burst":
        u=np.zeros(T)
        for start in (50,135,225):
            w=np.arange(36); u[start:start+36]=1.1*np.sin(2*np.pi*.08*w)
    elif condition=="reversed_sequence": u=.9*np.repeat(r.choice([-1.,1.],size=math.ceil(T/10)),10)[:T][::-1].copy()
    else: raise ValueError(condition)
    return u.astype(float)

@dataclass(frozen=True)
class MimicParams:
    av: float; ao: float; gv: float; go: float
M10_GRID=[MimicParams(av,ao,gv,go) for av in (.76,.82,.88) for ao in (.74,.81,.87) for gv in (.30,.36) for go in (.28,.34)]

def _noise(pair,tag,scale=.04): return rng_for(VERSION,"noise",pair,tag).normal(0,scale,T)

def simulate(mode,condition,index,m10=None):
    u=intervention(condition,index); ps=pair_seed(condition,index)
    n0=_noise(ps,"shared",.045); nv=_noise(ps,"v",.04); no=_noise(ps,"o",.04); nc=_noise(ps,"common",.05)
    B=np.zeros(T); V=np.zeros(T); O=np.zeros(T); Bv=np.zeros(T); Bo=np.zeros(T); C=np.zeros(T)
    sat=np.tanh
    for t in range(1,T):
        ut=u[t-1]
        if mode=="M0":
            B[t]=.84*B[t-1]+.38*ut-.045*B[t-1]**3+n0[t]
            V[t]=.72*V[t-1]+.34*sat(B[t])+.025*B[t-1]+.018*nv[t]
            O[t]=.69*O[t-1]+.31*sat(B[t])+.035*B[t-1]+.018*no[t]
        elif mode=="M1":
            Bv[t]=.78*Bv[t-1]+.37*ut+nv[t]; Bo[t]=.90*Bo[t-1]+.31*ut+no[t]
            V[t]=.73*V[t-1]+.34*sat(Bv[t]); O[t]=.66*O[t-1]+.31*sat(Bo[t])
        elif mode=="M2":
            C[t]=.91*C[t-1]+nc[t]; V[t]=.75*V[t-1]+.28*C[t]+.12*ut+nv[t]; O[t]=.72*O[t-1]+.25*C[t]+.10*ut+no[t]
        elif mode=="M3":
            Bv[t]=.84*Bv[t-1]+.38*ut+nv[t]; V[t]=.72*V[t-1]+.34*sat(Bv[t]); O[t]=.76*O[t-1]+no[t]
        elif mode=="M4":
            Bo[t]=.84*Bo[t-1]+.38*ut+no[t]; V[t]=.76*V[t-1]+nv[t]; O[t]=.69*O[t-1]+.31*sat(Bo[t])
        elif mode=="M5": V[t]=.78*V[t-1]+nv[t]; O[t]=.76*O[t-1]+no[t]
        elif mode=="M6": V[t]=.80*V[t-1]+nv[t]+.16*ut; O[t]=.78*O[t-1]+no[t]+.15*ut
        elif mode=="M7":
            Bv[t]=.55*Bv[t-1]+.48*ut+nv[t]; Bo[t]=.52*Bo[t-1]+.46*ut+no[t]
            V[t]=.76*V[t-1]+.30*sat(Bv[t]); O[t]=.73*O[t-1]+.29*sat(Bo[t])
        elif mode=="M8":
            Bv[t]=.81*Bv[t-1]+.39*ut+nv[t]; Bo[t]=.79*Bo[t-1]+.37*ut+no[t]
            V[t]=.72*V[t-1]+.33*sat(Bv[t]); O[t]=.70*O[t-1]+.31*sat(Bo[t])
        elif mode=="M9":
            Bv[t]=.835*Bv[t-1]+.38*ut+nv[t]; Bo[t]=.83*Bo[t-1]+.375*ut+no[t]
            V[t]=.72*V[t-1]+.335*sat(Bv[t]); O[t]=.695*O[t-1]+.305*sat(Bo[t])
        elif mode=="M10":
            p=m10 or MimicParams(.82,.81,.36,.34)
            Bv[t]=p.av*Bv[t-1]+p.gv*ut-.04*Bv[t-1]**3+nv[t]
            Bo[t]=p.ao*Bo[t-1]+p.go*ut-.04*Bo[t-1]**3+no[t]
            V[t]=.72*V[t-1]+.34*sat(Bv[t])+.025*Bv[t-1]; O[t]=.69*O[t-1]+.31*sat(Bo[t])+.035*Bo[t-1]
        else: raise ValueError(mode)
    return u,V,O

def complex_transfer(u,y,f):
    t=np.arange(len(u)); e=np.exp(-2j*np.pi*f*t); H=np.dot(y,e)/(np.dot(u,e)+1e-8)
    return abs(H),np.angle(H)

def lag_regress_residual(u,y,lags=10):
    n=len(u)-lags; X=np.column_stack([u[lags-k:len(u)-k] for k in range(lags+1)]); X=np.column_stack([np.ones(n),X]); yy=y[lags:]
    return yy-X@np.linalg.lstsq(X,yy,rcond=None)[0]

def recovery_proxy(y):
    y=y-np.mean(y)
    if np.std(y)<1e-8:return 0.
    ac=np.correlate(y,y,mode="full")[len(y)-1:]; ac=ac/(ac[0]+EPS); hit=np.where(ac<math.exp(-1))[0]
    return float(hit[0] if len(hit) else min(40,len(y)-1))/40.

def asymmetry(u,y):
    q=np.quantile(np.abs(u),.65); pos=y[u>q]; neg=y[u<-q]
    return 0. if len(pos)<3 or len(neg)<3 else float(abs(pos.mean()+neg.mean())/(np.std(y)+EPS))

def hysteresis(u,y):
    du=np.diff(u,prepend=u[0]); mid=np.abs(u)<np.quantile(np.abs(u),.7); a=y[(du>0)&mid]; d=y[(du<0)&mid]
    return 0. if len(a)<3 or len(d)<3 else float((a.mean()-d.mean())/(np.std(y)+EPS))

def features(u,V,O):
    vals=[]; names=[]
    for f in TARGET_FREQS:
        for lab,y in (("V",V),("O",O)):
            g,p=complex_transfer(u,y,f); vals += [np.log1p(g),math.sin(p),math.cos(p)]; names += [f"gain_{lab}_{f:.5f}",f"phase_sin_{lab}_{f:.5f}",f"phase_cos_{lab}_{f:.5f}"]
    for lag in (0,1,2,4,8):
        us=u if lag==0 else u[:-lag]
        for lab,y in (("V",V),("O",O)):
            yy=y if lag==0 else y[lag:]; c=0. if np.std(us)<EPS or np.std(yy)<EPS else float(np.corrcoef(us,yy)[0,1])
            vals.append(c); names.append(f"h_{lab}_lag{lag}")
    for lab,y in (("V",V),("O",O)): vals.append(recovery_proxy(y)); names.append(f"tau_{lab}")
    rv=lag_regress_residual(u,V); ro=lag_regress_residual(u,O); rc=0. if np.std(rv)<EPS or np.std(ro)<EPS else float(np.corrcoef(rv,ro)[0,1])
    vals.append(rc); names.append("cross_transfer_residual_corr")
    for lab,y in (("V",V),("O",O)):
        vals += [asymmetry(u,y),hysteresis(u,y)]; names += [f"asym_{lab}",f"hyst_{lab}"]
    return np.nan_to_num(np.array(vals,float),nan=0.,posinf=20.,neginf=-20.),names

def raw_row(mode,condition,index,m10):
    u,V,O=simulate(mode,condition,index,m10); return features(u,V,O)

def optimize_m10():
    m0=[]
    for c in TRAIN_CONDITIONS:
        for i in TUNE: m0.append(raw_row("M0",c,i,None)[0])
    target=np.mean(m0,axis=0); scale=np.std(m0,axis=0)+.15; best=None
    for p in M10_GRID:
        arr=[]
        for c in TRAIN_CONDITIONS:
            for i in TUNE: arr.append(raw_row("M10",c,i,p)[0])
        score=float(np.mean(((np.mean(arr,axis=0)-target)/scale)**2))
        if best is None or score<best[0]: best=(score,p)
    return best

def build_dataset(m10):
    rows=[]; X=[]; names=None
    for mode in MODES:
        for c in ALL_CONDITIONS:
            for i in range(N_DEFAULT):
                f,names=raw_row(mode,c,i,m10); X.append(f); rows.append((mode,c,i,audit_seed(mode,c,i),pair_seed(c,i)))
    return np.vstack(X),rows,names

def split_mask(rows,indices,conditions):
    ii,cc=set(indices),set(conditions); return np.array([(i in ii and c in cc) for _,c,i,_,_ in rows])
def fit_standard(X):
    mu=X.mean(0); sd=X.std(0); return mu,np.where(sd<1e-6,1.,sd)

class Centroid:
    def fit(self,X,y): self.a=X[y==0].mean(0); self.b=X[y==1].mean(0); return self
    def predict(self,X): return (np.sum((X-self.b)**2,1)<np.sum((X-self.a)**2,1)).astype(int)
class Ridge:
    def fit(self,X,y):
        Xa=np.column_stack([np.ones(len(X)),X]); yy=2*y-1; reg=np.eye(Xa.shape[1])*.35; reg[0,0]=0; self.w=np.linalg.solve(Xa.T@Xa+reg,Xa.T@yy); return self
    def predict(self,X): return (np.column_stack([np.ones(len(X)),X])@self.w>0).astype(int)
class Logistic:
    def fit(self,X,y):
        Xa=np.column_stack([np.ones(len(X)),X]); w=np.zeros(Xa.shape[1])
        for _ in range(350):
            z=np.clip(Xa@w,-25,25); p=1/(1+np.exp(-z)); grad=Xa.T@(p-y)/len(y); grad[1:]+=.01*w[1:]; w-=.16*grad
        self.w=w; return self
    def predict(self,X): return (np.column_stack([np.ones(len(X)),X])@self.w>0).astype(int)
class StumpEnsemble:
    def fit(self,X,y):
        cand=[]
        for j in range(X.shape[1]):
            for q in (.25,.5,.75):
                thr=float(np.quantile(X[:,j],q))
                for sign in (1,-1):
                    pred=((sign*(X[:,j]-thr))>0).astype(int); cand.append((np.mean(pred!=y),j,thr,sign))
        self.stumps=sorted(cand,key=lambda z:z[0])[:24]; return self
    def predict(self,X):
        votes=np.zeros(len(X))
        for err,j,thr,sign in self.stumps: votes+=max(.01,.5-err)*(2*((sign*(X[:,j]-thr)>0).astype(float))-1)
        return (votes>0).astype(int)
class KNN:
    def fit(self,X,y): self.X=X.copy(); self.y=y.copy(); return self
    def predict(self,X):
        out=[]
        for z in X:
            d=np.sum((self.X-z)**2,1); k=np.argpartition(d,min(4,len(d)-1))[:5]; out.append(int(np.mean(self.y[k])>=.5))
        return np.array(out)
CLASSIFIERS={"logistic":Logistic,"ridge":Ridge,"capacity_limited_tree_ensemble":StumpEnsemble,"nearest_centroid":Centroid,"nonparametric_distance":KNN}

def mode_rates(pred,rows):
    out={}
    for mode in MODES:
        k=np.array([r[0]==mode for r in rows]);
        if k.any(): out[mode]=float(np.mean(pred[k]))
    return out

def run_pilot(outdir):
    outdir.mkdir(parents=True,exist_ok=True); opt_score,m10=optimize_m10(); X,rows,feature_names=build_dataset(m10)
    tr=split_mask(rows,TRAIN,TRAIN_CONDITIONS); ev=split_mask(rows,EVAL,TRAIN_CONDITIONS); y=np.array([1 if r[0]=="M0" else 0 for r in rows])
    mu,sd=fit_standard(X[tr]); Z=(X-mu)/sd; ev_rows=[r for r,m in zip(rows,ev) if m]; reps={}
    for name,Cls in CLASSIFIERS.items(): reps[name]=mode_rates(Cls().fit(Z[tr],y[tr]).predict(Z[ev]),ev_rows)
    primary=reps["logistic"]; audit=[r[3] for r in rows]; unique_ok=len(audit)==len(set(audit)); pair_map={}; paired_ok=True
    for mode,c,i,aseed,pseed in rows:
        key=(c,i)
        if key in pair_map and pair_map[key]!=pseed: paired_ok=False
        pair_map[key]=pseed
    psel=ev & np.array([r[0] in ("M0","M10") for r in rows]); stds=np.std(X[psel],axis=0)
    powers=[float(np.var(intervention(c,i))) for c in TRAIN_CONDITIONS+EXTRA_CONDITIONS for i in EVAL]
    votes=sum((m.get("M0",0)>=.70 and m.get("M10",1)<=.15 and m.get("M0",0)>m.get("M10",1)) for m in reps.values())
    gate={
      "G0":bool(unique_ok and paired_ok),
      "G1":bool(np.isfinite(X).all() and np.all(stds>1e-5) and np.all(stds<50)),
      "G2":bool(min(powers)>0.02),
      "G3":bool(primary.get("M0",0)>=.80),
      "G4":bool(primary.get("M10",1)<=.05),
      "G5":bool(all(primary.get(m,1)<=.05 for m in ("M1","M2","M5"))),
      "G6":bool(votes>=3),
      "G7":bool(np.isfinite(X).all() and X.shape[1]==len(feature_names) and len(feature_names)>=20)
    }
    failed=[k for k,v in gate.items() if not v]; decision="PILOT_PASS_FREEZE_ALLOWED" if not failed else "STOP"
    result={"version":VERSION,"decision":decision,"failed_gates":failed,"gates":gate,"primary_representation":"logistic","primary_eval_rates":primary,"representations":reps,"m10_optimization":{"objective":opt_score,"params":m10.__dict__,"grid_size":len(M10_GRID),"split":"indices 0-19 only; train interventions only"},"classifier_split":"indices 20-39; train interventions only","gate_split":"indices 40-59; train interventions only","feature_count":len(feature_names),"feature_names":feature_names,"dynamic_range":{"min_std":float(stds.min()),"max_std":float(stds.max())},"excitation":{"min_variance":float(min(powers))},"seed_integrity":{"audit_seed_unique":unique_ok,"paired_rng":paired_ok,"legacy_overlap":0},"rule":"Any Pilot gate failure => STOP; changes require v0.3.2-r1 and fresh Pilot."}
    (outdir/"pilot_result.json").write_text(json.dumps(result,indent=2)+"\n"); (outdir/"m10_frozen_from_pilot_tuning.json").write_text(json.dumps(m10.__dict__,indent=2)+"\n"); (outdir/"standardization.json").write_text(json.dumps({"mean":mu.tolist(),"std":sd.tolist(),"features":feature_names})+"\n")
    with (outdir/"representation_confusion.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["representation"]+MODES)
        for name,m in reps.items(): w.writerow([name]+[m.get(md,"") for md in MODES])
    print(json.dumps(result,indent=2)); return 0 if decision=="PILOT_PASS_FREEZE_ALLOWED" else 2

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--outdir",default="artifacts/pilot"); args=ap.parse_args(); raise SystemExit(run_pilot(Path(args.outdir)))
if __name__=="__main__": main()
