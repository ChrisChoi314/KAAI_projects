#!/bin/bash -l
#SBATCH --job-name=transport-build
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:30:00
#SBATCH --output=build-%j.log
set -eo pipefail
repo="$SLURM_SUBMIT_DIR"
case_name="${1:?Specify shock, smooth, or turbulence}"
case "$case_name" in shock|smooth|turbulence) ;; *) exit 2 ;; esac
module load gcc/11.2.0 mpi/4.1.1-gcc11.2.0
export OMP_NUM_THREADS=1
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh
cd "$repo/runs/experiment-$case_name-kt"
# Reusing one binary is valid only when all compile-time inputs match.
for method in d6 adaptive; do
  for file in cparam.local Makefile.local kt_transport_experiment.f90; do
    cmp "src/$file" "$repo/runs/experiment-$case_name-$method/src/$file"
  done
done
pc_setupsrc
pc_build -f GNU-GCC_MPI
test -x src/start.x
test -x src/run.x
echo "BUILD COMPLETE $case_name"
