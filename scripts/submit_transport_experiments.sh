#!/bin/bash
# On Vera, from repo root. Builds and method runs use separate dependencies.
set -euo pipefail
case_list="${*:-turbulence}"
# Validate the requested set/order before any jobs are submitted.
seen_cases=' '
for case_name in $case_list; do
  case "$case_name" in shock|smooth|turbulence) ;; *) echo "Unknown case: $case_name"; exit 2 ;; esac
  case "$seen_cases" in *" $case_name "*) echo "Duplicate case: $case_name"; exit 2 ;; esac
  seen_cases="$seen_cases$case_name "
  for method in kt d6 adaptive; do
    run="runs/experiment-$case_name-$method"
    test -f "$run/experiment.json"
    if [ -e "$run/data/proc0/VAR0" ]; then
      echo "Already initialized: $run. Refusing duplicate submission."; exit 2
    fi
  done
done
# Guard against a second invocation while jobs are pending/running.
active=$(squeue -h -u "$USER" -o '%j' | awk '/^transport-/ {print}')
if [ -n "$active" ]; then
  echo 'Transport jobs already queued; refusing duplicate submission:'
  echo "$active"; exit 2
fi
# Compile all requested cases concurrently. Save IDs in a temporary manifest.
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
for case_name in $case_list; do
  build_job=$(sbatch --parsable --job-name="transport-build-$case_name" scripts/build_transport.slurm "$case_name")
  build_job=${build_job%%;*}
  printf '%s %s\n' "$case_name" "$build_job" >> "$manifest"
  printf '%s: build job %s\n' "$case_name" "$build_job"
done
# Canonical order ensures any requested control dependencies are known first.
control_jobs=''
for case_name in shock smooth turbulence; do
  build_job=$(awk -v name="$case_name" '$1==name {print $2}' "$manifest")
  if [ -z "$build_job" ]; then continue; fi
  case "$case_name" in shock|smooth) tasks=3 ;; turbulence) tasks=4 ;; esac
  dependency="$build_job"
  if [ "$case_name" = turbulence ] && [ -n "$control_jobs" ]; then
    dependency="$dependency:$control_jobs"
  fi
  method_jobs=''
  for method in kt d6 adaptive; do
    run_job=$(sbatch --parsable --ntasks="$tasks" --job-name="transport-$case_name-$method" \
      --dependency="afterok:$dependency" scripts/transport_experiment.slurm "$case_name" "$method")
    run_job=${run_job%%;*}
    if [ -z "$method_jobs" ]; then method_jobs="$run_job"; else method_jobs="$method_jobs:$run_job"; fi
    printf '%s %s: simulation job %s\n' "$case_name" "$method" "$run_job"
    export_job=$(sbatch --parsable --job-name="transport-export-$case_name-$method" \
      --dependency="afterok:$run_job" scripts/export_transport.slurm "$case_name" "$method")
    printf '%s %s: export job %s\n' "$case_name" "$method" "${export_job%%;*}"
  done
  if [ "$case_name" != turbulence ]; then
    if [ -z "$control_jobs" ]; then control_jobs="$method_jobs"; else control_jobs="$control_jobs:$method_jobs"; fi
  fi
done
