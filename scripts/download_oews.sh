#!/usr/bin/env bash
#
# Download BLS OEWS (Occupational Employment and Wage Statistics) metro files.
# No API key required, BUT www.bls.gov rejects requests without a descriptive
# User-Agent (returns HTTP 403) — this script sends one.
#
# Usage:
#   scripts/download_oews.sh [YY]
#
#   YY   2-digit data year (default: 23 = May 2023 estimates)
#
# Downloads the metropolitan-area estimates archive `oesm<YY>ma.zip` and unzips
# it. Inside are wage estimates (mean + 10/25/50/75/90th percentiles) by
# occupation for every MSA. Bay Area MSA codes include 41860 (SF-Oakland-
# Berkeley) and 41940 (San Jose-Sunnyvale-Santa Clara).
# Catalog: https://www.bls.gov/oes/tables.htm
#
set -euo pipefail

YY="${1:-23}"
OUTDIR="data/raw/oews_${YY}"
mkdir -p "$OUTDIR"
UA="bay-area-extremes/1.0 (research; eric@distyl.ai)"

zip="oesm${YY}ma.zip"
url="https://www.bls.gov/oes/special-requests/${zip}"
echo "Downloading OEWS metro estimates ${zip}"
curl -fSL -A "$UA" --retry 4 --retry-delay 2 -o "${OUTDIR}/${zip}" "$url"

echo "Unzipping ${zip}"
unzip -o "${OUTDIR}/${zip}" -d "$OUTDIR"

echo "Done. Files in ${OUTDIR}:"
ls -lhR "$OUTDIR" | head -30
