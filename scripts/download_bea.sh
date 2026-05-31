#!/usr/bin/env bash
#
# Download BEA (Bureau of Economic Analysis) Regional data via the BEA API.
# REQUIRES a free UserID — there is no key-free route.
#   Register: https://apps.bea.gov/API/signup/
#   Then:     export BEA_API_KEY=<your-userid>
#
# Usage:
#   scripts/download_bea.sh [TABLE] [LINECODE] [GEOFIPS] [YEAR]
#
#   TABLE     Regional table name   (default: CAINC1  = personal income summary)
#   LINECODE  line within the table (default: 3       = per-capita personal income)
#   GEOFIPS   geography code        (default: 41860   = SF-Oakland-Berkeley MSA)
#   YEAR      year or "ALL"         (default: ALL)
#
# Examples:
#   scripts/download_bea.sh                          # SF MSA per-capita income, all years
#   scripts/download_bea.sh CAINC1 3 06075 ALL       # SF County
#   scripts/download_bea.sh CAGDP2 1 41860 ALL       # SF MSA real GDP
#
# Tip: enumerate valid tables/lines/geofips with method=GetParameterValues, e.g.
#   curl "https://apps.bea.gov/api/data?&UserID=$BEA_API_KEY&method=GetParameterValues&datasetname=Regional&ParameterName=TableName&ResultFormat=json"
#
set -euo pipefail

if [[ -z "${BEA_API_KEY:-}" ]]; then
  echo "ERROR: BEA_API_KEY is not set." >&2
  echo "Register a free UserID at https://apps.bea.gov/API/signup/ then:" >&2
  echo "  export BEA_API_KEY=<your-userid>" >&2
  exit 1
fi

TABLE="${1:-CAINC1}"
LINECODE="${2:-3}"
GEOFIPS="${3:-41860}"
YEAR="${4:-ALL}"

OUTDIR="data/raw/bea"
mkdir -p "$OUTDIR"
out="${OUTDIR}/${TABLE}_line${LINECODE}_${GEOFIPS}_${YEAR}.json"

url="https://apps.bea.gov/api/data?&UserID=${BEA_API_KEY}&method=GetData&datasetname=Regional&TableName=${TABLE}&LineCode=${LINECODE}&GeoFips=${GEOFIPS}&Year=${YEAR}&ResultFormat=json"

echo "Downloading BEA ${TABLE} line ${LINECODE} for ${GEOFIPS} (${YEAR})"
curl -fSL --retry 4 --retry-delay 2 -o "$out" "$url"

# Surface API-level errors (BEA returns HTTP 200 even on bad requests).
if grep -q '"Error"' "$out"; then
  echo "WARNING: BEA returned an error payload:" >&2
  cat "$out" >&2
  exit 1
fi

echo "Done -> ${out}"
