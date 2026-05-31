#!/usr/bin/env bash
#
# Download QCEW (BLS Quarterly Census of Employment and Wages) area CSV files.
# No API key required — uses the BLS open data API.
#
# Usage:
#   scripts/download_qcew.sh [YEAR] [QTR] [AREA_FIPS ...]
#
#   YEAR       reference year                  (default: 2022)
#   QTR        1|2|3|4 for a quarter, or "a"    (default: a = annual averages)
#   AREA_FIPS  one or more area FIPS codes      (default: all 9 Bay Area counties)
#
# Examples:
#   scripts/download_qcew.sh                       # 9 Bay Area counties, 2022 annual
#   scripts/download_qcew.sh 2023 a 06075          # SF only, 2023 annual
#   scripts/download_qcew.sh 2022 1 06001 06085    # Alameda + Santa Clara, Q1
#
set -euo pipefail

YEAR="${1:-2022}"
QTR="${2:-a}"
shift || true; shift || true

# Bay Area county FIPS (Alameda, Contra Costa, Marin, Napa, SF, San Mateo,
# Santa Clara, Solano, Sonoma).
BAY_AREA=(06001 06013 06041 06055 06075 06081 06085 06095 06097)
AREAS=("$@")
[[ ${#AREAS[@]} -eq 0 ]] && AREAS=("${BAY_AREA[@]}")

OUTDIR="data/raw/qcew_${YEAR}_q${QTR}"
mkdir -p "$OUTDIR"

for fips in "${AREAS[@]}"; do
  url="https://data.bls.gov/cew/data/api/${YEAR}/${QTR}/area/${fips}.csv"
  echo "Downloading area ${fips}"
  curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${fips}.csv" "$url"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
