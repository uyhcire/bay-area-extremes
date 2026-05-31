#!/usr/bin/env bash
#
# Download Census BDS (Business Dynamics Statistics) — annual firm/establishment
# births, deaths, job creation/destruction. No API key required for the bulk
# CSV tables (the Census Data API timeseries/bds route DOES require a key).
#
# Usage:
#   scripts/download_bds.sh [YEAR]
#
#   YEAR   most recent data year in the release (default: 2022)
#
# Downloads the state-by-county time-series table `bds<YEAR>_st_cty.csv`, which
# contains all years up to <YEAR> for every state/county. Filter to California
# (st==06) / the 9 Bay Area county codes (cty).
# Catalog: https://www.census.gov/data/datasets/time-series/econ/bds/bds-datasets.html
#
set -euo pipefail

YEAR="${1:-2022}"
OUTDIR="data/raw/bds"
mkdir -p "$OUTDIR"

f="bds${YEAR}_st_cty.csv"
url="https://www2.census.gov/programs-surveys/bds/tables/time-series/${YEAR}/${f}"
echo "Downloading BDS state-county table ${f}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${f}" "$url"

echo "Done -> ${OUTDIR}/${f}"
wc -l "${OUTDIR}/${f}"
