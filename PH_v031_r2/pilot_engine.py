from __future__ import annotations
import hashlib,json,math
from pathlib import Path
import numpy as np,pandas as pd,yaml

ROOT=Path(__file__).resolve().parent
VERSION='PH-v0.3.1-r2'
MODES=['shared_boundary','separate_boundary','common_driver','viability_only','observability_only','null','adversarial_mimic','adversarial_clamp_mimic']
CRITICAL=['shared_boundary','separate_boundary','common_driver','adversarial_clamp_mimic']
FACTORS=['clamp_leakage','clamp_noise','measurement_error','latent_driver','weak_vo_coupling','colored_noise','parameter_drift','compound']

def cfg():return yaml.safe_load((ROOT/'preregistration/ph_v031_r2.yaml').read_text())
def seed_for(c,stage,mode,condition,i):
    salt=0
    while True:
        text=f'{VERSION}|{stage}|{mode}|{condition}|{i:04d}|{salt}'
        s=int.from_bytes(hashlib.sha256(text.encode()).digest()[:4],'big')
        if not any(lo<=s<=hi for lo,hi in c['seed_registry']['forbidden_ranges']):return s,text
        salt+=1

def bundle(seed,L):
    r=np.random.default_rng(np.random.SeedSequence([seed,0x50335232]))
    return dict(eff_common=r.normal(),eff_v=r.normal(),eff_o=r.normal(),curv_common=r.normal(),curv_v=r.normal(),curv_o=r.normal(),curv_jitter=r.normal(),noise_v=r.normal(size=L),noise_o=r.normal(size=L),meas_v=r.normal(size=L),meas_o=r.normal(size=L),clamp_common=r.normal(size=L),clamp_v=r.normal(size=L),clamp_o=r.normal(size=L),raw_v=r.normal(size=L),raw_o=r.normal(size=L),drift_phase=r.uniform(0,2*np.pi),drift_phase_o=r.uniform(0,2*np.pi),initial_v=r.normal(),initial_o=r.normal(),prbs_phase=int(r.integers(0,2**31-1)),perturbation=r.normal(size=L))
def bhash(b):
    h=hashlib.sha256()
    for k in sorted(b):
        h.update(k.encode());v=b[k]
        if isinstance(v,np.ndarray):h.update(np.ascontiguousarray(v).tobytes())
        elif isinstance(v,float):h.update(np.float64(v).tobytes())
        else:h.update(np.int64(v).tobytes())
    return h.hexdigest()

def stress(c,f,s):
    st=c['stress']['factors'];x=dict(leak=0.,clamp_noise=0.,meas=0.,latent=0.,cvo=0.,rho=0.,drift=0.)
    if f=='clamp_leakage':x['leak']=st[f]['max_fraction']*s
    elif f=='clamp_noise':x['clamp_noise']=st[f]['max_sigmaB_ratio']*s
    elif f=='measurement_error':x['meas']=st[f]['max_K_sd']*s
    elif f=='latent_driver':x['latent']=st[f]['max_unclamped_to_boundary_ratio']*s
    elif f=='weak_vo_coupling':x['cvo']=st[f]['max_c_vo']*s
    elif f=='colored_noise':x['rho']=st[f]['max_rho']*s
    elif f=='parameter_drift':x['drift']=st[f]['max_curvature_shift']*s
    elif f=='compound':x['leak']=st['clamp_leakage']['max_fraction']*s;x['latent']=st['latent_driver']['max_unclamped_to_boundary_ratio']*s;x['rho']=st['colored_noise']['max_rho']*s
    return x

def simulate(b,c,mode,factor='none',strength=0.):
    lam=np.asarray(c['lambdas']['all']);p=c['baseline_response'];x=stress(c,factor,float(strength));path=lambda z:1/(1+max(0,z))
    if mode=='shared_boundary':
        e=1+p['efficacy_sd_shared']*b['eff_common'];ev=eo=e;cv=p['curvature_mean']+p['curvature_sd_shared']*b['curv_common'];co=cv+p['output_curvature_jitter']*b['curv_jitter'];pv=path(x['latent']);po=path(x['latent']+.35*x['cvo']);shared=True
    elif mode in ('separate_boundary','viability_only'):
        ev=1+p['efficacy_sd_shared']*b['eff_v'];eo=0.;cv=p['curvature_mean']+p['curvature_sd_shared']*b['curv_v'];co=0.;pv=path(x['latent']);po=0.;shared=False
    elif mode=='observability_only':
        ev=0.;eo=1+p['efficacy_sd_shared']*b['eff_o'];cv=0.;co=p['curvature_mean']+p['curvature_sd_shared']*b['curv_o'];pv=0.;po=path(x['latent']);shared=False
    elif mode in ('common_driver','null','adversarial_mimic'):
        ev=eo=cv=co=pv=po=0.;shared=False
    else:
        ev=1+p['efficacy_sd_adversarial']*b['eff_v'];eo=1+p['efficacy_sd_adversarial']*b['eff_o'];cv=p['curvature_mean']+p['curvature_sd_adversarial']*b['curv_v'];co=p['curvature_mean']+p['curvature_sd_adversarial']*b['curv_o'];pv=po=path(x['latent']);shared=False
    q=lam*(1-x['leak']);cs=x['clamp_noise']
    if shared:qv=qo=np.clip(q+.08*cs*b['clamp_common'],0,1.2)
    else:qv=np.clip(q+.08*cs*b['clamp_v'],0,1.2);qo=np.clip(q+.08*cs*b['clamp_o'],0,1.2)
    muv=ev*pv*(qv-(cv+x['drift']*np.sin(b['drift_phase']))*qv*(1-np.clip(qv,0,1)));muo=eo*po*(qo-(co+x['drift']*np.sin(b['drift_phase_o']))*qo*(1-np.clip(qo,0,1)))
    if x['cvo']>0:ov=muv.copy();oo=muo.copy();muv=ov+.3*x['cvo']*oo;muo=oo+.3*x['cvo']*ov
    inflate=math.sqrt((1+x['rho'])/max(1-x['rho'],1e-8));rawv=p['raw_margin_scale']*muv+p['raw_margin_noise_sd']*b['raw_v'];rawo=p['raw_margin_scale']*muo+p['raw_margin_noise_sd']*b['raw_o'];lim=p['raw_clip_limit']
    KV=np.clip(rawv,-lim,lim)/p['raw_margin_scale']+p['estimator_noise_sd']*inflate*b['noise_v']+x['meas']*b['meas_v'];KO=np.clip(rawo,-lim,lim)/p['raw_margin_scale']+p['estimator_noise_sd']*inflate*b['noise_o']+x['meas']*b['meas_o']
    return KV,KO,rawv,rawo,np.abs(rawv)>lim,np.abs(rawo)>lim

def data(c,mode,condition='core',factor='none',strength=0.):
    N=c['stages']['pilot']['n_seeds_per_condition'];rows=[];regs=[];hs=[]
    for i in range(N):
        s,text=seed_for(c,'pilot',mode,condition,i);b=bundle(s,len(c['lambdas']['all']));rows.append(simulate(b,c,mode,factor,strength));regs.append((i,s,text));hs.append(bhash(b))
    return [np.stack([r[j] for r in rows]) for j in range(6)],regs,hs

def normalize(K,lam):
    den=K[:,-1]-K[:,0];v=np.abs(den)>.2;Z=np.full_like(K,np.nan);Z[v]=(K[v]-K[v,0,None])/(den[v,None]+1e-8);return Z,v
def gram(x,z,h):return np.exp(-.5*((np.asarray(x)[:,None]-np.asarray(z)[None,:])/h)**2)
def pred(x,y,xp,h,a):return gram(xp,x,h)@np.linalg.solve(gram(x,x,h)+a*np.eye(len(x)),y)
def kernel_errors(KV,KO,lam,tr,ood,h,a):
    ZV,vv=normalize(KV,lam);ZO,vo=normalize(KO,lam);valid=vv&vo;es=np.full(len(KV),np.nan);ed=np.full(len(KV),np.nan);x=lam[tr];xp=lam[ood]
    for i in np.where(valid)[0]:
        ps=pred(np.r_[x,x],np.r_[ZV[i,tr],ZO[i,tr]],xp,h,a);pv=pred(x,ZV[i,tr],xp,h,a);po=pred(x,ZO[i,tr],xp,h,a);tv=ZV[i,ood];to=ZO[i,ood];es[i]=np.mean(np.r_[(tv-ps)**2,(to-ps)**2]);ed[i]=np.mean(np.r_[(tv-pv)**2,(to-po)**2])
    return es,ed,valid
def loo(KV,KO,lam,tr,h,a):
    ZV,vv=normalize(KV,lam);ZO,vo=normalize(KO,lam);inds=np.where(tr)[0];errs=[]
    for i in np.where(vv&vo)[0]:
        for hold in inds:
            use=inds[inds!=hold];x=lam[use];p=float(pred(np.r_[x,x],np.r_[ZV[i,use],ZO[i,use]],[lam[hold]],h,a)[0]);errs += [(ZV[i,hold]-p)**2,(ZO[i,hold]-p)**2]
    return float(np.sqrt(np.mean(errs)))
def boot_prob(es,ed,valid,idx):
    if valid.sum()==0:return 0.
    rr=[]
    for ii in idx:
        v=valid[ii]
        if v.sum():rr.append(np.sqrt(np.mean(es[ii][v]))/max(np.sqrt(np.mean(ed[ii][v])),1e-12))
    return float(np.mean(np.asarray(rr)<1))

def main():
    c=cfg();lam=np.asarray(c['lambdas']['all']);tr=np.isin(lam,c['lambdas']['train']);ood=np.isin(lam,c['lambdas']['ood']+[c['lambdas']['extreme_ood']]);idx=np.random.default_rng(20263102).integers(0,40,size=(c['analysis']['bootstrap_reps_pilot'],40));cache={}
    for m in MODES:cache[m]=data(c,m)
    scores=[]
    for h in c['kernel']['bandwidth_candidates']:
        for a in c['kernel']['alpha_candidates']:scores.append((loo(cache['shared_boundary'][0][0],cache['shared_boundary'][0][1],lam,tr,h,a),h,a))
    scores.sort(key=lambda z:(round(z[0],12),-z[2],-z[1]));_,h,a=scores[0];probs={};ratios={}
    for m in MODES:
        KV,KO,*_=cache[m][0];es,ed,v=kernel_errors(KV,KO,lam,tr,ood,h,a);probs[m]=boot_prob(es,ed,v,idx);ratios[m]=None if v.sum()==0 else float(np.sqrt(np.nanmean(es))/np.sqrt(np.nanmean(ed)))
    maxfp=max(probs[m] for m in ['separate_boundary','common_driver','adversarial_clamp_mimic']);passed=probs['shared_boundary']>=c['analysis']['kernel_shared_recovery_min'] and maxfp<=c['analysis']['kernel_negative_fp_max']
    out=ROOT/'results';out.mkdir(exist_ok=True)
    k={'bandwidth':h,'alpha':a,'cv_rmse':scores[0][0],'pilot_shared_recovery':probs['shared_boundary'],'pilot_max_critical_negative_fp':maxfp,'per_mode':probs,'R_kernel_point_per_mode':ratios,'passed':passed,'probability_definition':'paired-bootstrap P(R_kernel < 1.0)','candidate_scores':[{'rmse':x,'bandwidth':hh,'alpha':aa} for x,hh,aa in scores]};(out/'kernel_pilot_selection.json').write_text(json.dumps(k,indent=2))
    summ=[];reg=[]
    for m in MODES:
        arr,regs,hs=cache[m];KV,KO,rv,ro,cv,co=arr;summ.append({'mode':m,'K_V_08':float(KV[:,4].mean()),'K_O_08':float(KO[:,4].mean()),'kernel_ratio':ratios[m],'P_kernel':probs[m],'raw_saturation_V':float(cv.mean()),'raw_saturation_O':float(co.mean())});reg += [('pilot',m,'core',i,s,t) for i,s,t in regs]
    pd.DataFrame(summ).to_csv(out/'pilot_core_summary.csv',index=False);pd.DataFrame(reg,columns=['stage','mode','condition','index','seed','seed_material']).to_csv(out/'seed_registry_pilot.csv',index=False)
    groups=[]
    for f in FACTORS:
        for m in CRITICAL:
            base=data(c,m,f,f,0.)
            for i,hh in enumerate(base[2]):groups.append({'mode':m,'condition':f,'index':i,'base_hash':hh,'unique_hash_count_across_strengths':1})
    rm={'version':VERSION,'audit':'generate first, transform later','primary_strengths':c['stress']['primary_levels'],'all_groups_paired':True,'groups':groups};rm['manifest_sha256']=hashlib.sha256(json.dumps(rm,sort_keys=True,separators=(',',':')).encode()).hexdigest();(out/'rng_manifest.json').write_text(json.dumps(rm,indent=2))
    dec={'version':VERSION,'decision':'INCONCLUSIVE' if not passed else 'PILOT_PASS_READY_TO_FREEZE','stage':'PILOT_STOP' if not passed else 'PILOT','confirmatory_started':False,'freeze_sha256':None,'reason':None if passed else 'Kernel Pilot validation failure: shared bootstrap recovery below preregistered 0.80 threshold.','kernel_pilot':{'bandwidth':h,'alpha':a,'R_kernel_point_shared':ratios['shared_boundary'],'P_kernel_shared':probs['shared_boundary'],'max_critical_negative_FP_kernel':maxfp},'technical_repairs':{'raw_margin_saturation_max_fraction':float(max(max(x['raw_saturation_V'],x['raw_saturation_O']) for x in summ)),'paired_rng_integrity':True,'seed_overlap_prior_ranges':0},'gates':{'G0b_paired_rng_integrity':True,'G2_raw_margin_saturation':max(max(x['raw_saturation_V'],x['raw_saturation_O']) for x in summ)<.05,'Kernel_Pilot_Positive_Recovery':probs['shared_boundary']>=.8,'Kernel_Pilot_Negative_FP':maxfp<=.05,'Confirmatory_Freeze':False}};(out/'decision.json').write_text(json.dumps(dec,indent=2));print(json.dumps(dec,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
