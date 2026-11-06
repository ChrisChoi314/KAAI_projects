#!/usr/bin/env python3
"""Set both thresholds before submitting the prepared experiment jobs."""
import argparse
import json
from pathlib import Path
import re

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('threshold',type=float)
parser.add_argument('--case',choices=['shock','smooth','turbulence','all'],default='turbulence')
args=parser.parse_args()
if not 0<=args.threshold<1: parser.error('Threshold must be in [0, 1)')
root=Path(__file__).resolve().parents[1]
pattern='experiment-*' if args.case=='all' else 'experiment-'+args.case+'-*'
runs=sorted(p for p in (root/'runs').glob(pattern) if (p/'experiment.json').is_file())
if not runs: parser.error('Prepare the experiment folders first')
for run in runs:
    if (run/'data/proc0/VAR0').exists():
        parser.error('Already initialized; leave existing results unchanged: '+str(run))
for run in runs:
    path=run/'transport.in'
    text=path.read_text()
    for key in ['compression_threshold','pressure_threshold']:
        text,count=re.subn(r'(?m)^\s*'+key+r'\s*=.*$',
                           ' '+key+'='+str(args.threshold),text)
        if count!=1: raise ValueError('Expected one '+key+' in '+str(path))
    metadata=json.loads((run/'experiment.json').read_text())
    for key in ['compression_threshold','pressure_threshold']: metadata[key]=args.threshold
    path.write_text(text)
    (run/'experiment.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(run.name, 'C*=J*='+str(args.threshold))
