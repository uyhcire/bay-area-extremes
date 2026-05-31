#!/usr/bin/env bash
#
# Download census-tract life expectancy from NCHS USALEEP (U.S. Small-area Life
# Expectancy Estimates Project, 2010-2015). No API key required.
#
# This is the standard tract-level life-expectancy dataset CDPH itself points
# to for California; the national project publishes a per-state file.
#
# Usage:
#   scripts/download_life_expectancy_tract.sh [ST]
#
#   ST   2-letter state abbrev (default: CA)
#
# Pulls the "A" file: life expectancy at birth, e(0), by census tract, with
# standard error. Columns:
#   Tract ID, STATE2KX, CNTY2KX, TRACT2KX, e(0), se(e(0)), Abridged life table flag
# CNTY2KX = county FIPS (Bay Area: 001 013 041 055 075 081 085 095 097).
# Record layout: https://www.cdc.gov/nchs/data/nvss/usaleep/Record_Layout_CensusTract_Life_Expectancy.pdf
#
set -euo pipefail

ST="${1:-CA}"
OUTDIR="data/raw/life_expectancy_tract"
mkdir -p "$OUTDIR"

base="https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV"
url="${base}/${ST}_A.CSV"
echo "Downloading USALEEP tract life expectancy for ${ST}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${ST}_A.csv" "$url"

echo "Done -> ${OUTDIR}/${ST}_A.csv"
wc -l "${OUTDIR}/${ST}_A.csv"
