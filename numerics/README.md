# First adaptive transport experiment

`kt_transport_experiment.f90` retains the KT implementation from Pencil revision
`c193fa7da25577df82be36aa2580342def041923` and adds a dispatcher. It supports
uniform Cartesian conservative relativistic radiation-fluid runs without a
Higgsless source. The fixed D6 control uses Pencil's original `lkt_transport=F` branch. KT and
adaptive use `lkt_transport=T` and select transport using `transport.in`:

- `transport_mode='kt'`: unchanged upstream KT transport.
- Fixed D6: `lkt_transport=F`, `DERIV=deriv`; the `transport.in` mode is unused.
- `transport_mode='d6'` remains available internally for operator tests; it is
  not the fixed D6 control submitted by the experiment scripts.
- `transport_mode='adaptive'`: KT at flagged faces, D6 at other faces.

D6 is a differentiation formula, not a sixth spatial derivative. All controls
retain the same default DERIV module and explicit viscosity/density diffusion.
The common dispatcher makes it possible to compile once per grid/case.
The adaptive branch expresses D6 as central face fluxes to share a single
selected flux between adjacent cells. This adds no KT jump-damping term.
The fixed D6 reference goes through the unmodified Pencil central derivative
routines for the energy and momentum flux divergence.

## Sensor and conservation

For each coordinate direction, the raw boundary indicators are
`C=max(0,v_left-v_right)/sqrt(1/3)` and
`J=abs(p_right-p_left)/(p_right+p_left)` from **cell-center physical** pressure
and normal velocity. Both must exceed their thresholds. The current default is C*=J*=0.003, an exploratory compromise. On the
completed 1D profile it flags 10 boundaries (before the two-face buffer),
compared with 8 at 0.01 and 20 at 0.0001. The smaller 0.0001 setting also
flags smooth compression in a synthetic check.
These are not calibrated universal
thresholds. Smooth compressions may trigger; weak shocks may be missed.

The flag expands by two neighboring faces along the same coordinate direction,
using the three ghost cells available to the default DERIV module. There is
no time persistence, vorticity veto, isotropic buffer, or ML in this first
implementation. Every component and both adjacent cells use the same selected
face flux. Selection is discrete, without continuous blending.

For efficiency, rows without any flags skip KT reconstruction; mixed rows
compute vectorized central and KT candidates before selecting by face. This
is not promised to run faster than either fixed method. Energy and momentum
still enter through the two existing Pencil hooks, as in the upstream module.

A sampled first-RK-stage count is written per rank every `it1` steps. The
exporter sums the counts to get the fraction of owned positive faces using KT.
The KT-only control has fraction one by construction. Noncausal or nonfinite
cell states in D6/adaptive mode stop with an error; this implementation does
not have positivity-preserving stage rollback or an entropy guarantee.

## Running on Vera

The current requested batch is mixed turbulence ONLY. From the project root,
run `python3 scripts/prepare_transport_experiment.py turbulence --reuse`,
`python3 scripts/set_transport_thresholds.py 0.003 --case turbulence`, then
`bash scripts/submit_transport_experiments.sh turbulence`. Existing initialized runs
are never overwritten. Names start with `runs/experiment-`.

For the requested turbulence-only batch, one build job compiles the shared
binary. Three independent simulation jobs then run KT, D6, and adaptive in
parallel, four MPI ranks each (12 ranks total if the scheduler admits all).
Each method has its own export job, released immediately after that method
finishes. There are seven jobs total: one build, three simulations, three
independent exports. Completed methods can be plotted while others run. No shock-tube or smooth-wave
jobs are submitted by default. The older optional case utilities remain
available but are outside the current batch.

The turbulence case copies the existing `mixed-turbulence-kt` inputs and keeps
its 64^3 setup/seed, with ampluu increased from 0.05 to 0.1 and
qirro_uu retained at 0.5; all three new controls use the same MPI layout and
precision. Full snapshots stay on Vera. Inspect the comparison plots before
making accuracy claims: turbulence at one resolution does not establish
convergence, and this weak setup may not contain strong shocks. A later
128^3 comparison must match the initial resolved Fourier realization; a shared
random seed alone does not establish that match.

Open `analysis/transport_comparison.ipynb` on the Mac after downloading the small
exports. Notebook outputs distinguish method differences from actual errors.

## Verification

`python3 tests/check_transport_module.py --pencil /path/to/pencil-code` compiles
and executes the actual Fortran module with minimal Pencil data stubs, bounds
checking, and floating-point traps. It checks 3D D6 equivalence, no flags on a
smooth field, nontrivial KT/D6 selection on a discontinuous field, and periodic
conservation of all four components. This does not replace a full Pencil/MPI
integration run. Those runs are intentionally left to the user's Vera jobs.

## Stronger initial field

The preparer now sets ampluu=0.1 and qirro_uu=0.5 in all three uninitialized
turbulence controls. This doubles the initializer amplitude while keeping the
same projected random-field mix, seed and grid. It is not a prescribed RMS
physical velocity: uu stores momentum here. With the original E=1 and peak
physical speed 0.335661, doubling momentum predicts a peak speed about 0.777
(and |S|/E about 0.863), provided the same initial realization is reproduced.
That makes stronger compression more likely; it does not guarantee shocks
by a fixed time. Verify the actual initial state and front profiles. Do not
extrapolate to larger amplitude without checking E>|S|.
