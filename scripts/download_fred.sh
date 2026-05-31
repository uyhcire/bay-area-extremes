#!/usr/bin/env bash
#
# Download FRED (St. Louis Fed) time series as CSV.
# No API key required — uses the public fredgraph.csv route.
#
# Usage:
#   scripts/download_fred.sh SERIES_ID [SERIES_ID ...]
#   scripts/download_fred.sh --start YYYY-MM-DD --end YYYY-MM-DD SERIES_ID ...
#
# Examples:
#   scripts/download_fred.sh GDP UNRATE CPIAUCSL
#   scripts/download_fred.sh --start 2000-01-01 SFXRSA   # SF Case-Shiller HPI
#
set -euo pipefail

COSD=""
COED=""
SERIES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) COSD="$2"; shift 2 ;;
    --end)   COED="$2"; shift 2 ;;
    *)       SERIES+=("$1"); shift ;;
  esac
done

if [[ ${#SERIES[@]} -eq 0 ]]; then
  echo "usage: $0 [--start YYYY-MM-DD] [--end YYYY-MM-DD] SERIES_ID [SERIES_ID ...]" >&2
  exit 1
fi

OUTDIR="data/raw/fred"
mkdir -p "$OUTDIR"

range=""
[[ -n "$COSD" ]] && range="${range}&cosd=${COSD}"
[[ -n "$COED" ]] && range="${range}&coed=${COED}"

for id in "${SERIES[@]}"; do
  url="https://fred.stlouisfed.org/graph/fredgraph.csv?id=${id}${range}"
  echo "Downloading ${id}"
  curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${id}.csv" "$url"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
