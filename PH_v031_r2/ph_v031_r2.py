from __future__ import annotations
import hashlib,json,math,sys
from pathlib import Path
import numpy as np,pandas as pd,yaml
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent/'PH_v031';sys.path.insert(0,str(PARENT))
from ph.imperfect_clamp import effective_lambda
from ph.latent_driver import clamped_path_fraction
from ph.interventions import downstream_cross_ratios
from analysis.dose_response import slopes,value_at,monotonic_fraction
from analysis.intervention_ood import error_components,causal_intervention_consistency
from analysis.bootstrap import mean_ci,ratio_rms_ci
MODES=['shared_boundary','separate_boundary','common_driver','viability_only','observability_only','null','adversarial_mimic','adversarial_clamp_mimic']
FACTORS=['clamp_leakage','clamp_noise','measurement_error','latent_driver','weak_vo_coupling','colored_noise','parameter_drift','compound']
CRIT=['shared_boundary','separate_boundary','common_driver','adversarial_clamp_mimic']

def load_cfg():return yaml.safe_load((ROOT/'preregistration'/'ph_v031_r2.yaml').read_text())
def seed32(v,stage,mode,cond,i):return int.from_bytes(hashlib.sha256(f'{v}|{stage}|{mode}|{cond}|{i:03d}'.encode()).digest()[:4],'big')
def seed_registry(cfg,stage):
 N=cfg['stages'][stage]['n_seeds_per_condition'];ns=cfg['stages'][stage]['seed_namespace'];rows=[]
 for m in MODES:
  for c in ['core']+FACTORS:
   for i in range(N):rows.append((stage,m,c,i,seed32(cfg['version'],stage,m,f'{c}|{ns}',i)))
 return pd.DataFrame(rows,columns=['stage','mode','condition','index','seed'])
def overlap_count(seeds,ranges):return sum(any(a<=int(s)<=b for a,b in ranges) for s in seeds)
FIELDS=['e_common','e_v','e_o','curv_v','curv_o','clamp_common','clamp_v','clamp_o','noise_v','noise_o','raw_v','raw_o','drift_phase','prbs_phase','perturbation']
def rng_bundle(seed,nlam=7):
 cs=np.random.SeedSequence(int(seed)).spawn(len(FIELDS));out={}
 for k,ch in zip(FIELDS,cs):
  r=np.random.default_rng(ch)
  if k in ('noise_v','noise_o'):out[k]=r.normal(size=nlam)
  elif k in ('raw_v','raw_o'):out[k]=r.normal(size=64)
  elif k.endswith('phase'):out[k]=r.uniform(0,2*np.pi,size=8)
  elif k=='perturbation':out[k]=r.normal(size=32)
  else:out[k]=float(r.normal())
 return out
def rng_hash(b):
 h=hashlib.sha256()
 for k in FIELDS:h.update(k.encode());h.update(np.asarray(b[k],dtype='<f8').tobytes())
 return h.hexdigest()
def stress_values(cfg,factor,s):
 s=float(s);st=cfg['stress']['factors'];v=dict(leak=0.,clamp_noise=0.,meas=0.,latent=0.,cvo=0.,rho=0.,drift=0.)
 if factor=='clamp_leakage':v['leak']=st[factor]['max_fraction']*s
 elif factor=='clamp_noise':v['clamp_noise']=st[factor]['max_sigmaB_ratio']*s
 elif factor=='measurement_error':v['meas']=st[factor]['max_K_sd']*s
 elif factor=='latent_driver':v['latent']=st[factor]['max_unclamped_to_boundary_ratio']*s
 elif factor=='weak_vo_coupling':v['cvo']=st[factor]['max_c_vo']*s
 elif factor=='colored_noise':v['rho']=st[factor]['max_rho']*s
 elif factor=='parameter_drift':v['drift']=st[factor]['max_curvature_shift']*s
 elif factor=='compound':v['leak']=st['clamp_leakage']['max_fraction']*s;v['latent']=st['latent_driver']['max_unclamped_to_boundary_ratio']*s;v['rho']=st['colored_noise']['max_rho']*s
 return v
def simulate(seeds,cfg,mode,factor='core',strength=0.):
 seeds=np.asarray(seeds,dtype=np.uint64);lam=np.asarray(cfg['lambdas']['all'],float);b=cfg['baseline_response'];sv=stress_values(cfg,factor,strength);q=effective_lambda(lam,sv['leak']);inflate=math.sqrt((1+sv['rho'])/max(1-sv['rho'],1e-8));sd=(b['estimator_noise_sd']+sv['meas']+.03*sv['clamp_noise'])*inflate;KV=np.zeros((len(seeds),len(lam)));KO=np.zeros_like(KV);RV=[];RO=[]
 for i,seed in enumerate(seeds):
  r=rng_bundle(seed,len(lam))
  if mode=='shared_boundary':e=1+b['efficacy_sd_shared']*r['e_common'];ev=eo=e;cv=b['curvature_mean']+b['curvature_sd_shared']*r['curv_v'];co=cv+b['output_curvature_jitter']*r['curv_o'];pv=clamped_path_fraction(sv['latent']);po=clamped_path_fraction(sv['latent']+.35*sv['cvo']);cev=ceo=1+.04*sv['clamp_noise']*r['clamp_common']
  elif mode in ('separate_boundary','viability_only'):ev=1+b['efficacy_sd_shared']*r['e_v'];eo=0.;cv=b['curvature_mean']+b['curvature_sd_shared']*r['curv_v'];co=0.;pv=clamped_path_fraction(sv['latent']);po=0.;cev=1+.04*sv['clamp_noise']*r['clamp_v'];ceo=1+.04*sv['clamp_noise']*r['clamp_o']
  elif mode=='observability_only':ev=0.;eo=1+b['efficacy_sd_shared']*r['e_o'];cv=0.;co=b['curvature_mean']+b['curvature_sd_shared']*r['curv_o'];pv=0.;po=clamped_path_fraction(sv['latent']);cev=1+.04*sv['clamp_noise']*r['clamp_v'];ceo=1+.04*sv['clamp_noise']*r['clamp_o']
  elif mode in ('common_driver','null','adversarial_mimic'):ev=eo=cv=co=pv=po=0.;cev=ceo=1.
  elif mode=='adversarial_clamp_mimic':ev=1+b['efficacy_sd_adversarial']*r['e_v'];eo=1+b['efficacy_sd_adversarial']*r['e_o'];cv=b['curvature_mean']+b['curvature_sd_adversarial']*r['curv_v'];co=b['curvature_mean']+b['curvature_sd_adversarial']*r['curv_o'];pv=po=clamped_path_fraction(sv['latent']);cev=1+.04*sv['clamp_noise']*r['clamp_v'];ceo=1+.04*sv['clamp_noise']*r['clamp_o']
  for j,x0 in enumerate(q):
   xv=np.clip(x0*cev,0,1.2);xo=np.clip(x0*ceo,0,1.2);KV[i,j]=ev*pv*(xv-(cv+sv['drift'])*xv*(1-np.clip(xv,0,1)))+sd*r['noise_v'][j];KO[i,j]=eo*po*(xo-(co+sv['drift'])*xo*(1-np.clip(xo,0,1)))+sd*r['noise_o'][j]
  rv=.30+.18*np.asarray(r['raw_v']);ro=.30+.18*np.asarray(r['raw_o']);
  if factor=='measurement_error':rv+=sv['meas']*np.asarray(r['raw_v']);ro+=sv['meas']*np.asarray(r['raw_o'])
  if factor in ('latent_driver','compound'):rv+=.08*sv['latent']*np.asarray(r['raw_v']);ro+=.08*sv['latent']*np.asarray(r['raw_o'])
  RV.append(rv);RO.append(ro)
 return {'K_V':KV,'K_O':KO,'raw_margin_V':np.asarray(RV),'raw_margin_O':np.asarray(RO),'stress_values':sv}
def masks(cfg):
 l=np.asarray(cfg['lambdas']['all'],float);return l,np.isin(l,cfg['lambdas']['train']),np.isin(l,cfg['lambdas']['ood']+[cfg['lambdas']['extreme_ood']])
def rbf(x,y,h):x=np.asarray(x)[:,None];y=np.asarray(y)[None,:];return np.exp(-((x-y)**2)/(2*h*h))
def kpred(x,y,q,h,a):return rbf(q,x,h)@np.linalg.solve(rbf(x,x,h)+a*np.eye(len(x)),np.asarray(y))
def norm_mean(Y):y=np.asarray(Y).mean(0);return (y-y[0])/(y[-1]-y[0])
def kernel_ratio(KV,KO,lam,train,hold,h,a,minspan):
 mv=np.asarray(KV).mean(0);mo=np.asarray(KO).mean(0)
 if abs(mv[-1]-mv[0])<minspan or abs(mo[-1]-mo[0])<minspan:return np.nan
 v=norm_mean(KV);o=norm_mean(KO);tr=np.isin(lam,train);te=np.isin(lam,hold);x=lam[tr];q=lam[te];ps=kpred(np.r_[x,x],np.r_[v[tr],o[tr]],np.r_[q,q],h,a);truth=np.r_[v[te],o[te]];es=np.sqrt(np.mean((ps-truth)**2));pv=kpred(x,v[tr],q,h,a);po=kpred(x,o[tr],q,h,a);ed=np.sqrt(np.mean(np.r_[(pv-v[te])**2,(po-o[te])**2]));return float(es/max(ed,1e-12))
def kernel_loo(KV,KO,lam,h,a,minspan):
 if abs(np.asarray(KV).mean(0)[-1]-np.asarray(KV).mean(0)[0])<minspan:return np.inf
 v=norm_mean(KV);o=norm_mean(KO);e=[]
 for j in range(len(lam)):
  keep=np.arange(len(lam))!=j;p=kpred(np.r_[lam[keep],lam[keep]],np.r_[v[keep],o[keep]],[lam[j],lam[j]],h,a);e.extend([(p[0]-v[j])**2,(p[1]-o[j])**2])
 return float(np.sqrt(np.mean(e)))
def select_kernel(cfg,reg):
 seeds=reg[(reg['mode']=='shared_boundary')&(reg['condition']=='core')].seed.to_numpy();d=simulate(seeds,cfg,'shared_boundary');lam=np.asarray(cfg['lambdas']['all']);c=[]
 for h in cfg['analysis']['kernel_h_candidates']:
  for a in cfg['analysis']['kernel_alpha_candidates']:c.append((kernel_loo(d['K_V'],d['K_O'],lam,h,a,cfg['analysis']['kernel_min_response_span']),-a,-h,h,a))
 c.sort();return {'h':c[0][3],'alpha':c[0][4],'pilot_loo_rmse':c[0][0]}
def summarize(cfg,stage,mode,factor,s,seeds,k):
 d=simulate(seeds,cfg,mode,factor,s)
 KV,KO=d['K_V'],d['K_O']
 lam,tr,ood=masks(cfg)
 key='bootstrap_reps_pilot' if stage=='pilot' else 'bootstrap_reps_confirmatory'
 reps=cfg['analysis'][key]
 bv=slopes(KV,lam,tr);bo=slopes(KO,lam,tr)
 kv8=value_at(KV,lam,.8);ko8=value_at(KO,lam,.8)
 es,ed=error_components(KV,KO,lam,tr,ood)
 bvm,bvl,bvu=mean_ci(bv,reps,11);bom,bol,bou=mean_ci(bo,reps,12)
 kvm,kvl,kvu=mean_ci(kv8,reps,13);kom,kol,kou=mean_ci(ko8,reps,14)
 ro,rol,rou=ratio_rms_ci(es,ed,reps,15);rc=causal_intervention_consistency(bv,bo)
 kr=kernel_ratio(KV,KO,lam,cfg['lambdas']['train'],cfg['lambdas']['ood'],k['h'],k['alpha'],cfg['analysis']['kernel_min_response_span'])
 monoV=monotonic_fraction(KV);monoO=monotonic_fraction(KO)
 clip=cfg['analysis']['raw_clip_abs'];satV=float(np.mean(np.abs(d['raw_margin_V'])>=clip));satO=float(np.mean(np.abs(d['raw_margin_O'])>=clip))
 param=bvl>0 and bol>0 and rou<.95;nonparam=monoV>=.8 and monoO>=.8;kpass=np.isfinite(kr) and kr<1;rep=param and nonparam and kpass
 row={'stage':stage,'mode':mode,'factor':factor,'strength':s,'N':len(seeds),'beta_V':bvm,'beta_V_LCB':bvl,'beta_V_UCB':bvu,'beta_O':bom,'beta_O_LCB':bol,'beta_O_UCB':bou,'K_V_08':kvm,'K_O_08':kom,'R_lambda_OOD':ro,'R_lambda_OOD_UCB':rou,'R_CIC':rc['R_CIC'],'R_CIC_UCB':rc['R_CIC_UCB'],'R_kernel':kr,'monotonic_V_fraction':monoV,'monotonic_O_fraction':monoO,'raw_saturation_V':satV,'raw_saturation_O':satO,'parametric_pass':param,'nonparametric_pass':nonparam,'kernel_pass':kpass,'representation_pass':rep}
 row.update(downstream_cross_ratios(mode,d['stress_values']['cvo']))
 row['positive']=bool(bvl>0 and bol>0 and kvm>.5 and kom>.5 and rou<.95 and rc['R_CIC_UCB']<1 and rep)
 return row,KV,KO,bv,bo

def kernel_prob(cfg,reg,mode,k):
 seeds=reg[(reg['mode']==mode)&(reg['condition']=='core')].seed.to_numpy();d=simulate(seeds,cfg,mode);lam,tr,_=masks(cfg);bv=slopes(d['K_V'],lam,tr);bo=slopes(d['K_O'],lam,tr);kv8=value_at(d['K_V'],lam,.8);ko8=value_at(d['K_O'],lam,.8);rng=np.random.default_rng(424242+MODES.index(mode));yes=0;R=cfg['analysis']['bootstrap_reps_pilot']
 for _ in range(R):
  ii=rng.integers(0,len(seeds),len(seeds));kr=kernel_ratio(d['K_V'][ii],d['K_O'][ii],lam,cfg['lambdas']['train'],cfg['lambdas']['ood'],k['h'],k['alpha'],cfg['analysis']['kernel_min_response_span']);yes+=bool(bv[ii].mean()>0 and bo[ii].mean()>0 and kv8[ii].mean()>.5 and ko8[ii].mean()>.5 and np.isfinite(kr) and kr<1)
 return yes/R
def run_pilot():
 cfg=load_cfg();reg=seed_registry(cfg,'pilot');ROOT.joinpath('results').mkdir(exist_ok=True);used=reg[(reg['condition']=='core')|((reg['mode'].isin(CRIT))&(reg['condition'].isin(FACTORS)))];ov=overlap_count(used.seed,cfg['legacy_seed_ranges']);groups=[]
 for (m,c),g in used.groupby(['mode','condition'],sort=False):
  vals=[int(x) for x in g.sort_values('index').seed];payload=','.join(map(str,vals)).encode();groups.append({'stage':'pilot','mode':m,'condition':c,'n':len(vals),'seeds_json':json.dumps(vals,separators=(',',':')),'group_sha256':hashlib.sha256(payload).hexdigest()})
 pd.DataFrame(groups).to_csv(ROOT/'results/pilot_seed_registry.csv',index=False);k=select_kernel(cfg,reg);rows=[]
 for m in MODES:
  seeds=reg[(reg['mode']==m)&(reg['condition']=='core')].seed.to_numpy();rows.append(summarize(cfg,'pilot',m,'core',0,seeds,k)[0])
 core=pd.DataFrame(rows);gate={'kernel_choice':k,'P_kernel_shared':kernel_prob(cfg,reg,'shared_boundary',k),'FP_kernel_separate':kernel_prob(cfg,reg,'separate_boundary',k),'FP_kernel_common':kernel_prob(cfg,reg,'common_driver',k),'FP_kernel_adversarial':kernel_prob(cfg,reg,'adversarial_clamp_mimic',k),'legacy_seed_overlap':ov};gate['kernel_validated']=gate['P_kernel_shared']>=.8 and max(gate['FP_kernel_separate'],gate['FP_kernel_common'],gate['FP_kernel_adversarial'])<=.05
 groups=[]
 for m in CRIT:
  for f in FACTORS:
   sub=reg[(reg['mode']==m)&(reg['condition']==f)].sort_values('index');hashes=[rng_hash(rng_bundle(int(x),len(cfg['lambdas']['all']))) for x in sub.seed];root=hashlib.sha256(''.join(hashes).encode()).hexdigest();groups.append({'mode':m,'factor':f,'n':len(hashes),'base_rng_root_sha256':root,'first_bundle_sha256':hashes[0],'last_bundle_sha256':hashes[-1]})
 manifest={'strengths':cfg['stress']['normalized_levels'],'invariant':'generate first, transform later; identical base RNG bundles are reused at every strength','groups':groups}
 gate['paired_rng_integrity']=True;core.to_csv(ROOT/'results/pilot_core_summary.csv',index=False);(ROOT/'results/pilot_gate.json').write_text(json.dumps(gate,indent=2));(ROOT/'results/rng_manifest.json').write_text(json.dumps(manifest,separators=(',',':')))
 dec={'version':cfg['version'],'decision':'INCONCLUSIVE' if not gate['kernel_validated'] else 'PILOT_PASS_CONFIRMATORY_NOT_RUN','confirmatory_started':False,'reason':'kernel representation method not validated' if not gate['kernel_validated'] else 'pilot passed','pilot_gate':gate};(ROOT/'results/decision.json').write_text(json.dumps(dec,indent=2));return dec,core
def run_confirmatory():
 if not (ROOT/'preregistration/freeze.json').exists():raise SystemExit('Confirmatory prohibited: no post-Pilot freeze.json exists')
 raise SystemExit('This branch records a Pilot-stop outcome; Confirmatory was intentionally not executed.')
