#!/usr/bin/env bash
#
# Download CDPH vital statistics (deaths, births) from the CHHS Open Data
# Portal (data.chhs.ca.gov). No API key required.
#
# The portal is CKAN-based and resource filenames are date-stamped (they change
# every release), so this script resolves current download URLs via the CKAN
# package API rather than hardcoding them.
#
# Usage:
#   scripts/download_cdph_vital.sh [DATASET_SLUG ...]
#
# Default datasets (county-level):
#   death-profiles-by-county        deaths by year/month by county (1970-present)
#   live-birth-profiles-by-county   births by year/month by county (1960-present)
#
# Other useful slugs you can pass:
#   death-profiles-by-zip-code  live-birth-by-zip-code  statewide-death-profiles
#
# Records cover all CA counties; filter to the 9 Bay Area counties afterward.
#
set -euo pipefail

DEFAULT=(death-profiles-by-county live-birth-profiles-by-county)
SLUGS=("$@")
[[ ${#SLUGS[@]} -eq 0 ]] && SLUGS=("${DEFAULT[@]}")

API="https://data.chhs.ca.gov/api/3/action/package_show?id="
OUTDIR="data/raw/cdph_vital"
mkdir -p "$OUTDIR"

for slug in "${SLUGS[@]}"; do
  echo "Resolving CSV resources for ${slug}"
  dest="${OUTDIR}/${slug}"
  mkdir -p "$dest"
  # Emit "url<TAB>filename" for every CSV resource in the package.
  curl -fsSL --retry 4 --retry-delay 2 "${API}${slug}" \
    | python3 -c "
import sys, json
res = json.load(sys.stdin)['result']['resources']
for r in res:
    if r.get('format','').upper() == 'CSV':
        url = r['url']
        print(url + '\t' + url.rsplit('/',1)[-1])
" \
    | while IFS=$'\t' read -r url fname; do
        echo "  -> ${fname}"
        curl -fSL --retry 4 --retry-delay 2 -o "${dest}/${fname}" "$url"
      done
done

echo "Done. Files in ${OUTDIR}:"
ls -lhR "$OUTDIR" | head -40
