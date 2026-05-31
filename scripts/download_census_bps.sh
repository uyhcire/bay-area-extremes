#!/usr/bin/env bash
#
# Download Census Building Permits Survey (BPS) — county annual new-housing
# permits. No API key required.
#
# Usage:
#   scripts/download_census_bps.sh [YEAR]
#
#   YEAR   permit year (default: 2022)
#
# The county file `co<YEAR>a.txt` is a national fixed-layout CSV (the first two
# rows are a split header). Filter to California (state FIPS 6) / the 9 Bay Area
# county FIPS afterward. Column layout reference:
#   https://www2.census.gov/econ/bps/County/ (see the *Documentation* files)
#
set -euo pipefail

YEAR="${1:-2022}"
OUTDIR="data/raw/census_bps"
mkdir -p "$OUTDIR"

url="https://www2.census.gov/econ/bps/County/co${YEAR}a.txt"
echo "Downloading Census BPS county permits ${YEAR}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/co${YEAR}a.csv" "$url"

echo "Done -> ${OUTDIR}/co${YEAR}a.csv"
wc -l "${OUTDIR}/co${YEAR}a.csv"
