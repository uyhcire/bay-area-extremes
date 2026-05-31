#!/usr/bin/env bash
#
# Download FHFA House Price Index (HPI) data. No API key required.
#
# Usage:
#   scripts/download_fhfa_hpi.sh
#
# Pulls the metro (CBSA) quarterly all-transactions index. The CSV has NO header
# row; columns are:
#   metro_name, cbsa_code, year, quarter, index_nsa, index_sa
# Missing values are "-". The San Francisco-Oakland-Berkeley CBSA is 41860.
#
# County-level ("developing-markets" bdl) and state files are linked from the
# FHFA HPI datasets page — the exact filenames change across releases:
#   https://www.fhfa.gov/data/hpi/datasets
#
set -euo pipefail

OUTDIR="data/raw/fhfa_hpi"
mkdir -p "$OUTDIR"
UA="bay-area-extremes/1.0 (research; eric@distyl.ai)"

url="https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv"
echo "Downloading FHFA metro HPI"
curl -fSL -A "$UA" --retry 4 --retry-delay 2 -o "${OUTDIR}/hpi_at_metro.csv" "$url"

echo "Done -> ${OUTDIR}/hpi_at_metro.csv"
wc -l "${OUTDIR}/hpi_at_metro.csv"
