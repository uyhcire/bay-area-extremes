#!/usr/bin/env bash
#
# Download CDC PLACES county-level health measures. No API key required —
# uses the CDC Socrata open-data CSV endpoint.
#
# Usage:
#   scripts/download_cdc_places.sh [STATE_ABBR]
#
#   STATE_ABBR   2-letter state filter (default: CA). Use ALL for the nation.
#
# Dataset swc5-untb = "PLACES: County Data". Long format: one row per
# county x measure (e.g. obesity, diabetes, no health insurance, poor mental
# health). Filter to the Bay Area by `locationname` (county) or `locationid`
# (county FIPS) afterward. Socrata caps rows per request, so we page with
# $limit/$offset. Browse: https://data.cdc.gov/d/swc5-untb
#
set -euo pipefail

STATE="${1:-CA}"
OUTDIR="data/raw/cdc_places"
mkdir -p "$OUTDIR"
out="${OUTDIR}/places_county_${STATE}.csv"

base="https://data.cdc.gov/resource/swc5-untb.csv"
where=""
[[ "$STATE" != "ALL" ]] && where="&\$where=stateabbr='${STATE}'"

limit=50000
offset=0
: > "$out"
while : ; do
  url="${base}?\$limit=${limit}&\$offset=${offset}&\$order=:id${where}"
  tmp="$(mktemp)"
  curl -fSL --retry 4 --retry-delay 2 -o "$tmp" "$url"
  rows=$(($(wc -l < "$tmp") - 1))   # minus header
  if [[ $offset -eq 0 ]]; then
    cat "$tmp" > "$out"             # keep header on first page
  else
    tail -n +2 "$tmp" >> "$out"     # drop header on later pages
  fi
  rm -f "$tmp"
  echo "  fetched ${rows} rows at offset ${offset}"
  [[ $rows -lt $limit ]] && break
  offset=$((offset + limit))
done

echo "Done -> ${out}"
wc -l "$out"
