#!/bin/bash -l
#SBATCH --job-name=d6-half-cfl
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=d6-half-cfl-%j.log
set -eo pipefail
repo="$SLURM_SUBMIT_DIR"
module load gcc/11.2.0 mpi/4.1.1-gcc11.2.0
export OMP_NUM_THREADS=1
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh
cd "$repo/runs/experiment-turbulence-d6-half-cfl"
if [ -e data/proc0/VAR0 ]; then echo 'Already initialized; refusing overwrite'; exit 2; fi
pc_setupsrc
pc_start -f GNU-GCC_MPI
pc_run -f GNU-GCC_MPI run
test -f COMPLETED
echo 'D6 HALF-CFL SIMULATION COMPLETE'
