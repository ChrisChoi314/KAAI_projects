#!/bin/bash -l
#SBATCH --job-name=mixed-flow-check
#SBATCH --partition=RM
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:20:00
#SBATCH --output=flow-check-%j.log
set -eo pipefail
cd "$SLURM_SUBMIT_DIR"
module load anaconda3/2020.07
source /hildafs/projects/phy210003p/choic/software/pencil-code/sourceme.sh
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MPLCONFIGDIR="${TMPDIR:-/tmp}/kaai-flow-$SLURM_JOB_ID"
python analysis/inspect_mixed_flow.py "${1:-runs/mixed-turbulence-kt}"
