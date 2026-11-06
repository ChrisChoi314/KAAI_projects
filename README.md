# KAAI constraints simulations

Keep each simulation in its own directory under `runs/`. The Pencil Code
installation is shared and lives outside this repository. Each run has its own
inputs, build, and output, so changing one run does not alter another.

```text
KAAI_constraints_ML/
  README.md
  .gitignore
  scripts/
    new_run.py           # Shared tool for creating independent runs
  runs/
    jeans-x/             # Original completed 64-cell, single-processor test
      start.in           # Initial conditions
      run.in             # Runtime parameters
      print.in           # Quantities to record
      src/
        Makefile.local   # Enabled physics modules and MPI setting
        cparam.local     # Grid size and processor layout
      data/              # Generated results (ignored)
```

Use the repository root for shared tools, documentation, and future analysis
scripts. Keep all run-specific `.in` files and `src/*.local` settings inside the
corresponding run. Builds and results are generated there as well and are ignored
by Git. The original test's existing results and build have been preserved.

## Activate Pencil Code

In each new Terminal, activate your external installation, then return here:

```bash
cd ~/Work/research/software/pencil-code
source sourceme.sh
cd ~/Work/grad/workshops/KAAI_alberto/KAAI_constraints_ML
```

Adjust the installation path if you move Pencil Code. On another machine, install
Pencil Code separately and regenerate the links with `pc_setupsrc` in each run.

## Create a new run

From the repository root:

```bash
python3 scripts/new_run.py jeans-low-amplitude
```

This copies only `.in` and `src/*.local` files from `runs/jeans-x/`. It creates an
empty data directory and refuses to overwrite an existing run. Results, compiled
files, and generated links are never copied. To copy another run's settings:

```bash
python3 scripts/new_run.py jeans-high-resolution --from jeans-low-amplitude
```

Custom source files or extra input formats must be copied separately if a future
experiment needs them.

## Configure, build, and run

Edit the new run's inputs and settings first. Then, in that run's directory:

```bash
cd runs/jeans-low-amplitude
pc_setupsrc
pc_build -f GNU-GCC CC=gcc-16
pc_run
```

This is the tested Mac compiler command for Homebrew GCC 16 and the current
single-processor setup (`MPICOMM=nompicomm`, `ncpus=1`). Rebuild after changing
`src/*.local`; compiler or module changes may require a clean build. MPI runs need
consistent processor settings and an MPI build configuration instead.

Successful runs create `COMPLETED` and write results under `data/`, including
`data/time_series.dat`. Use a new run directory for a new experiment to preserve
earlier results. Keep the completed `jeans-x` run as a baseline.

## GitHub

Commit the run inputs, local settings, documentation, and analysis scripts.
Simulation data, generated Pencil Code links, build files, and caches are ignored.
If you add custom source files under a run's `src/`, add explicit exceptions in
`.gitignore` so Git can track them. The ignore rules filter names and paths, not
file sizes, so review staged files before committing:

```bash
git add -A
git diff --cached --stat
```

## Vera

Clone this project repository on Vera separately from the Pencil Code source
checkout. Track simulation inputs, `src/*.local`, job scripts, and analysis here;
keep generated builds and data out of Git.

The initial test uses Pencil revision
`c193fa7da25577df82be36aa2580342def041923`, matching the local installation,
with Vera modules `gcc/11.2.0` and `mpi/4.1.1-gcc11.2.0`. Install Pencil at
`/hildafs/projects/phy210003p/choic/software/pencil-code`, or set
`VERA_PENCIL_HOME` to another checkout before submitting.

From this repository's root on Vera:

```bash
sbatch scripts/vera-jeans.slurm
squeue -u choic
```

The job builds and runs the tracked Jeans inputs with one MPI process on an RM
compute node. Each submission creates `runs/jeans-vera-JOBID/`, preserving the
baseline. Read `vera-jeans-JOBID.log` after completion; success ends with
`PENCIL TEST COMPLETED` and numerical output. This checks execution; numerical
agreement and multi-process scaling are subsequent checks.

For a new scientific experiment, create and commit a named run's inputs before
submission. Record the project and Pencil revisions along with its outputs.
Use the project filesystem for this small test; confirm scratch access and
output storage before large production runs.
