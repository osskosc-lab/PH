from pathlib import Path
from experiment import load_config,run_core,run_robustness
ROOT=Path(__file__).resolve().parent
cfg=load_config(ROOT/'preregistration'/'ph_v031.yaml')
core,_=run_core(cfg,'pilot',ROOT/'results');rob,detail,bp=run_robustness(cfg,'pilot',ROOT/'results')
print(core[['mode','positive','positive_probability','R_lambda_OOD','R_CIC']].to_string(index=False))
print('\nPilot breakpoints\n',bp.to_string(index=False))
