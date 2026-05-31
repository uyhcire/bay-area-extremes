#!/usr/bin/env bash
#
# Download an IPUMS microdata extract (default: IPUMS USA, ACS 2022 1-year).
# REQUIRES a free IPUMS API key — there is no key-free route.
#   Register: https://usa.ipums.org/   (one account spans the IPUMS collections)
#   Make a key: https://account.ipums.org/api_keys
#   Then: export IPUMS_API_KEY=<your-key>
#
# Also requires the official Python client:
#   pip install ipumspy
#
# Usage:
#   scripts/download_ipums.sh [SAMPLE] [COLLECTION]
#
#   SAMPLE      IPUMS sample id   (default: us2022a = ACS 2022 1-year)
#   COLLECTION  IPUMS collection  (default: usa)
#
# Override the variable list with IPUMS_VARS (space- or comma-separated):
#   IPUMS_VARS="AGE SEX STATEFIP PUMA HHINCOME INCTOT" scripts/download_ipums.sh
#
# Unlike the keyless bulk sources, IPUMS is a job-based API: this script defines
# an extract, submits it, waits for the server to build it (can take minutes),
# then downloads the gzipped fixed-width data + DDI (.xml) codebook. Extracts
# cover the whole sample (all U.S.); filter to California (STATEFIP == 6) / the
# Bay Area PUMAs afterward. Read the data with ipumspy's readers, e.g.:
#   from ipumspy import readers
#   ddi = readers.read_ipums_ddi("<file>.xml")
#   df  = readers.read_microdata(ddi, "<file>.dat.gz")
#
set -euo pipefail

if [[ -z "${IPUMS_API_KEY:-}" ]]; then
  echo "ERROR: IPUMS_API_KEY is not set." >&2
  echo "Register at https://usa.ipums.org/ and create a key at" >&2
  echo "  https://account.ipums.org/api_keys, then: export IPUMS_API_KEY=<key>" >&2
  exit 1
fi

if ! python3 -c "import ipumspy" 2>/dev/null; then
  echo "ERROR: the 'ipumspy' Python package is required. Install it with:" >&2
  echo "  pip install ipumspy" >&2
  exit 1
fi

SAMPLE="${1:-us2022a}"
COLLECTION="${2:-usa}"
# Default variables aimed at income / demographic extremes; override via IPUMS_VARS.
: "${IPUMS_VARS:=AGE SEX MARST RACE HISPAN EDUC EMPSTAT OCC IND STATEFIP PUMA HHINCOME INCTOT INCWAGE POVERTY}"

OUTDIR="data/raw/ipums_${COLLECTION}"
mkdir -p "$OUTDIR"

SAMPLE="$SAMPLE" COLLECTION="$COLLECTION" IPUMS_VARS="$IPUMS_VARS" OUTDIR="$OUTDIR" \
python3 - <<'PY'
import os
from ipumspy import IpumsApiClient, MicrodataExtract

collection = os.environ["COLLECTION"]
sample = os.environ["SAMPLE"]
variables = os.environ["IPUMS_VARS"].replace(",", " ").split()
outdir = os.environ["OUTDIR"]

client = IpumsApiClient(os.environ["IPUMS_API_KEY"])

extract = MicrodataExtract(
    collection=collection,
    samples=[sample],
    variables=variables,
    description=f"bay-area-extremes {collection} {sample}",
)

print(f"Submitting {collection} extract for sample {sample} ({len(variables)} variables)...")
client.submit_extract(extract)
print(f"  extract id: {extract.extract_id}; waiting for it to build (can take minutes)...")
client.wait_for_extract(extract)

print(f"Downloading to {outdir}...")
client.download_extract(extract, download_dir=outdir)
PY

echo "Done. Files in ${OUTDIR}:"
ls -lh "$OUTDIR"
