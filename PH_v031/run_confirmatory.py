from pathlib import Path
import json
from experiment import load_config,run_core,run_robustness,build_decision
ROOT=Path(__file__).resolve().parent
cfg=load_config(ROOT/'preregistration'/'ph_v031.yaml')
freeze=json.loads((ROOT/'preregistration'/'freeze.json').read_text())
core,_=run_core(cfg,'confirmatory',ROOT/'results');rob,detail,bp=run_robustness(cfg,'confirmatory',ROOT/'results')
dec=build_decision(cfg,core,rob,bp,freeze)
(ROOT/'results'/'decision.json').write_text(json.dumps(dec,indent=2),encoding='utf-8')
print(json.dumps(dec,indent=2))
