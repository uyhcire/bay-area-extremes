#!/usr/bin/env bash
#
# Download California Dept. of Finance (DOF) population estimates.
# No API key required. DOF is the authoritative source for CA city/county
# population (more current and CA-specific than the Census Bureau).
#
# Usage:
#   scripts/download_dof_population.sh
#
# Downloads the E-1 table (population estimates for cities, counties, and the
# state). The exact filename bumps each year (E-1_<YEAR>_InternetVersion.xlsx),
# so this script scrapes the E-1 landing page for the current .xlsx link rather
# than hardcoding it. Each county sheet covers all 58 CA counties; pull the 9
# Bay Area rows. Other tables (E-2 components of change, E-5 city/county detail)
# are linked from https://dof.ca.gov/forecasting/demographics/estimates/
#
set -euo pipefail

OUTDIR="data/raw/dof_population"
mkdir -p "$OUTDIR"

PAGE="https://dof.ca.gov/forecasting/demographics/estimates-e1/"
echo "Resolving current E-1 file from ${PAGE}"
rel="$(curl -fsSL --retry 4 --retry-delay 2 "$PAGE" \
  | grep -oiE 'href="[^"]*E-1_[0-9]{4}_InternetVersion\.xlsx"' \
  | head -1 | sed 's/href="//;s/"//')"

if [[ -z "$rel" ]]; then
  echo "ERROR: could not find E-1 .xlsx link on the page (layout may have changed)." >&2
  echo "Check ${PAGE} manually." >&2
  exit 1
fi

# Make the link absolute if it is site-relative.
[[ "$rel" == /* ]] && url="https://dof.ca.gov${rel}" || url="$rel"
fname="$(basename "$rel")"

echo "Downloading ${fname}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${fname}" "$url"

echo "Done -> ${OUTDIR}/${fname}"
ls -lh "${OUTDIR}/${fname}"
