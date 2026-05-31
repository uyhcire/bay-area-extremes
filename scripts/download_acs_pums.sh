#!/usr/bin/env bash
#
# Download ACS PUMS (Census Public Use Microdata Sample) bulk CSV files.
# No API key required — pulls the bulk ZIPs from www2.census.gov.
#
# Usage:
#   scripts/download_acs_pums.sh [YEAR] [SPAN] [STATE] [REC]
#
#   YEAR   ACS reference year         (default: 2022)
#   SPAN   "1-Year" or "5-Year"       (default: 1-Year)
#   STATE  lowercase 2-letter abbrev  (default: ca)
#   REC    "p" persons / "h" housing  (default: p)
#
# Examples:
#   scripts/download_acs_pums.sh                 # CA 2022 1-yr persons
#   scripts/download_acs_pums.sh 2022 1-Year ca h   # + housing records
#   scripts/download_acs_pums.sh 2022 5-Year ca p   # 5-year persons
#
set -euo pipefail

YEAR="${1:-2022}"
SPAN="${2:-1-Year}"
STATE="${3:-ca}"
REC="${4:-p}"

BASE="https://www2.census.gov/programs-surveys/acs/data/pums"
OUTDIR="data/raw/acs_pums_${YEAR}_${SPAN,,}"
mkdir -p "$OUTDIR"

zip="csv_${REC}${STATE}.zip"
url="${BASE}/${YEAR}/${SPAN}/${zip}"

echo "Downloading ${url}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${zip}" "$url"

# Companion data dictionary (variable names + value codes).
dict="PUMS_Data_Dictionary_${YEAR}.csv"
echo "Downloading data dictionary ${dict}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${dict}" \
  "${BASE}/${YEAR}/${SPAN}/${dict}" || \
  echo "  (data dictionary not found at that path — check ${BASE}/${YEAR}/${SPAN}/)"

echo "Unzipping ${zip}"
unzip -o "${OUTDIR}/${zip}" -d "$OUTDIR"

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
