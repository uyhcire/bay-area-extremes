#!/usr/bin/env bash
#
# Download Zillow Research public data (ZHVI home values, ZORI rents).
# No API key required — public CSVs at files.zillowstatic.com.
#
# Usage:
#   scripts/download_zillow.sh
#
# Pulls County- and Metro-level ZHVI (smoothed, seasonally adjusted, all homes)
# and ZORI. Each CSV is wide: one row per region, one column per month.
# Filter to Bay Area afterward (RegionName / StateName == CA, the 9 counties /
# "San Francisco, CA" + "San Jose, CA" metros).
#
# Browse the full catalog (more tiers, bedroom cuts, ZIP level) at
# https://www.zillow.com/research/data/
#
set -euo pipefail

BASE="https://files.zillowstatic.com/research/public_csvs"
OUTDIR="data/raw/zillow"
mkdir -p "$OUTDIR"

declare -A FILES=(
  ["County_zhvi.csv"]="zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
  ["Metro_zhvi.csv"]="zhvi/Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
  ["Metro_zori.csv"]="zori/Metro_zori_uc_sfrcondomfr_sm_month.csv"
)

for name in "${!FILES[@]}"; do
  echo "Downloading ${name}"
  curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${name}" "${BASE}/${FILES[$name]}"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
