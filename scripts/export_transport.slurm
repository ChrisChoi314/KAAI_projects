#!/bin/bash -l
#SBATCH --job-name=transport-export
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=export-%j.log
set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
module load anaconda3/2020.07
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MPLCONFIGDIR="${TMPDIR:-/tmp}/kaai-matplotlib-$SLURM_JOB_ID"
case_name="${1:?Specify case}"
methods="${2:-kt d6 adaptive}"
for method in $methods; do
  case "$method" in kt|d6|adaptive) ;; *) echo 'Unknown method'; exit 2 ;; esac
  test -f "runs/experiment-$case_name-$method/COMPLETED"
  python analysis/export_transport_results.py "runs/experiment-$case_name-$method"
done
echo 'EXPORT COMPLETE'
