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
