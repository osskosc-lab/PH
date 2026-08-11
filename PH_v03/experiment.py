from __future__ import annotations
import json, hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import yaml
from ph.stimuli import multisine,prbs,impulse,unseen_frequency,unseen_amplitude,chirp
from ph.dynamics import simulate
from ph.interventions import boundary_clamp_pair,downstream_specificity
from ph.horizons import margin_audit
from spectral.transfer import spectral_gain,transfer_at
from spectral.coherence import ensemble_coherence
from spectral.leakage import leakage_fraction,min_registered_power
from spectral.impulse import dominant_pole_from_mean_impulse
from spectral.parametric import fit_shared_factor
from models import shared_boundary as shared_model
from models import separate_boundary as separate_model
from audit.bootstrap import mean_ci

MODES=['shared_boundary','separate_boundary','common_driver','viability_only','observability_only','null','adversarial_mimic']

def load_config(path):
    with open(path,'r',encoding='utf-8') as f:return yaml.safe_load(f)

def _ci_fields(prefix,x,reps,seed):
    m,l,u=mean_ci(x,reps,seed);return {prefix:m,prefix+'_LCB':l,prefix+'_UCB':u}

def residual_cross_coherence(U,V,O,burn,freqs):
    ua=U[:,burn:];va=V[:,burn:];oa=O[:,burn:]
    FU=np.fft.rfft(ua,axis=1);FV=np.fft.rfft(va,axis=1);FO=np.fft.rfft(oa,axis=1);fg=np.fft.rfftfreq(ua.shape[1])
    vals=[]
    for f in freqs[:3]:
        j=int(np.argmin(abs(fg-f)));u=FU[:,j];v=FV[:,j];o=FO[:,j]
        hv=np.sum(np.conj(u)*v)/(np.sum(np.abs(u)**2)+1e-15);ho=np.sum(np.conj(u)*o)/(np.sum(np.abs(u)**2)+1e-15)
        rv=v-hv*u;ro=o-ho*u
        c=np.abs(np.mean(np.conj(rv)*ro))**2/((np.mean(np.abs(rv)**2)*np.mean(np.abs(ro)**2))+1e-15)
        vals.append(float(np.clip(c,0,1)))
    return float(np.mean(vals))

def model_ratios(Utrain,train_sims,Uood,ood_sims,cfg):
    N=Utrain[0].shape[0];burn=cfg['time']['burn_in'];a=cfg['analysis'];out=np.zeros(N)
    for i in range(N):
        tr=[(Utrain[k][i],train_sims[k]['M_V'][i],train_sims[k]['M_O'][i]) for k in range(3)]
        te=[(Uood[k][i],ood_sims[k]['M_V'][i],ood_sims[k]['M_O'][i]) for k in range(3)]
        sm=shared_model.fit(tr,burn,a['fit_stride'],a['ridge_lambda']);dm=separate_model.fit(tr,burn,a['fit_stride'],a['ridge_lambda'])
        es=shared_model.rmse(sm,te,burn);ed=separate_model.rmse(dm,te,burn);out[i]=es/max(ed,1e-12)
    return out

def run_stage(cfg,stage,outdir):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    N=int(cfg['stages'][stage]['n_seeds_per_mode']);start=int(cfg['stages'][stage]['seed_start']);seeds=np.arange(start,start+N,dtype=int)
    T=cfg['time']['T'];burn=cfg['time']['burn_in'];s=cfg['stimuli'];freqs=np.asarray(s['train_multisine_frequencies'],float);a=cfg['analysis']
    U_ms,phases=multisine(seeds,T,burn,freqs,s['train_amplitude'],code=11)
    U_pr=prbs(seeds,T,burn,s['train_amplitude'],s['prbs_block'],code=23)
    U_im=impulse(seeds,T,burn,s['impulse_amplitude'])
    U_uf=unseen_frequency(seeds,T,burn,np.asarray(s['ood_frequencies'],float),s['ood_amplitude'],code=31)
    U_ch=chirp(seeds,T,burn,s['chirp_f0'],s['chirp_f1'],s['ood_amplitude'],code=41)
    U_ua=unseen_amplitude(seeds,T,burn,freqs,s['unseen_amplitude'],code=37)
    Utrain=[U_ms,U_pr,U_im];Uood=[U_uf,U_ch,U_ua]
    input_leak=leakage_fraction(U_ms,burn,freqs);input_power=min_registered_power(U_ms,burn,freqs)
    phase_df=pd.DataFrame(phases,columns=[f'phase_{f:.8f}' for f in freqs]);phase_df.insert(0,'seed',seeds);phase_df.to_csv(outdir/f'{stage}_multisine_phases.csv',index=False)
    rows=[]; per_seed_frames=[]
    for mi,mode in enumerate(MODES):
        free_ms,clamp_ms=boundary_clamp_pair(U_ms,seeds,cfg,mode,noise_code=1000+mi*100)
        sim_pr=simulate(U_pr,seeds,cfg,mode,False,noise_code=1100+mi*100)
        sim_im=simulate(U_im,seeds,cfg,mode,False,noise_code=1200+mi*100)
        sim_uf=simulate(U_uf,seeds,cfg,mode,False,noise_code=1300+mi*100)
        sim_ch=simulate(U_ch,seeds,cfg,mode,False,noise_code=1400+mi*100)
        sim_ua=simulate(U_ua,seeds,cfg,mode,False,noise_code=1500+mi*100)
        audit=margin_audit(free_ms,burn,a['saturation_abs'])
        gv_free=spectral_gain(U_ms,free_ms['M_V'],burn,freqs);go_free=spectral_gain(U_ms,free_ms['M_O'],burn,freqs)
        gv_clamp=spectral_gain(U_ms,clamp_ms['M_V'],burn,freqs);go_clamp=spectral_gain(U_ms,clamp_ms['M_O'],burn,freqs)
        KV=1-gv_clamp/(gv_free+1e-12);KO=1-go_clamp/(go_free+1e-12)
        ds=downstream_specificity(seeds,cfg,mode)
        R=model_ratios(Utrain,[free_ms,sim_pr,sim_im],Uood,[sim_uf,sim_ch,sim_ua],cfg)
        _,cohV=ensemble_coherence(U_ms,free_ms['M_V'],burn,freqs);_,cohO=ensemble_coherence(U_ms,free_ms['M_O'],burn,freqs)
        _,HV=transfer_at(U_ms,free_ms['M_V'],burn,freqs);_,HO=transfer_at(U_ms,free_ms['M_O'],burn,freqs)
        hpV=np.mean(HV,axis=0);hpO=np.mean(HO,axis=0);param=fit_shared_factor(freqs,hpV,hpO)
        npV=dominant_pole_from_mean_impulse(sim_im['M_V'],burn);npO=dominant_pole_from_mean_impulse(sim_im['M_O'],burn)
        resid_coh=residual_cross_coherence(U_ms,free_ms['M_V'],free_ms['M_O'],burn,freqs)
        rep_pass=bool(np.isfinite(npV) and np.isfinite(npO) and abs(npV-param['rho_B'])<a['representation_rho_tolerance'] and abs(npO-param['rho_B'])<a['representation_rho_tolerance'] and resid_coh>=a['representation_min_lowfreq_residual_coherence'])
        per_positive=(KV>.30)&(KO>.30)&(R<a['ood_ratio_ucb_max'])&(ds['V_cross_ratio']<a['downstream_cross_ratio_max'])&(ds['O_cross_ratio']<a['downstream_cross_ratio_max'])
        df=pd.DataFrame({'stage':stage,'mode':mode,'seed':seeds,'K_V':KV,'K_O':KO,'R_OOD':R,'V_cross_ratio':ds['V_cross_ratio'],'O_cross_ratio':ds['O_cross_ratio'],'sd_V':audit['sd_V'],'sd_O':audit['sd_O'],'sat_V':audit['sat_V'],'sat_O':audit['sat_O'],'input_leakage':input_leak,'min_input_power':input_power,'PH_like_seed':per_positive.astype(int)})
        per_seed_frames.append(df)
        row={'stage':stage,'mode':mode,'N':N,'positive_seed_rate':float(np.mean(per_positive)),
             'dynamic_range_pass':bool(np.mean((audit['sd_V']>a['margin_sd_min'])&(audit['sd_O']>a['margin_sd_min']))>=.95),
             'saturation_pass':bool(np.mean((audit['sat_V']<a['saturation_fraction_max'])&(audit['sat_O']<a['saturation_fraction_max']))>=.95),
             'spectral_excitation_pass':bool(np.all(input_power>a['spectral_power_min'])),
             'leakage_pass':bool(np.all(input_leak<a['leakage_max'])),
             'coherence_V_mean':float(np.mean(cohV)),'coherence_O_mean':float(np.mean(cohO)),
             'rho_B_parametric':param['rho_B'],'tau_B_parametric':param['tau_B'],'rho_B_nonparam_V':npV,'rho_B_nonparam_O':npO,'residual_lowfreq_coherence':resid_coh,'representation_pass':rep_pass}
        row.update(_ci_fields('K_V',KV,a['bootstrap_reps'],start+mi*17+1));row.update(_ci_fields('K_O',KO,a['bootstrap_reps'],start+mi*17+2));row.update(_ci_fields('R_OOD',R,a['bootstrap_reps'],start+mi*17+3));row.update(_ci_fields('V_cross_ratio',ds['V_cross_ratio'],a['bootstrap_reps'],start+mi*17+4));row.update(_ci_fields('O_cross_ratio',ds['O_cross_ratio'],a['bootstrap_reps'],start+mi*17+5))
        rows.append(row)
    sdf=pd.DataFrame(rows);pdf=pd.concat(per_seed_frames,ignore_index=True)
    sdf.to_csv(outdir/f'{stage}_summary.csv',index=False);pdf.to_csv(outdir/f'{stage}_per_seed.csv',index=False)
    meta={'stage':stage,'N_per_mode':N,'seed_start':start,'seed_end':int(seeds[-1]),'modes':MODES}
    with open(outdir/f'{stage}_meta.json','w') as f:json.dump(meta,f,indent=2)
    return sdf,pdf

def summarize_controls(stage_summary):
    idx=stage_summary.set_index('mode')
    core=['separate_boundary','common_driver','null']
    return {'max_core_negative_fp':float(max(idx.loc[m,'positive_seed_rate'] for m in core)), 'adversarial_fp':float(idx.loc['adversarial_mimic','positive_seed_rate'])}

def make_freeze(root,cfg,pilot_summary):
    root=Path(root);files=[]
    for p in sorted(root.rglob('*.py')):
        if 'results' in p.parts: continue
        files.append(p)
    yaml_path=root/'preregistration'/'ph_v03.yaml';files.append(yaml_path)
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    pilot_sha=hashlib.sha256(pilot_summary.to_csv(index=False).encode()).hexdigest()
    obj={'version':cfg['version'],'frozen_after_pilot':True,'config':cfg,'source_hashes':hashes,'pilot_summary_sha256':pilot_sha}
    payload=json.dumps(obj,sort_keys=True,separators=(',',':')).encode();obj['freeze_sha256']=hashlib.sha256(payload).hexdigest()
    fp=root/'preregistration'/'freeze.json';fp.write_text(json.dumps(obj,indent=2),encoding='utf-8');return obj
