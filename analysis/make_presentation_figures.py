"""Create slide-ready figures from completed pilot data only."""
from pathlib import Path
import sys, warnings
sys.path.insert(0,str(Path.home()/'Work/research/software/pencil-code/python'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pencil as pc

root=Path(__file__).resolve().parents[1]
run=root/'runs/mixed-turbulence-kt'
out=run/'plots/presentation'; out.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.size':16,'axes.spines.top':False,'axes.spines.right':False,
                     'axes.titlesize':19,'axes.labelsize':17,'legend.fontsize':13})
def save(fig,name):
    fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight')
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight'); plt.close(fig)
ts=pc.read.ts(datadir=str(run/'data'),precision='d',quiet=True)
par=pc.read.param(datadir=str(run/'data'),quiet=True)
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    power=pc.read.power(datadir=str(run/'data'),file_name='powerv.dat',quiet=True)
valid=np.any(power.v>0,axis=1); times=power.t[valid]; spectra=power.v[valid]
k=np.arange(spectra.shape[1])*2*np.pi/par.lxyz[0]
fig,ax=plt.subplots(figsize=(11,5.5))
for i in sorted(set([0,int(np.argmin(abs(times-2))),int(np.argmin(abs(times-5))),len(times)-1])):
    keep=(k>0)&(spectra[i]>0)
    ax.loglog(k[keep],spectra[i,keep],linewidth=2.5,label=f't = {times[i]:.2f}')
ax.set_xlabel('Wavenumber k'); ax.set_ylabel('Total velocity power per shell')
ax.set_title('Completed KT pilot: velocity spectrum evolves'); ax.legend(ncol=2)
ax.grid(alpha=.15); fig.tight_layout()
fig.text(.08,-.035,'64³, initial amplitude 0.05. Total velocity spectrum; no vortical/compressional split shown.',fontsize=12)
save(fig,'pilot_total_spectrum')
fig,axes=plt.subplots(1,2,figsize=(12,5.2))
axes[0].plot(ts.t,ts.ekin/ts.ekin[0],lw=2.5); axes[0].set_ylabel('Kinetic energy / initial value')
axes[0].set_title('Kinetic energy decays')
axes[1].plot(ts.t,ts.o2m/ts.o2m[0],lw=2.5,label='Mean squared curl / initial')
axes[1].plot(ts.t,ts.divu2m/ts.divu2m[0],lw=2.5,label='Mean squared divergence / initial')
axes[1].set_title('Both types of gradients are present'); axes[1].legend(fontsize=11)
for ax in axes: ax.set_xlabel('Simulation time'); ax.grid(alpha=.15)
fig.tight_layout(); fig.text(.07,-.035,'Completed weak KT pilot. Decay alone does not distinguish physical dissipation from numerical damping.',fontsize=12)
save(fig,'pilot_energy_and_gradients')
# Read the already transferred final 1D profiles through Pencil's averaging reader.
shock=root/'runs/relshock-standard'
a=pc.read.aver(datadir=str(shock/'data'),simdir=str(shock),plane_list=['yz'],
    avfile_list=['yzaverages_final.dat'],infile_list=['yzaver.in'],precision='d',quiet=True)
p0=pc.read.param(datadir=str(shock/'data'),quiet=True)
dim=pc.read.dim(datadir=str(shock/'data'))
x=np.linspace(p0.xyz0[0],p0.xyz1[0],dim.nx)
v=np.asarray(a.yz.uxmx[-1]); p=float(p0.cs0)**2*np.asarray(a.yz.rhomx[-1])
xf=(x[:-1]+x[1:])/2; pf=(p[:-1]+p[1:])/2
C=np.maximum(0,v[:-1]-v[1:])/float(p0.cs0); J=np.abs(np.diff(p))/(p[:-1]+p[1:])
fig,axes=plt.subplots(1,3,figsize=(13,4.8),sharex=True,sharey=True)
for ax,threshold in zip(axes,[.01,.003,.0001]):
    flag=(C>threshold)&(J>threshold)
    ax.plot(x,p,'o-',color='0.4',markersize=3,lw=1)
    ax.scatter(xf[flag],pf[flag],color='#d1495b',s=35,zorder=3)
    ax.set_title(f'C* = J* = {threshold:g}\n{flag.sum()} raw flagged boundaries')
    ax.set_xlim(2.225,2.28); ax.set_ylim(.025,.115); ax.set_xlabel('Position x'); ax.grid(alpha=.15)
axes[0].set_ylabel('Physical pressure')
fig.tight_layout(); fig.text(.055,-.055,'Completed 1D calibration only, t = 3. Red: raw flags before the two-face buffer. Not proof of shock-only detection.',fontsize=12)
save(fig,'sensor_threshold_comparison')
print(out)
