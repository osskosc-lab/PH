from pathlib import Path
import json
from experiment import load_config,run_stage,summarize_controls
from audit.gates import confirmatory_gates
from audit.decision import decide
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    cfg=load_config(ROOT/'preregistration'/'ph_v03.yaml')
    freeze=json.loads((ROOT/'preregistration'/'freeze.json').read_text())
    pilot=__import__('pandas').read_csv(ROOT/'results'/'pilot_summary.csv'); pshared=pilot.set_index('mode').loc['shared_boundary']
    pilot_info={'positive_detection_rate':float(pshared['positive_seed_rate'])}
    s,_=run_stage(cfg,'confirmatory',ROOT/'results'); shared=s.set_index('mode').loc['shared_boundary'].to_dict();shared['freeze_ok']=bool(freeze.get('frozen_after_pilot'))
    controls=summarize_controls(s);g=confirmatory_gates(shared,controls,cfg,pilot_info);decision=decide(g,shared,controls,cfg)
    out={'version':cfg['version'],'decision':decision,'freeze_sha256':freeze['freeze_sha256'],'pilot':pilot_info,'controls':controls,'gates':g,'shared_confirmatory':shared}
    (ROOT/'results'/'decision.json').write_text(json.dumps(out,indent=2,default=str),encoding='utf-8')
    print(json.dumps({'decision':decision,'controls':controls,'gates':g,'K_V':[shared['K_V_LCB'],shared['K_V'],shared['K_V_UCB']],'K_O':[shared['K_O_LCB'],shared['K_O'],shared['K_O_UCB']],'R_OOD':[shared['R_OOD_LCB'],shared['R_OOD'],shared['R_OOD_UCB']]},indent=2))
