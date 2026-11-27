#!/usr/bin/env bash
# Download BLS Consumer Expenditure Survey (CEX) geographic mean tables:
#   - West-region MSA table (includes San Francisco-Oakland-Hayward)
#   - Census-region table (its "All consumer units" column is the U.S. average)
# Both are 2-year averages ending in YEAR.
#
# Usage: BLS_USER_AGENT="my-project/1.0 (research; you@example.com)" \
#          scripts/download_cex.sh [YEAR]        # default YEAR=2024 (2023-24 avg)
#
# www.bls.gov returns HTTP 403 unless the User-Agent carries a contact address,
# so this script requires BLS_USER_AGENT to be set by the caller.
set -euo pipefail

YEAR="${1:-2024}"
: "${BLS_USER_AGENT:?set BLS_USER_AGENT to a descriptive User-Agent with a contact email (BLS returns 403 otherwise)}"

OUT="$(cd "$(dirname "$0")/.." && pwd)/data/raw/cex_${YEAR}_2yr"
mkdir -p "$OUT"
BASE="https://www.bls.gov/cex/tables/geographic/mean"

for f in "cu-msa-west-2-year-average-${YEAR}.xlsx" "cu-region-2-year-average-${YEAR}.xlsx"; do
  echo "-> $f"
  curl -fL --retry 4 --retry-delay 2 -A "$BLS_USER_AGENT" -o "$OUT/$f" "$BASE/$f"
  # A blocked request comes back as an HTML "Access Denied" page, not a workbook.
  if ! head -c 2 "$OUT/$f" | grep -q "PK"; then
    echo "ERROR: $f is not an xlsx (blocked or wrong URL?)" >&2; exit 1
  fi
done
echo "Saved to $OUT"
