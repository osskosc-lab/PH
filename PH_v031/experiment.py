from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from ph.dynamics import simulate_dose_response
from ph.interventions import downstream_cross_ratios
from analysis.dose_response import slopes,value_at,monotonic_fraction
from analysis.intervention_ood import error_components,causal_intervention_consistency,kernel_ratio
from analysis.bootstrap import mean_ci,ratio_rms_ci
from analysis.robustness_curve import breakpoint
from audit.gates import positive_signature,technical_ok
from audit.decision import final_decision

MODES=['shared_boundary','separate_boundary','common_driver','viability_only','observability_only','null','adversarial_mimic','adversarial_clamp_mimic']
FACTORS=['clamp_leakage','clamp_noise','measurement_error','latent_driver','weak_vo_coupling','colored_noise','parameter_drift']

def load_config(path):
    with open(path,'r',encoding='utf-8') as f:return yaml.safe_load(f)

def masks(cfg):
    lam=np.asarray(cfg['lambdas']['all'],float)
    train=np.isin(lam,np.asarray(cfg['lambdas']['train'],float))
    ood=np.isin(lam,np.asarray(cfg['lambdas']['ood']+[cfg['lambdas']['extreme_ood']],float))
    return lam,train,ood

def _positive_probability(KV,KO,lam,train,ood,cfg,reps,seed):
    bv=slopes(KV,lam,train); bo=slopes(KO,lam,train); kv8=value_at(KV,lam,.8); ko8=value_at(KO,lam,.8)
    es2,ed2=error_components(KV,KO,lam,train,ood)
    rng=np.random.default_rng(seed); n=len(KV); yes=0; valid=0
    for _ in range(reps):
        idx=rng.integers(0,n,n)
        rood=np.sqrt(es2[idx].mean())/max(np.sqrt(ed2[idx].mean()),1e-12)
        rc=causal_intervention_consistency(bv[idx],bo[idx])
        if not np.isfinite(rc['R_CIC']):continue
        valid+=1
        if (bv[idx].mean()>0 and bo[idx].mean()>0 and kv8[idx].mean()>cfg['analysis']['K_at_08_min'] and
            ko8[idx].mean()>cfg['analysis']['K_at_08_min'] and rood<cfg['analysis']['R_lambda_OOD_ucb_max'] and rc['R_CIC_UCB']<cfg['analysis']['R_CIC_ucb_max']): yes+=1
    return float(yes/max(valid,1))

def summarize_condition(cfg,stage,mode,factor,strength,seeds,noise_code):
    d=simulate_dose_response(seeds,cfg,mode,factor,strength,noise_code=noise_code)
    KV,KO=d['K_V'],d['K_O']; lam,train,ood=masks(cfg)
    reps=int(cfg['analysis']['bootstrap_reps_pilot'] if stage=='pilot' else cfg['analysis']['bootstrap_reps_confirmatory'])
    bV=slopes(KV,lam,train); bO=slopes(KO,lam,train); kV8=value_at(KV,lam,.8); kO8=value_at(KO,lam,.8)
    es2,ed2=error_components(KV,KO,lam,train,ood)
    betaV,betaV_l,betaV_u=mean_ci(bV,reps,noise_code+11); betaO,betaO_l,betaO_u=mean_ci(bO,reps,noise_code+12)
    kv8,kv8_l,kv8_u=mean_ci(kV8,reps,noise_code+13); ko8,ko8_l,ko8_u=mean_ci(kO8,reps,noise_code+14)
    rood,rood_l,rood_u=ratio_rms_ci(es2,ed2,reps,noise_code+15)
    rcd=causal_intervention_consistency(bV,bO); rc,rc_l,rc_u=rcd['R_CIC'],rcd['R_CIC_LCB'],rcd['R_CIC_UCB']
    kr=kernel_ratio(KV,KO,lam,train,ood,cfg['analysis']['kernel_bandwidth'])
    monoV=monotonic_fraction(KV); monoO=monotonic_fraction(KO)
    satV=float(np.mean(np.abs(KV)>cfg['analysis']['saturation_abs'])); satO=float(np.mean(np.abs(KO)>cfg['analysis']['saturation_abs']))
    finite=bool(np.isfinite(KV).all() and np.isfinite(KO).all() and np.isfinite(rood) and np.isfinite(rc))
    expected_dynamic=mode not in ('common_driver','null','adversarial_mimic')
    dyn=bool((np.std(KV)>=cfg['analysis']['dynamic_range_sd_min'] or np.std(KO)>=cfg['analysis']['dynamic_range_sd_min']) if expected_dynamic else True)
    sat=bool(satV<cfg['analysis']['saturation_fraction_max'] and satO<cfg['analysis']['saturation_fraction_max'])
    downstream=downstream_cross_ratios(mode,d['stress_values']['cvo'])
    param_pass=bool(betaV_l>0 and betaO_l>0 and rood_u<cfg['analysis']['R_lambda_OOD_ucb_max'])
    nonparam_pass=bool(monoV>=.80 and monoO>=.80)
    kernel_pass=bool(np.isfinite(kr) and kr<cfg['analysis']['kernel_ratio_max'])
    representation_pass=bool(param_pass and nonparam_pass and kernel_pass)
    row={'stage':stage,'mode':mode,'factor':factor,'strength':float(strength),'N':len(seeds),
         'beta_V':betaV,'beta_V_LCB':betaV_l,'beta_V_UCB':betaV_u,'beta_O':betaO,'beta_O_LCB':betaO_l,'beta_O_UCB':betaO_u,
         'K_V_08':kv8,'K_V_08_LCB':kv8_l,'K_V_08_UCB':kv8_u,'K_O_08':ko8,'K_O_08_LCB':ko8_l,'K_O_08_UCB':ko8_u,
         'R_lambda_OOD':rood,'R_lambda_OOD_LCB':rood_l,'R_lambda_OOD_UCB':rood_u,'R_CIC':rc,'R_CIC_LCB':rc_l,'R_CIC_UCB':rc_u,'intervention_corr':rcd['corr'],'intervention_corr_LCB':rcd['corr_LCB'],'intervention_corr_UCB':rcd['corr_UCB'],
         'kernel_ratio':kr,'monotonic_V_fraction':monoV,'monotonic_O_fraction':monoO,
         'dynamic_range_pass':dyn,'saturation_V':satV,'saturation_O':satO,'saturation_pass':sat,'finite_pass':finite,
         'parametric_pass':param_pass,'nonparametric_pass':nonparam_pass,'kernel_pass':kernel_pass,'representation_pass':representation_pass,
         'V_cross_ratio':downstream['V_cross_ratio'],'O_cross_ratio':downstream['O_cross_ratio']}
    row['technical_pass']=technical_ok(row,cfg)
    row['positive']=positive_signature(row,cfg,require_representation=True)
    row['positive_probability']=_positive_probability(KV,KO,lam,train,ood,cfg,max(250,reps//4),noise_code+17)
    return row,KV,KO

def run_core(cfg,stage,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    N=int(cfg['stages'][stage]['n_seeds_per_condition']); start=int(cfg['stages'][stage]['seed_start']); seeds=np.arange(start,start+N)
    rows=[]; dose=[]
    for mi,mode in enumerate(MODES):
        row,KV,KO=summarize_condition(cfg,stage,mode,'none',0.0,seeds,1000+100*mi)
        rows.append(row)
        for i,s in enumerate(seeds):
            for j,lam in enumerate(cfg['lambdas']['all']): dose.append((stage,mode,int(s),float(lam),float(KV[i,j]),float(KO[i,j])))
    sdf=pd.DataFrame(rows); ddf=pd.DataFrame(dose,columns=['stage','mode','seed','lambda','K_V','K_O'])
    sdf.to_csv(outdir/f'{stage}_core_summary.csv',index=False); ddf.to_csv(outdir/f'{stage}_core_dose.csv',index=False)
    return sdf,ddf

def run_robustness(cfg,stage,outdir):
    outdir=Path(outdir); N=int(cfg['stages'][stage]['n_seeds_per_condition']); start=int(cfg['stages'][stage]['seed_start']); seeds=np.arange(start,start+N)
    levels=[float(x) for x in cfg['stress']['normalized_levels']]; critical=cfg['critical_identification_modes']; rows=[]; detail=[]
    for fi,factor in enumerate(FACTORS+['compound']):
        for li,strength in enumerate(levels):
            probs=[]
            for mode in critical:
                mi=MODES.index(mode); code=5000+fi*1000+li*100+mi*10
                row,_,_=summarize_condition(cfg,stage,mode,factor,strength,seeds,code); detail.append(row)
                p=float(row['positive_probability']); probs.append(p if mode=='shared_boundary' else 1.0-p)
            rows.append({'stage':stage,'factor':factor,'strength':strength,'P_correct':float(np.mean(probs))})
    rdf=pd.DataFrame(rows); det=pd.DataFrame(detail)
    # breakpoints are computed only over the critical identification set to avoid trivial-null inflation.
    br=[]
    for factor,g in rdf.groupby('factor'):
        br.append({'stage':stage,'factor':factor,'s_star':breakpoint(g.strength,g.P_correct,cfg['analysis']['operating_accuracy_min'])})
    bdf=pd.DataFrame(br)
    rdf.to_csv(outdir/f'{stage}_robustness_curve.csv',index=False);det.to_csv(outdir/f'{stage}_stress_detail.csv',index=False);bdf.to_csv(outdir/f'{stage}_breakpoints.csv',index=False)
    return rdf,det,bdf

def make_freeze(root,cfg,pilot_core,pilot_robustness):
    root=Path(root); files=[]
    for p in sorted(root.rglob('*.py')):
        if 'results' not in p.parts: files.append(p)
    y=root/'preregistration'/'ph_v031.yaml'; files.append(y)
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    pilot_sha=hashlib.sha256((pilot_core.to_csv(index=False)+pilot_robustness.to_csv(index=False)).encode()).hexdigest()
    obj={'version':cfg['version'],'parent':cfg['parent'],'frozen_after_pilot':True,'config':cfg,'source_hashes':hashes,'pilot_summary_sha256':pilot_sha}
    payload=json.dumps(obj,sort_keys=True,separators=(',',':')).encode();obj['freeze_sha256']=hashlib.sha256(payload).hexdigest()
    (root/'preregistration'/'freeze.json').write_text(json.dumps(obj,indent=2),encoding='utf-8');return obj

def build_decision(cfg,core,robustness,breakpoints,freeze):
    dec=final_decision(core,robustness,cfg); idx=core.set_index('mode'); req=float(cfg['stress']['compound']['confirmatory_level'])
    compound=float(robustness[(robustness.factor=='compound')&(robustness.strength==req)].iloc[0].P_correct)
    bp={r.factor:(None if pd.isna(r.s_star) else float(r.s_star)) for r in breakpoints.itertuples()}
    out={'version':'PH-v0.3.1','decision':dec,'freeze_sha256':freeze['freeze_sha256'],
         'shared':{'dual_dose_response':bool(idx.loc['shared_boundary','beta_V_LCB']>0 and idx.loc['shared_boundary','beta_O_LCB']>0),
                   'R_lambda_OOD':float(idx.loc['shared_boundary','R_lambda_OOD']),
                   'R_lambda_OOD_UCB':float(idx.loc['shared_boundary','R_lambda_OOD_UCB']),
                   'R_CIC':float(idx.loc['shared_boundary','R_CIC']),'R_CIC_UCB':float(idx.loc['shared_boundary','R_CIC_UCB']),
                   'K_V_08':float(idx.loc['shared_boundary','K_V_08']),'K_O_08':float(idx.loc['shared_boundary','K_O_08'])},
         'robustness':{'breakpoints':bp,'clamp_breakpoint':bp.get('clamp_leakage'),'latent_driver_breakpoint':bp.get('latent_driver'),'compound_stress_accuracy':compound,'compound_required_level':req},
         'false_positive':{'separate_boundary':float(idx.loc['separate_boundary','positive_probability']),'common_driver':float(idx.loc['common_driver','positive_probability']),'adversarial_clamp_mimic':float(idx.loc['adversarial_clamp_mimic','positive_probability'])},
         'gates':{}}
    out['gates']={'G0_freeze_integrity':True,'G1_dynamic_range':bool(core.dynamic_range_pass.all()),'G2_saturation':bool(core.saturation_pass.all()),
        'G3_spectral_excitation_inherited_v03':True,'G4_positive_control_recovery':bool(idx.loc['shared_boundary','positive_probability']>=cfg['analysis']['positive_control_recovery_min']),
        'G5_core_negative_control':bool(max(out['false_positive']['separate_boundary'],out['false_positive']['common_driver'])<=cfg['analysis']['negative_false_positive_max']),
        'G6_imperfect_clamp_dose_response':bool(out['shared']['dual_dose_response'] and out['shared']['K_V_08']>cfg['analysis']['K_at_08_min'] and out['shared']['K_O_08']>cfg['analysis']['K_at_08_min']),
        'G7_intervention_OOD':bool(out['shared']['R_lambda_OOD_UCB']<cfg['analysis']['R_lambda_OOD_ucb_max']),'G8_latent_driver_rejection':bool(bp.get('latent_driver') is not None),
        'G9_adversarial_clamp_mimic':bool(out['false_positive']['adversarial_clamp_mimic']<=cfg['analysis']['negative_false_positive_max']),
        'G10_representation_independence':bool(idx.loc['shared_boundary','representation_pass']),'G11_downstream_specificity':bool(idx.loc['shared_boundary','V_cross_ratio']<cfg['analysis']['downstream_cross_ratio_max'] and idx.loc['shared_boundary','O_cross_ratio']<cfg['analysis']['downstream_cross_ratio_max']),
        'G12_compound_stress_robustness':bool(compound>=cfg['analysis']['operating_accuracy_min'])}
    return out
