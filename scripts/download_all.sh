#!/usr/bin/env bash
#
# Run every download_*.sh with default (Bay Area / California) parameters,
# regenerating the full local raw cache under data/raw/ (git-ignored, ~1.6 GB).
#
# Usage:
#   scripts/download_all.sh            # run all sources
#   scripts/download_all.sh --list     # print the steps and exit (no downloads)
#
# Each source runs as an independent step: a failure is logged and the run
# continues. Per-step output goes to data/raw/_logs/<step>.log. A summary
# (OK / FAIL / SKIP) prints at the end; the exit code is non-zero if any step
# failed. BEA is SKIPped automatically when BEA_API_KEY is not set.
#
set -uo pipefail   # deliberately NOT -e: we want to continue past failures

cd "$(dirname "$0")/.."   # repo root
HERE="scripts"

# Each entry is a full command line (script + default args).
STEPS=(
  "download_acs_pums.sh"
  "download_fred.sh GDP UNRATE SFXRSA CASANF0URN"
  "download_qcew.sh"
  "download_bea.sh"
  "download_hmda.sh"
  "download_irs_soi.sh"
  "download_zillow.sh"
  "download_fhfa_hpi.sh"
  "download_census_bps.sh"
  "download_laus.sh"
  "download_oews.sh"
  "download_cbp.sh"
  "download_bds.sh"
  "download_lodes.sh"
  "download_cdc_places.sh"
  "download_cdph_vital.sh"
  "download_life_expectancy_tract.sh"
  "download_dof_population.sh"
)

if [[ "${1:-}" == "--list" ]]; then
  echo "Steps (${#STEPS[@]}):"
  for s in "${STEPS[@]}"; do echo "  ${HERE}/${s}"; done
  exit 0
fi

LOGDIR="data/raw/_logs"
mkdir -p "$LOGDIR"

declare -a RESULTS=()
fail_count=0

for step in "${STEPS[@]}"; do
  name="${step%% *}"; name="${name%.sh}"          # script basename without .sh
  log="${LOGDIR}/${name}.log"

  # BEA needs a key — skip cleanly rather than fail when it is absent.
  if [[ "$step" == download_bea.sh* && -z "${BEA_API_KEY:-}" ]]; then
    echo "SKIP  ${name}  (BEA_API_KEY not set)"
    RESULTS+=("SKIP  ${name}")
    continue
  fi

  printf 'RUN   %-28s ' "$name"
  read -ra parts <<< "$step"          # split "script.sh arg1 arg2" into an array
  start=$(date +%s)
  if "${HERE}/${parts[0]}" "${parts[@]:1}" >"$log" 2>&1; then
    elapsed=$(( $(date +%s) - start ))
    echo "OK   (${elapsed}s)"
    RESULTS+=("OK    ${name}")
  else
    elapsed=$(( $(date +%s) - start ))
    echo "FAIL (${elapsed}s) — see ${log}"
    tail -3 "$log" | sed 's/^/        | /'
    RESULTS+=("FAIL  ${name}")
    fail_count=$((fail_count + 1))
  fi
done

echo ""
echo "===================== SUMMARY ====================="
for r in "${RESULTS[@]}"; do echo "  $r"; done
echo "==================================================="
echo "Raw cache size: $(du -sh data/raw 2>/dev/null | cut -f1)"
[[ $fail_count -gt 0 ]] && { echo "${fail_count} step(s) failed."; exit 1; }
echo "All steps OK (skips are not failures)."
