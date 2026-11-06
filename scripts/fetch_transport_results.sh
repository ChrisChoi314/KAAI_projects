#!/bin/bash
# On the Mac, download only exports whose completion marker is present.
set -euo pipefail
manifest=$(mktemp)
trap 'rm -f "$manifest"' EXIT
ssh choic@vera.psc.edu 'for method in kt d6 adaptive; do
  base="/hildafs/projects/phy210003p/choic/KAAI_projects/runs/experiment-turbulence-$method/data"
  if [ -f "$base/export_complete.txt" ]; then
    for name in time_series.dat powerv.dat transport_usage.dat velocity_components.dat velocity_component_summary.dat experiment.json export_complete.txt; do
      if [ -f "$base/$name" ]; then
        printf "experiment-turbulence-%s/data/%s\n" "$method" "$name"
      fi
    done
  fi
done
true' > "$manifest"
if [ ! -s "$manifest" ]; then
  echo 'No completed exports yet. Run this command again after an export finishes.'
  exit 0
fi
rsync -av --files-from="$manifest" \
  choic@vera.psc.edu:/hildafs/projects/phy210003p/choic/KAAI_projects/runs/ runs/
