#!/usr/bin/env bash
#
# Download Census metro/CSA geography reference files. No API key required.
#
# Usage:
#   scripts/download_csa_geography.sh
#
# Fetches two things needed to roll counties up to Combined Statistical Areas
# (CSAs) and to rank CSAs by size:
#
#   1. OMB/Census delineation file (list1) — the county -> CBSA -> CSA crosswalk.
#      Columns include `CSA Code`, `CSA Title`, `FIPS State Code`,
#      `FIPS County Code`. Reflects the 2023 vintage (CT counties replaced by
#      planning regions).
#   2. PEP CSA population estimates (csa-est2023-alldata) — one row per CSA
#      (LSAD == "Combined Statistical Area") with POPESTIMATE2020..2023, used to
#      pick the largest CSAs.
#
# Both are official Census Bureau files.
set -euo pipefail

OUTDIR="data/raw/csa_geography"
mkdir -p "$OUTDIR"

DELIN_URL="https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx"
POP_URL="https://www2.census.gov/programs-surveys/popest/datasets/2020-2023/metro/totals/csa-est2023-alldata.csv"

echo "Fetching CSA delineation crosswalk"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/delineation_list1_2023.xlsx" "$DELIN_URL"

echo "Fetching CSA population estimates"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/csa_population_2023.csv" "$POP_URL"

echo "Done -> ${OUTDIR}/"
ls -la "$OUTDIR"
