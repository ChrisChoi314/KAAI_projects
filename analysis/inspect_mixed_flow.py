"""Inspect existing 3D periodic snapshots for compression, vortices and fronts.
This diagnoses shock candidates; it does not certify shocks from a threshold.
Full snapshots remain on Vera. Run through scripts/inspect_mixed_flow.slurm.
"""
import argparse
from pathlib import Path
import numpy as np
import pencil as pc
from export_velocity_components import physical_velocity, component_spectra


def gradients(velocity, lengths):
    grad=np.empty((3,3)+velocity.shape[1:],dtype=float)
    for direction in range(3):
        axis=2-direction
        h=lengths[direction]/velocity.shape[axis+1]
        for component in range(3):
            field=velocity[component]
            grad[component,direction]=(np.roll(field,-1,axis=axis)-np.roll(field,1,axis=axis))/(2*h)
    divergence=grad[0,0]+grad[1,1]+grad[2,2]
    curl=np.stack([grad[2,1]-grad[1,2],grad[0,2]-grad[2,0],grad[1,0]-grad[0,1]])
    return divergence, np.sqrt(np.sum(curl**2,axis=0))


def inspect(velocity,pressure,lengths,cs):
    divergence,omega=gradients(velocity,lengths)
    strong=np.zeros(pressure.shape,dtype=bool)
    weak_count=strong_count=0
    best={'score':-1.0}
    max_c=max_j=0.0
    for direction in range(3):
        axis=2-direction
        c=np.maximum(0,velocity[direction]-np.roll(velocity[direction],-1,axis=axis))/cs
        neighbor=np.roll(pressure,-1,axis=axis)
        jump=np.abs(neighbor-pressure)/(neighbor+pressure)
        weak=(c>1e-4)&(jump>1e-4)
        seeds=(c>.03)&(jump>.03)
        weak_count+=np.count_nonzero(weak); strong_count+=np.count_nonzero(seeds)
        strong|=seeds|np.roll(seeds,1,axis=axis)
        score=c*jump
        index=np.unravel_index(np.argmax(score),score.shape)
        if score[index]>best['score']:
            best={'score':float(score[index]),'direction':direction,'index':index,
                  'C':float(c[index]),'J':float(jump[index])}
        max_c=max(max_c,float(c.max())); max_j=max(max_j,float(jump.max()))
    denominator=3*pressure.size
    return divergence,omega,strong,best,weak_count/denominator,strong_count/denominator,max_c,max_j


def save_front(data,out,velocity,pressure,divergence,omega,mask,best,lengths,t):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    direction=best['direction']; axis=2-direction; index=best['index']
    selector=tuple(slice(None) if a==axis else index[a] for a in range(3))
    offsets=np.arange(-12,14)
    indices=(index[axis]+offsets)%pressure.shape[axis]
    distance=(offsets-.5)*lengths[direction]/pressure.shape[axis]
    fields=[pressure,velocity[direction],-divergence,omega]
    lines=[field[selector][indices] for field in fields]
    np.savetxt(data/'strongest_front_profile.dat',np.column_stack([distance]+lines),fmt='%.12e',
               header='t={:.12e}; direction={}\ndistance pressure normal_velocity minus_divergence curl_magnitude'.format(t,'xyz'[direction]))
    fig,axes=plt.subplots(1,3,figsize=(13,3.5))
    axes[0].plot(distance,lines[0],'.-'); axes[0].set_ylabel('Physical pressure')
    axes[1].plot(distance,lines[1],'.-'); axes[1].set_ylabel('Physical normal velocity')
    axes[2].plot(distance,lines[2],'.-',label='-div v')
    axes[2].plot(distance,lines[3],'.-',label='|curl v|'); axes[2].legend()
    for ax in axes: ax.axvline(0,color='0.7',linestyle='--'); ax.set_xlabel('Distance from selected face')
    fig.suptitle('Largest C*J candidate, t={:.5g}; not automatically a shock'.format(t))
    fig.tight_layout(); fig.savefig(out/'strongest_front.png',dpi=160); plt.close(fig)
    z=index[0]
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,field,title in zip(axes,[pressure,-divergence,omega],['Physical pressure','Compression: -div v','Vorticity magnitude']):
        image=ax.imshow(field[z],origin='lower',aspect='equal',extent=[0,lengths[0],0,lengths[1]])
        fig.colorbar(image,ax=ax,shrink=.7)
        ax.set_title(title); ax.set_xlabel('x'); ax.set_ylabel('y')
    fig.suptitle('Common z slice through candidate, t={:.5g}'.format(t))
    fig.tight_layout(); fig.savefig(out/'pressure_compression_vorticity.png',dpi=160); plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args(); run=args.run.resolve(); data=run/'data'
    par=pc.read.param(datadir=str(data),quiet=True)
    if not np.all(par.lperi): raise ValueError('This inspection assumes periodic boundaries')
    cs=float(par.cs0); w=cs**2
    names=sorted([p.name for p in (data/'proc0').glob('VAR*') if p.name[3:].isdigit()],key=lambda s:int(s[3:]))
    if (data/'proc0/var.dat').is_file(): names.append('var.dat')
    if not names: raise FileNotFoundError('No snapshots in '+str(data/'proc0'))
    out=run/'plots/flow_check'; out.mkdir(parents=True,exist_ok=True)
    rows=[]; largest=-1.0
    print('These are flow diagnostics, not a certified shock classification.',flush=True)
    for name in names:
        var=pc.read.var(var_file=name,datadir=str(data),trimall=True,quiet=True,timing=False)
        t=float(var.t)
        if rows and np.isclose(t,rows[-1][0],rtol=1e-12,atol=1e-12): continue
        velocity=physical_velocity(var,w)
        pressure=w*(np.asarray(var.rho)-np.sum(np.asarray(var.uu)*velocity,axis=0))
        if np.any(pressure<=0): raise ValueError('Nonpositive physical pressure')
        divergence,omega,mask,best,weak,strong,max_c,max_j=inspect(velocity,pressure,par.lxyz,cs)
        _,total,vort,comp,mean,error=component_spectra(velocity,par.lxyz)
        speed=np.sqrt(np.sum(velocity**2,axis=0)); fraction=comp.sum()/max(vort.sum()+comp.sum(),1e-30)
        row=[t,np.sqrt(np.mean(speed**2))/cs,speed.max()/cs,vort.sum(),comp.sum(),fraction,
             np.mean(omega**2),np.mean(divergence**2),weak,strong,max_c,max_j,best['score']]
        rows.append(row)
        print('{} t={:.5g}: rms(v)/cs={:.3f}, max(v)/cs={:.3f}, longitudinal fraction={:.3f}, '
              'weak-flag faces={:.2%}, stronger-candidate faces={:.2%}, max C*J={:.3g}'.format(
                  name,t,row[1],row[2],fraction,weak,strong,best['score']),flush=True)
        if best['score']>largest:
            largest=best['score']
            save_front(data,out,velocity,pressure,divergence,omega,mask,best,par.lxyz,t)
    header=('t vrms_over_cs vmax_over_cs vortical_power compressional_power compressional_fraction '
            'curl2_mean divergence2_mean raw_flag_fraction_1em4 raw_flag_fraction_003 max_C max_J max_C_times_J')
    np.savetxt(data/'flow_diagnostics.dat',rows,fmt='%.12e',header=header)
    print('SAVED:',data/'flow_diagnostics.dat',flush=True)
    print('SAVED:',out/'strongest_front.png',flush=True)
    print('SAVED:',out/'pressure_compression_vorticity.png',flush=True)
    print('INSPECTION COMPLETE',flush=True)
if __name__=='__main__': main()
