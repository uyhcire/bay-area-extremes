#!/usr/bin/env bash
#
# Download BLS LAUS (Local Area Unemployment Statistics) flat files.
# No API key required, BUT download.bls.gov rejects requests without a
# descriptive User-Agent (returns HTTP 403) — this script sends one.
#
# Usage:
#   scripts/download_laus.sh
#
# Pulls the California series data file plus the reference (mapping) files
# needed to decode it:
#   la.data.11.California  - all CA series observations (counties, metros, state)
#   la.series              - series_id -> area/measure metadata
#   la.area                - area codes -> names
#   la.area_type           - area-type codes
#   la.measure             - measure codes (unemployment rate, employment, etc.)
#
# Series IDs encode area + measure; join on la.series / la.area to pull the 9
# Bay Area counties or the SF/San Jose metro divisions.
# Reference: https://download.bls.gov/pub/time.series/la/la.txt
#
set -euo pipefail

BASE="https://download.bls.gov/pub/time.series/la"
OUTDIR="data/raw/laus"
mkdir -p "$OUTDIR"
UA="bay-area-extremes/1.0 (research; eric@distyl.ai)"

for f in la.data.11.California la.series la.area la.area_type la.measure; do
  echo "Downloading ${f}"
  curl -fSL -A "$UA" --retry 4 --retry-delay 2 -o "${OUTDIR}/${f}" "${BASE}/${f}"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
