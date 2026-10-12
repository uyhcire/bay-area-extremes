#!/usr/bin/env bash
#
# Download CPS ASEC (March Annual Social and Economic Supplement) public-use
# microdata straight from the Census Bureau. No key required.
#
# This is the keyless route to the same person records IPUMS CPS distributes
# (IPUMS needs a separate CPS registration on top of the API key). For 2001
# the script fetches the SCHIP-expanded file (chip2001pub), which is the file
# IPUMS uses for its 2001 ASEC sample (218,269 persons).
#
# Usage:
#   scripts/download_cps_asec.sh [SURVEY_YEAR ...]   # default: 2001 2010 2019 2025
#
# Formats differ by year: 2019+ ship as CSV zips (pppub<yy>.csv is the person
# file); earlier years are hierarchical fixed-width .dat files (record type in
# column 1: 1=household, 2=family, 3=person). Record layouts are in
#   https://www2.census.gov/programs-surveys/cps/techdocs/cpsmar<yy>.pdf
# analysis/gender_wage_ratios/build_extract.py parses both into IPUMS names.
#
set -euo pipefail

OUTDIR="data/raw/census_cps_asec"
BASE="https://www2.census.gov/programs-surveys/cps/datasets"
mkdir -p "$OUTDIR"

fetch() {
  local url="$1" out="$OUTDIR/$(basename "$1")"
  if [[ -s "$out" ]]; then echo "  have $out"; return; fi
  echo "  GET $url"
  curl -fsS --retry 4 --retry-delay 2 -o "$out" "$url"
}

YEARS=("$@")
[[ ${#YEARS[@]} -eq 0 ]] && YEARS=(2001 2010 2019 2025)

for y in "${YEARS[@]}"; do
  yy="${y:2:2}"
  echo "ASEC $y:"
  if (( y >= 2019 )); then
    fetch "$BASE/$y/march/asecpub${yy}csv.zip"
  elif (( y == 2001 )); then
    fetch "$BASE/$y/march/chip2001pub.cps.gz"
  else
    fetch "$BASE/$y/march/asec${y}_pubuse.dat.gz"
  fi
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
