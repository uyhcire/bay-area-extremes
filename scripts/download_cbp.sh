#!/usr/bin/env bash
#
# Download Census County Business Patterns (CBP) — county-level establishment
# counts, employment, and payroll by industry. No API key required.
#
# Usage:
#   scripts/download_cbp.sh [YY]
#
#   YY   2-digit data year (default: 22 = 2022)
#
# Downloads the complete county file `cbp<YY>co.zip` and unzips it. Records are
# by county x NAICS industry. Filter to California (fipstate==6) / the 9 Bay
# Area county codes (fipscty). Layout docs are in the same datasets folder:
#   https://www2.census.gov/programs-surveys/cbp/datasets/<YEAR>/
#
set -euo pipefail

YY="${1:-22}"
YEAR="20${YY}"
OUTDIR="data/raw/cbp_${YEAR}"
mkdir -p "$OUTDIR"

zip="cbp${YY}co.zip"
url="https://www2.census.gov/programs-surveys/cbp/datasets/${YEAR}/${zip}"
echo "Downloading CBP county file ${zip}"
curl -fSL --retry 4 --retry-delay 2 -o "${OUTDIR}/${zip}" "$url"

echo "Unzipping ${zip}"
unzip -o "${OUTDIR}/${zip}" -d "$OUTDIR"

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
