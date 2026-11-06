#!/bin/bash -l
#SBATCH --job-name=mixed-kt
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:30:00
#SBATCH --output=evolve-%j.log

set -e
cd "$SLURM_SUBMIT_DIR"

module load gcc/11.2.0 mpi/4.1.1-gcc11.2.0
export OMP_NUM_THREADS=1
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh

pc_run -f GNU-GCC_MPI run

test -f COMPLETED
echo "SIMULATION COMPLETE"
tail -n 3 data/time_series.dat
