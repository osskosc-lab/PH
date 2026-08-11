from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent

def main():
    core=pd.read_csv(ROOT/'results'/'confirmatory_core_summary.csv')
    rob=pd.read_csv(ROOT/'results'/'confirmatory_robustness_curve.csv')
    dose=pd.read_csv(ROOT/'results'/'confirmatory_core_dose.csv')
    dec=json.loads((ROOT/'results'/'decision.json').read_text())
    sh=dose[dose['mode']=='shared_boundary'].groupby('lambda')[['K_V','K_O']].mean().reset_index()
    plt.figure(figsize=(8,5));plt.plot(sh['lambda'],sh['K_V'],marker='o',label='K_V');plt.plot(sh['lambda'],sh['K_O'],marker='o',label='K_O');plt.xlabel('lambda');plt.ylabel('K(lambda)');plt.ylim(-.05,1.05);plt.legend();plt.tight_layout();plt.savefig(ROOT/'figures'/'dose_response.png',dpi=180);plt.close()
    plt.figure(figsize=(8,5))
    for factor,g in rob.groupby('factor'):plt.plot(g['strength'],g['P_correct'],marker='o',label=factor)
    plt.axhline(.8,linestyle='--');plt.xlabel('normalized stress strength');plt.ylabel('P_correct');plt.ylim(0,1.03);plt.legend(fontsize=7,ncol=2);plt.tight_layout();plt.savefig(ROOT/'figures'/'robustness_curve.png',dpi=180);plt.close()
    idx=core.set_index('mode'); s=idx.loc['shared_boundary']
    lines=['# PH v0.3.1 Imperfect-Intervention Identifiability Stress Test','',f"**Decision: {dec['decision']}**",'',
           '## Confirmatory shared-boundary endpoints','',f"- beta_V = {s.beta_V:.4f} (95% CI {s.beta_V_LCB:.4f}..{s.beta_V_UCB:.4f})",f"- beta_O = {s.beta_O:.4f} (95% CI {s.beta_O_LCB:.4f}..{s.beta_O_UCB:.4f})",f"- K_V(0.8) = {s.K_V_08:.4f}",f"- K_O(0.8) = {s.K_O_08:.4f}",f"- R_lambda_OOD = {s.R_lambda_OOD:.4f} (UCB {s.R_lambda_OOD_UCB:.4f})",f"- R_CIC = {s.R_CIC:.4f} (UCB {s.R_CIC_UCB:.4f})",f"- intervention correlation = {s.intervention_corr:.4f}",f"- kernel ratio = {s.kernel_ratio:.4f}",'',
           '## False-positive audit','',f"- separate_boundary = {dec['false_positive']['separate_boundary']:.4f}",f"- common_driver = {dec['false_positive']['common_driver']:.4f}",f"- adversarial_clamp_mimic = {dec['false_positive']['adversarial_clamp_mimic']:.4f}",'',
           '## Operating envelope','']
    for k,v in dec['robustness']['breakpoints'].items():lines.append(f'- {k}: s* = {v}')
    lines += ['',f"Compound stress accuracy at s={dec['robustness']['compound_required_level']}: {dec['robustness']['compound_stress_accuracy']:.4f}",'',
              '## Interpretation','', 'This is a robustness/identifiability audit of the v0.3 synthetic detector. It is not evidence that PH exists in biology, AI, consciousness, or nature. ROBUST means the preregistered detector retains >=80% identification accuracy at the preregistered compound-stress point; FRAGILE means the ideal detector remains valid but the operating envelope is narrow.']
    (ROOT/'reports'/'PH_v0.3.1_Imperfect_Intervention_Report_2026-08-12.md').write_text('\n'.join(lines),encoding='utf-8')
if __name__=='__main__':main()
