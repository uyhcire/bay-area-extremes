#!/usr/bin/env bash
#
# Download IRS SOI (Statistics of Income) data — no API key required.
#   - County-to-county migration flows (inflow + outflow)
#   - ZIP-code-level individual income tax statistics (AGI bands)
#
# Usage:
#   scripts/download_irs_soi.sh [MIGRATION_PAIR] [ZIP_YEAR]
#
#   MIGRATION_PAIR  4-digit consecutive-year pair (default: 2122 = TY2021->2022)
#   ZIP_YEAR        2-digit tax year for ZIP data  (default: 21 = TY2021)
#
# Examples:
#   scripts/download_irs_soi.sh                # 2021->2022 migration + 2021 ZIP
#   scripts/download_irs_soi.sh 2021 20        # 2020->2021 migration + 2020 ZIP
#
# Notes:
#   - Migration files cover ALL U.S. counties in one CSV; filter to CA (state
#     FIPS 06) / Bay Area county FIPS yourself afterward.
#   - ZIP file `<yy>zpallagi.csv` is national; California ZIPs start 94/95.
#
set -euo pipefail

MIG="${1:-2122}"
ZY="${2:-21}"

BASE="https://www.irs.gov/pub/irs-soi"
OUTDIR="data/raw/irs_soi"
mkdir -p "$OUTDIR"

for f in "countyinflow${MIG}.csv" "countyoutflow${MIG}.csv" "${ZY}zpallagi.csv"; do
  echo "Downloading ${f}"
  curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${f}" "${BASE}/${f}"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
