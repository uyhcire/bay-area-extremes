#!/usr/bin/env bash
#
# Upload the local raw data cache (data/raw/) to a Google Cloud Storage bucket,
# preserving the directory layout as object paths. The companion download step
# is scripts/download_all.sh; run that first to populate data/raw/.
#
# This environment has no gcloud/gsutil, so all GCS calls go through
# scripts/gcs_lib.sh, which mints an OAuth token from the service account in
# GCP_PROJECT_SERVICE_ACCOUNT_JSON_BASE64 (openssl-signed JWT) and uses the GCS
# JSON API over curl.
#
# Usage:
#   scripts/upload_to_gcs.sh                 # bucket defaults to bay-area-extremes-data-<project>
#   scripts/upload_to_gcs.sh BUCKET          # custom bucket name
#   scripts/upload_to_gcs.sh BUCKET SRC_DIR  # custom bucket + source directory
#
# The bucket is created (US multi-region) if it does not already exist. The
# bookkeeping files under data/raw/ (_logs/, _download_all.out) are skipped.
#
set -uo pipefail

cd "$(dirname "$0")/.."   # repo root
source scripts/gcs_lib.sh
set +u +o pipefail        # the shell snapshot references unbound vars; don't let nounset kill subshells

PROJECT="$(gcs_project)"
BUCKET="${1:-bay-area-extremes-data-${PROJECT}}"
SRC_DIR="${2:-data/raw}"

if [[ ! -d "$SRC_DIR" ]]; then
  echo "Source directory '$SRC_DIR' not found. Run scripts/download_all.sh first." >&2
  exit 1
fi

echo "Project: $PROJECT"
echo "Bucket:  gs://$BUCKET"
echo "Source:  $SRC_DIR/"
echo ""

gcs_make_bucket "$BUCKET" US || exit 1
gcs_token >/dev/null || { echo "Failed to obtain access token." >&2; exit 1; }

mapfile -t FILES < <(find "$SRC_DIR" -type f ! -path '*/_logs/*' ! -name '_download_all.out' | sort)
echo "Files to upload: ${#FILES[@]}"
echo ""

ok=0; fail=0; total_bytes=0
for f in "${FILES[@]}"; do
  obj="${f#"$SRC_DIR"/}"        # object name preserves the layout under SRC_DIR
  sz=$(stat -c%s "$f")
  if gcs_upload "$BUCKET" "$f" "$obj"; then
    ok=$((ok+1)); total_bytes=$((total_bytes+sz))
    printf 'OK   %12d  %s\n' "$sz" "$obj"
  else
    fail=$((fail+1)); printf 'FAIL %12s  %s\n' "-" "$obj"
  fi
done

echo ""
echo "===================== SUMMARY ====================="
echo "  Uploaded OK: $ok    FAILED: $fail"
echo "  Total bytes: $total_bytes ($(numfmt --to=iec "$total_bytes" 2>/dev/null))"
echo "  Bucket:      gs://$BUCKET"
echo "==================================================="
[[ $fail -gt 0 ]] && exit 1
exit 0
