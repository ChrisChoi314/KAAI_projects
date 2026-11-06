#!/bin/bash -l
#SBATCH --job-name=pencil-jeans
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=vera-jeans-%j.log

# Submit from the repository root: sbatch scripts/vera-jeans.slurm
set -e
cd "$SLURM_SUBMIT_DIR"
REPO_DIR="$PWD"
test -f runs/jeans-x/start.in
test -f runs/jeans-x/src/cparam.local

module load gcc/11.2.0 mpi/4.1.1-gcc11.2.0
export OMP_NUM_THREADS=1
export PENCIL_HOME="${VERA_PENCIL_HOME:-/hildafs/projects/phy210003p/choic/software/pencil-code}"
source "$PENCIL_HOME/sourceme.sh"

# Each submission gets a fresh directory; preserve the tracked baseline.
RUN_DIR="$REPO_DIR/runs/jeans-vera-$SLURM_JOB_ID"
mkdir "$RUN_DIR"
mkdir "$RUN_DIR/src" "$RUN_DIR/data"
cp "$REPO_DIR"/runs/jeans-x/*.in "$RUN_DIR/"
cp "$REPO_DIR"/runs/jeans-x/src/*.local "$RUN_DIR/src/"
sed -i 's/nompicomm/mpicomm/' "$RUN_DIR/src/Makefile.local"

module list
echo "Project revision: $(git -C "$REPO_DIR" rev-parse HEAD)"
git -C "$REPO_DIR" status --short
echo "Pencil revision: $(git -C "$PENCIL_HOME" rev-parse HEAD)"
echo "Run directory: $RUN_DIR"

cd "$RUN_DIR"
pc_setupsrc
pc_build -f GNU-GCC_MPI
pc_run -f GNU-GCC_MPI

test -f COMPLETED
test -s data/time_series.dat
echo "PENCIL TEST COMPLETED"
tail -n 5 data/time_series.dat
