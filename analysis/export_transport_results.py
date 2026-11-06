"""Export small plot-ready results on Vera; retain full snapshots there."""
import argparse
from pathlib import Path
import json
import numpy as np
import pencil as pc
from export_velocity_components import main as export_components


def export_usage(data):
    files=sorted(data.glob('transport-rank*.dat'))
    if not files: return  # Original KT path always uses KT, no selector needed.
    totals={}
    for path in files:
        rows=np.atleast_2d(np.loadtxt(path))
        seen=set()
        for it,t,selected,total in rows:
            key=int(it)
            if key in seen: raise ValueError('Repeated iteration in '+str(path))
            seen.add(key)
            if key not in totals: totals[key]=[t,0,0,0]
            record=totals[key]
            if not np.isclose(t,record[0],rtol=1e-10,atol=1e-12):
                raise ValueError('MPI rank sample times differ')
            record[1]+=int(selected); record[2]+=int(total); record[3]+=1
    # Export only samples written by every rank (e.g. partial failed outputs).
    output=[[it,r[0],r[1],r[2],r[1]/r[2]] for it,r in sorted(totals.items())
            if r[3]==len(files) and r[2]>0]
    np.savetxt(data/'transport_usage.dat',output,fmt='%.12e',
               header='iteration t kt_selected_faces total_faces kt_fraction')


def export_results(run):
    data=run/'data'
    par=pc.read.param(datadir=str(data),quiet=True)
    dim=pc.read.dim(datadir=str(data))
    export_usage(data)
    if dim.ny==dim.nz==1:
        filename='yzaverages.dat' if (data/'yzaverages.dat').exists() else 'yzaverages_final.dat'
        aver=pc.read.aver(datadir=str(data),simdir=str(run),plane_list=['yz'],
                          avfile_list=[filename],infile_list=['yzaver.in'],precision='d',quiet=True)
        if par.lperi[0]:
            x=par.xyz0[0]+np.arange(dim.nx)*par.lxyz[0]/dim.nx
        else:
            x=np.linspace(par.xyz0[0],par.xyz1[0],dim.nx)
        for name,index in [('initial',0),('final',-1)]:
            t=float(aver.yz.t[index])
            if name=='initial' and not np.isclose(t,0.0): continue
            velocity=np.asarray(aver.yz.uxmx[index],dtype=float)
            rest_energy=np.asarray(aver.yz.rhomx[index],dtype=float)
            pressure=float(par.cs0)**2*rest_energy
            np.savetxt(data/('profile_'+name+'.dat'),np.column_stack([x,velocity,rest_energy,pressure]),
                       fmt='%.12e',header='t={:.12e}\nx velocity_x rest_energy pressure'.format(t))
        print('Exported 1D profiles:',run,flush=True)
    else:
        # Reuse the tested Helmholtz/Parseval exporter; no snapshots transferred.
        import sys
        previous=sys.argv
        try:
            sys.argv=[previous[0],str(run)]
            export_components()
        finally:
            sys.argv=previous
    metadata=run/'experiment.json'
    if metadata.exists():
        (data/'experiment.json').write_text(metadata.read_text())
    completed=run/'COMPLETED'
    if completed.exists():
        (data/'export_complete.txt').write_text('Simulation completed; small exports produced.\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    export_results(args.run.resolve())
if __name__=='__main__': main()
