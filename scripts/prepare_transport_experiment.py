#!/usr/bin/env python3
"""Prepare fresh KT / D6 / adaptive controls; never overwrite existing runs.
Run from the repository root on Vera. Uses only the Python standard library.
"""
import argparse
from pathlib import Path
import re
import shutil
import json
import getpass
import subprocess

ROOT = Path(__file__).resolve().parents[1]
METHODS = ('kt', 'd6', 'adaptive')

def set_parameter(text, group, key, value):
    pattern = re.compile(r'(^\s*&'+re.escape(group)+r'\b)(.*?)(^\s*/\s*$)', re.I|re.M|re.S)
    match = pattern.search(text)
    if not match:
        text += '\n&'+group+'\n/\n'
        match = pattern.search(text)
    body = match.group(2)
    assignment = re.compile(r'^\s*'+re.escape(key)+r'\s*=.*$', re.I|re.M)
    line = '  '+key+'='+str(value)
    if assignment.search(body):
        body = assignment.sub(lambda _:line, body)
    else:
        body = body.rstrip()+'\n'+line+'\n'
    return text[:match.start()]+match.group(1)+'\n'+body.strip('\n')+'\n'+match.group(3)+text[match.end():]

def make_parameter(text, key, value):
    pattern = re.compile(r'^\s*'+re.escape(key)+r'\s*[?:+]?=.*$', re.M)
    if pattern.search(text): return pattern.sub(lambda _:key+' = '+value,text)
    return text.rstrip()+'\n'+key+' = '+value+'\n'

def configure_turbulence_output(path):
    """Keep everything needed for physical-velocity component spectra on Vera."""
    start=(path/'start.in').read_text()
    for group,key,value in [('init_pars','lwrite_aux','T'),('init_pars','lwrite_ic','T'),
                            ('hydro_init_pars','lvv_as_comaux','T'),
                            ('hydro_init_pars','llorentz_as_aux','T')]:
        start=set_parameter(start,group,key,value)
    (path/'start.in').write_text(start)
    run=(path/'run.in').read_text()
    method=json.loads((path/'experiment.json').read_text())['method']
    run=set_parameter(run,'hydro_run_pars','lkt_transport','F' if method=='d6' else 'T')
    for key,value in [('dsnap','.5'),('dspec','.25'),('relvel_spec','T'),('lspec_start','T')]:
        run=set_parameter(run,'run_pars',key,value)
    (path/'run.in').write_text(run)
    make=(path/'src/Makefile.local').read_text()
    for key,value in [('POWER','power_spectrum'),('FOURIER','fourier_fftpack')]:
        make=make_parameter(make,key,value)
    (path/'src/Makefile.local').write_text(make)
    diagnostics=['t','dt','urms','umax','ekin','rhom','rhomin','rhomax','o2m','divu2m','gammax']
    (path/'print.in').write_text('it(i8)\n'+''.join(name+'(e18.10)\n' for name in diagnostics))

def configure_turbulence_strength(path, amplitude):
    start=(path/'start.in').read_text()
    for key,value in [('ampluu',str(amplitude)),('qirro_uu','.5'),('lsqrt_qirro_uu','T')]:
        start=set_parameter(start,'hydro_init_pars',key,value)
    (path/'start.in').write_text(start)
    metadata=json.loads((path/'experiment.json').read_text())
    metadata.update(ampluu=amplitude,qirro_uu=.5)
    (path/'experiment.json').write_text(json.dumps(metadata,indent=2)+'\n')

def prepare(case, cstar, jstar, reuse=False, amplitude=.1):
    if shutil.which('squeue'):
        queue=subprocess.run(['squeue','-h','-u',getpass.getuser(),'-o','%j'],
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True)
        if queue.returncode: raise SystemExit('Cannot check queue; leaving inputs unchanged: '+queue.stderr)
        if any(name.startswith('transport-') for name in queue.stdout.splitlines()):
            raise SystemExit('Transport jobs already queued/running; refusing to change their inputs.')
    baseline = ROOT/'runs'/('mixed-turbulence-kt' if case=='turbulence' else 'relshock-standard')
    required = [baseline/'start.in',baseline/'run.in',baseline/'src/Makefile.local']
    missing = [str(p) for p in required if not p.is_file()]
    if missing: raise SystemExit('Missing baseline inputs (run this on Vera): '+', '.join(missing))
    paths = [ROOT/'runs'/('experiment-'+case+'-'+method) for method in METHODS]
    if reuse and all((path/'experiment.json').is_file() for path in paths):
        for path in paths:
            for relative in ['start.in','run.in','transport.in','src/cparam.local','src/Makefile.local','src/kt_transport_experiment.f90']:
                if not (path/relative).is_file(): raise SystemExit('Incomplete prepared run: '+str(path))
            if (path/'data/proc0/VAR0').exists(): raise SystemExit('Already initialized: '+str(path))
        if case=='turbulence':
            for path in paths:
                configure_turbulence_output(path)
                configure_turbulence_strength(path,amplitude)
        print('Prepared '+case+' inputs updated before initialization. Use the threshold setter for thresholds.')
        return
    for path in paths:
        if path.exists(): raise SystemExit('Refusing to overwrite '+str(path))
    tasks = 4 if case=='turbulence' else 3
    grid = (64,64,64) if case=='turbulence' else ((384,1,1) if case=='smooth' else (4608,1,1))
    layout = (2,2,1) if case=='turbulence' else (3,1,1)
    source_start = (baseline/'start.in').read_text()
    if case=='smooth':
        source_start = '''! Smooth, weak compressional wave control: no initial discontinuity.
&init_pars
 xyz0=0.,0.,0.
 xyz1=6.283185307179586,1.,1.
 lperi=T,T,T
 lwrite_aux=T
 lwrite_ic=T
/
&eos_init_pars
 gamma=1., cs0=.57735027
/
&hydro_init_pars
 lconservative=T
 lrelativistic=T
 llorentz_as_aux=T
 inituu='sinwave-x'
 ampluu=.01
 kx_uu=1.
/
&density_init_pars
 initlnrho='const_rho',rho_const=1.
 lrelativistic_eos=T
 ldensity_nolog=T
/
'''
    for path,method in zip(paths,METHODS):
        path.mkdir(parents=True)
        (path/'src').mkdir()
        # Only editable inputs; never copy old outputs, binaries or linked source.
        for inp in baseline.glob('*.in'):
            if inp.name not in ('start.in','run.in'): shutil.copyfile(inp,path/inp.name)
        for local in (baseline/'src').glob('*.local'):
            shutil.copyfile(local,path/'src'/local.name)
        (path/'start.in').write_text(source_start)
        run = (baseline/'run.in').read_text()
        for group,key,value in [('hydro_run_pars','lkt_transport','F' if method=='d6' else 'T'),
                                ('hydro_run_pars','kt_theta','2.'),
                                ('run_pars','it1','50')]:
            run=set_parameter(run,group,key,value)
        # Keep baseline explicit viscosity and density diffusion identical.
        if case=='smooth':
            for key,value in [('tmax','1.'),('nt','20000'),('dt','2e-4'),('dsnap','.25')]:
                run=set_parameter(run,'run_pars',key,value)
        elif case=='shock':
            run=set_parameter(run,'run_pars','nt','20000')
            run=set_parameter(run,'run_pars','tmax','3.')
        (path/'run.in').write_text(run)
        make=(path/'src/Makefile.local').read_text()
        for key,value in [('KT_TRANSPORT','kt_transport_experiment'),('DERIV','deriv'),('REAL_PRECISION','double')]:
            make=make_parameter(make,key,value)
        (path/'src/Makefile.local').write_text(make)
        # Retain baseline auxiliary-count directives, which Pencil reads as metadata.
        aux = 10 if case=='turbulence' else 7
        directives='! MAUX CONTRIBUTION {0}\n! COMMUNICATED AUXILIARIES {0}'.format(aux)
        (path/'src/cparam.local').write_text(directives+'\n'+
            'integer, parameter :: ncpus={0},nprocx={1},nprocy={2},nprocz={3}\n'.format(tasks,*layout)+
            'integer, parameter :: nxgrid={0},nygrid={1},nzgrid={2}\n'.format(*grid))
        shutil.copyfile(ROOT/'numerics/kt_transport_experiment.f90',path/'src/kt_transport_experiment.f90')
        (path/'transport.in').write_text('''&transport_experiment
 transport_mode='{method}'
 compression_threshold={cstar}
 pressure_threshold={jstar}
 sensor_buffer=2
/
'''.format(method=method,cstar=cstar,jstar=jstar))
        if case!='turbulence': (path/'yzaver.in').write_text('uxmx\nrhomx\n')
        metadata={'case':case,'method':method,'grid':grid,'tasks':tasks,
                  'baseline':str(baseline.relative_to(ROOT)),'compression_threshold':cstar,
                  'pressure_threshold':jstar,'buffer_faces':2,
                  'note':'D6 means central conservative transport; other derivatives and explicit diffusion unchanged.'}
        (path/'experiment.json').write_text(json.dumps(metadata,indent=2)+'\n')
        if case=='turbulence':
            configure_turbulence_output(path)
            configure_turbulence_strength(path,amplitude)
        print(path.relative_to(ROOT))
    print('Prepared '+case+' controls. No simulations have been started.')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('case',choices=['shock','smooth','turbulence','all'])
    parser.add_argument('--compression-threshold',type=float,default=.003)
    parser.add_argument('--pressure-threshold',type=float,default=.003)
    parser.add_argument('--amplitude',type=float,default=.1,help='Initializer amplitude; not physical RMS velocity')
    parser.add_argument('--reuse',action='store_true',help='Keep complete, uninitialized prepared folders')
    args=parser.parse_args()
    if not (args.compression_threshold>=0 and 0<=args.pressure_threshold<1):
        parser.error('Invalid thresholds')
    if not 0<args.amplitude<=.1:
        parser.error('Use 0 < amplitude <= 0.1 for this initial-field configuration')
    for case in (['shock','smooth','turbulence'] if args.case=='all' else [args.case]):
        prepare(case,args.compression_threshold,args.pressure_threshold,args.reuse,args.amplitude)
if __name__=='__main__': main()
