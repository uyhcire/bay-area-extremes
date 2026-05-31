#!/usr/bin/env bash
#
# Download county-level U.S. presidential election returns. No API key required.
#
# Usage:
#   scripts/download_election_returns.sh [YEAR ...]
#
#   YEAR   Presidential election year(s) to fetch (default: 2024 2020 2016).
#
# Source: the widely-used `tonmcg/US_County_Level_Election_Results_08-24`
# compilation of Associated Press / state-certified county returns. There is no
# single official .gov CSV of county presidential results, so this third-party
# aggregation (popular for exactly this kind of geographic analysis) is used.
# Each file is one row per county with columns:
#   state_name, county_fips, county_name, votes_gop, votes_dem, total_votes, ...
#
# County FIPS are 5-digit. NOTE: the 2024 file already uses Connecticut's new
# planning-region FIPS (091x0), matching the 2023 Census delineation; the 2016
# and 2020 files still use Connecticut's legacy county FIPS (0900x), which will
# not join to the 2023 CSA crosswalk for CT.
set -euo pipefail

YEARS=("$@")
[[ ${#YEARS[@]} -eq 0 ]] && YEARS=(2024 2020 2016)

OUTDIR="data/raw/election_returns"
mkdir -p "$OUTDIR"

base="https://raw.githubusercontent.com/tonmcg/US_County_Level_Election_Results_08-24/master"

for year in "${YEARS[@]}"; do
  url="${base}/${year}_US_County_Level_Presidential_Results.csv"
  out="${OUTDIR}/county_presidential_${year}.csv"
  echo "Fetching ${year} -> ${out}"
  curl -fSL --retry 4 --retry-delay 2 -o "$out" "$url"
  echo "  $(($(wc -l < "$out") - 1)) counties"
done

echo "Done -> ${OUTDIR}/"
