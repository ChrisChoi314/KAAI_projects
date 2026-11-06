"""Copy the failed D6 configuration, changing only timestep safety factors."""
from pathlib import Path
import json, shutil
from prepare_transport_experiment import set_parameter
root=Path(__file__).resolve().parents[1]
source=root/'runs/experiment-turbulence-d6'
target=root/'runs/experiment-turbulence-d6-half-cfl'
if target.exists(): raise SystemExit('Refusing to overwrite '+str(target))
for required in ['start.in','run.in','src/Makefile.local','src/cparam.local','src/start.x','src/run.x']:
    if not (source/required).is_file(): raise SystemExit('Missing '+str(source/required))
target.mkdir(); (target/'src').mkdir(); (target/'data').mkdir()
for path in source.glob('*.in'): shutil.copyfile(path,target/path.name)
for path in (source/'src').glob('*.local'): shutil.copyfile(path,target/'src'/path.name)
for name in ['start.x','run.x']: shutil.copy2(source/'src'/name,target/'src'/name)
text=(target/'run.in').read_text()
# Original comparison uses cdt=0.25, cdtv=0.1. Halve both bounds.
import re
for key,expected in [('cdt',.25),('cdtv',.1)]:
    match=re.search(r'(?im)^\s*'+key+r'\s*=\s*([\d.eEdD+-]+)',text)
    if not match or abs(float(match.group(1).replace('D','e').replace('d','e'))-expected)>1e-12:
        raise SystemExit('Unexpected original '+key+'; inspect original inputs before retrying')
    text=set_parameter(text,'run_pars',key,str(expected/2))
text=set_parameter(text,'hydro_run_pars','lkt_transport','F')
(target/'run.in').write_text(text)
if (source/'experiment.json').exists():
    metadata=json.loads((source/'experiment.json').read_text())
    metadata.update(timestep_check='half CFL factors',cdt=.125,cdtv=.05)
    (target/'experiment.json').write_text(json.dumps(metadata,indent=2)+'\n')
assert (target/'start.in').read_bytes()==(source/'start.in').read_bytes()
print('Prepared',target)
print('Only intended changes: cdt 0.25 -> 0.125; cdtv 0.1 -> 0.05. Native no-KT transport retained.')
