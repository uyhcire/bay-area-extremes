#!/usr/bin/env bash
#
# Download HMDA (Home Mortgage Disclosure Act) loan-level records as CSV.
# No API key required — uses the CFPB HMDA Data Browser CSV export API.
#
# Usage:
#   scripts/download_hmda.sh [YEAR] [COUNTY_FIPS ...]
#
#   YEAR         HMDA data year                   (default: 2022)
#   COUNTY_FIPS  5-digit county FIPS code(s)       (default: 9 Bay Area counties)
#
# Examples:
#   scripts/download_hmda.sh                       # Bay Area, 2022
#   scripts/download_hmda.sh 2023 06075            # SF County, 2023
#   scripts/download_hmda.sh 2022 06001 06085      # Alameda + Santa Clara
#
# Notes:
#   - The API streams a generated CSV (a 301 -> files.ffiec.cfpb.gov redirect,
#     so -L is required). Statewide pulls are large; filtering by county keeps
#     files manageable.
#   - Other filters the API accepts: &actions_taken= &loan_types= &races= etc.
#     See https://ffiec.cfpb.gov/data-browser/  (Data Browser).
#
set -euo pipefail

YEAR="${1:-2022}"
shift || true
BAY_AREA=(06001 06013 06041 06055 06075 06081 06085 06097 06095)
COUNTIES=("$@")
[[ ${#COUNTIES[@]} -eq 0 ]] && COUNTIES=("${BAY_AREA[@]}")

# Join county codes with commas for the API.
IFS=','; counties_csv="${COUNTIES[*]}"; unset IFS

OUTDIR="data/raw/hmda"
mkdir -p "$OUTDIR"
out="${OUTDIR}/hmda_${YEAR}_$(echo "$counties_csv" | tr ',' '-').csv"

url="https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?counties=${counties_csv}&years=${YEAR}"
echo "Downloading HMDA ${YEAR} for counties ${counties_csv}"
curl -fSL --retry 4 --retry-delay 2 -o "$out" "$url"

echo "Done -> ${out}"
wc -l "$out"
