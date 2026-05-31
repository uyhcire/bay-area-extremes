#!/usr/bin/env bash
#
# Download Census LEHD LODES (LEHD Origin-Destination Employment Statistics).
# No API key required.
#
# Usage:
#   scripts/download_lodes.sh [STATE] [YEAR] [SEG] [JOBTYPE]
#
#   STATE    lowercase 2-letter abbrev   (default: ca)
#   YEAR     data year                   (default: 2021)
#   SEG      workforce segment for WAC/RAC: S000=all jobs (default: S000)
#   JOBTYPE  JT00=all jobs (default), JT01=primary, JT02=private, etc.
#
# Downloads three block-level files (gzipped CSV) for the state:
#   od  - origin-destination pairs (home block -> work block), main part
#   wac - Workplace Area Characteristics (jobs by work-block, by SEG)
#   rac - Residence Area Characteristics (workers by home-block, by SEG)
# Aggregate the 15-digit GEOIDs up to the 9 Bay Area county FIPS (06001 ...).
# Catalog + schema (LODESTechDoc): https://lehd.ces.census.gov/data/
#
set -euo pipefail

STATE="${1:-ca}"
YEAR="${2:-2021}"
SEG="${3:-S000}"
JT="${4:-JT00}"

BASE="https://lehd.ces.census.gov/data/lodes/LODES8/${STATE}"
OUTDIR="data/raw/lodes_${STATE}_${YEAR}"
mkdir -p "$OUTDIR"

declare -a FILES=(
  "od/${STATE}_od_main_${JT}_${YEAR}.csv.gz"
  "wac/${STATE}_wac_${SEG}_${JT}_${YEAR}.csv.gz"
  "rac/${STATE}_rac_${SEG}_${JT}_${YEAR}.csv.gz"
)

for rel in "${FILES[@]}"; do
  name="$(basename "$rel")"
  echo "Downloading ${name}"
  curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${name}" "${BASE}/${rel}"
done

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
