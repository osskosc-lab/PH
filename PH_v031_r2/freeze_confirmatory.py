from pathlib import Path
import json
R=Path(__file__).resolve().parent
ksel=json.loads((R/'results'/'kernel_pilot_selection.json').read_text())
if not ksel.get('passed',False):
    raise SystemExit('REFUSE_FREEZE: preregistered Kernel Pilot Gate failed; Confirmatory must not start')
raise SystemExit('PILOT_PASS_REQUIRES_EXPLICIT_CONFIRMATORY_FREEZE_IMPLEMENTATION')
