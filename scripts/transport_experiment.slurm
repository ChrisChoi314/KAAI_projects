#!/bin/bash -l
#SBATCH --job-name=transport-run
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=3
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=transport-%j.log
# One method per allocation. A successful build job must precede this job.
set -eo pipefail
repo="$SLURM_SUBMIT_DIR"
case_name="${1:?Specify shock, smooth, or turbulence}"
method="${2:?Specify kt, d6, or adaptive}"
case "$case_name" in
  shock|smooth) expected_tasks=3 ;;
  turbulence) expected_tasks=4 ;;
  *) echo 'Unknown case'; exit 2 ;;
esac
case "$method" in kt|d6|adaptive) ;; *) echo 'Unknown method'; exit 2 ;; esac
if [ "$SLURM_NTASKS" -ne "$expected_tasks" ]; then
  echo "Submit with --ntasks=$expected_tasks for $case_name"; exit 2
fi
module load gcc/11.2.0 mpi/4.1.1-gcc11.2.0
export OMP_NUM_THREADS=1
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh
run_dir="$repo/runs/experiment-$case_name-$method"
test -f "$run_dir/experiment.json"
if [ -e "$run_dir/data/proc0/VAR0" ]; then
  echo "Refusing to restart existing initialized run: $run_dir"; exit 2
fi
cd "$run_dir"
pc_setupsrc
if [ "$method" != kt ]; then
  cp "$repo/runs/experiment-$case_name-kt/src/start.x" src/start.x
  cp "$repo/runs/experiment-$case_name-kt/src/run.x" src/run.x
fi
test -x src/start.x
test -x src/run.x
echo "INITIALIZING $case_name $method"
pc_start -f GNU-GCC_MPI
test -s data/proc0/VAR0
echo "EVOLVING $case_name $method"
pc_run -f GNU-GCC_MPI run
test -f COMPLETED
echo "COMPLETED $case_name $method"
tail -n 3 data/time_series.dat
