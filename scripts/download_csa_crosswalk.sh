#!/usr/bin/env bash
#
# Download the reference files needed to roll Zillow's CBSA-level series up to
# Combined Statistical Areas (CSAs):
#
#   1. Census/OMB delineation file  — county FIPS -> CBSA -> CSA crosswalk
#   2. Census county population est. — to rank CSAs by size and weight the roll-up
#
# No API key required. Both are public CSV/XLSX at www2.census.gov.
#
# Usage:
#   scripts/download_csa_crosswalk.sh
#
# Writes to data/raw/xwalk/ (git-ignored). Pair with scripts/rank_csa.py, which
# joins these to the Zillow County_zhvi / County_zori files by county FIPS.
#
set -euo pipefail

OUTDIR="data/raw/xwalk"
mkdir -p "$OUTDIR"

# OMB July 2023 delineation (List 1: CBSAs, Metro Divisions, and CSAs).
# Columns of interest: CBSA Code, CSA Code, CBSA Title, CSA Title,
# FIPS State Code, FIPS County Code.
DELINEATION="https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx"

# Vintage 2023 county population estimates (SUMLEV 050 = county).
POPEST="https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/counties/totals/co-est2023-alldata.csv"

echo "Downloading delineation crosswalk -> ${OUTDIR}/delineation.xlsx"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/delineation.xlsx" "$DELINEATION"

echo "Downloading county population estimates -> ${OUTDIR}/co-est.csv"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/co-est.csv" "$POPEST"

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
