#!/usr/bin/env bash
# Inputs for scripts/analyze_csa_fertility_gdp.py (fertility vs. per-capita GDP, top CSAs).
# All key-free. Writes ~3 GB to data/raw/csa_fertility/ (national ACS PUMS person file).
#   scripts/download_csa_fertility.sh [PUMS_YEAR] [PEP_VINTAGE]     # default: 2024 2025
set -euo pipefail
Y="${1:-2024}"; V="${2:-2025}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/data/raw/csa_fertility"
mkdir -p "$OUT/bea" "$OUT/pums"; cd "$OUT"
get() { curl -fsSL --retry 4 --retry-delay 2 -o "$2" "$1"; echo "ok  $2"; }
PEP="https://www2.census.gov/programs-surveys/popest/datasets/2020-$V/counties"
get "$PEP/totals/co-est$V-alldata.csv"        "co-est$V-alldata.csv"         # births, population
get "$PEP/asrh/cc-est$V-agesex-all.csv"       "cc-est$V-agesex-all.csv"      # women by age
get "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx" list1_2023.xlsx
get "https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt" 2020_Census_Tract_to_2020_PUMA.txt
for t in CAGDP1 CAINC4; do                                                   # BEA bulk zips need no key
  get "https://apps.bea.gov/regional/zip/$t.zip" "$t.zip"; unzip -oq "$t.zip" "*ALL_AREAS*" -d bea
done
get "https://www2.census.gov/programs-surveys/acs/data/pums/$Y/1-Year/csv_pus.zip" csv_pus.zip
unzip -oq csv_pus.zip -d pums
