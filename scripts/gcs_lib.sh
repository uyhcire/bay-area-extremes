#!/usr/bin/env bash
#
# Helper library for talking to Google Cloud Storage from this environment,
# which has no gcloud/gsutil and a broken python crypto stack. We mint an
# OAuth2 access token from the service account in GCP_PROJECT_SERVICE_ACCOUNT_JSON_BASE64
# by signing a JWT with openssl, then call the GCS JSON API with curl.
#
# Source this file, then use:
#   gcs_token            -> echoes an access token (cached for the process)
#   gcs_project          -> echoes the service account's project_id
#   gcs_make_bucket NAME [LOCATION]
#   gcs_upload BUCKET LOCAL_PATH OBJECT_NAME
#
set -uo pipefail

_gcs_b64url() { openssl base64 -e -A | tr '+/' '-_' | tr -d '='; }

_gcs_sa_file() {
  # Writes the decoded SA JSON to a temp file (once) and echoes its path.
  if [[ -z "${_GCS_SA_FILE:-}" ]]; then
    _GCS_SA_FILE="$(mktemp)"
    echo "${GCP_PROJECT_SERVICE_ACCOUNT_JSON_BASE64:?env var not set}" | base64 -d > "$_GCS_SA_FILE"
  fi
  echo "$_GCS_SA_FILE"
}

gcs_project() {
  python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['project_id'])" "$(_gcs_sa_file)"
}

gcs_token() {
  # Cache the token for ~50 min within the process.
  local now; now=$(date +%s)
  if [[ -n "${_GCS_TOKEN:-}" && $(( now - ${_GCS_TOKEN_AT:-0} )) -lt 3000 ]]; then
    echo "$_GCS_TOKEN"; return 0
  fi

  local sa pk client_email token_uri
  sa="$(_gcs_sa_file)"
  pk="$(mktemp)"
  client_email=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['client_email'])" "$sa")
  token_uri=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['token_uri'])" "$sa")
  python3 -c "import json,sys;open(sys.argv[2],'w').write(json.load(open(sys.argv[1]))['private_key'])" "$sa" "$pk"

  local header claim jh jc signing_input sig jwt resp
  header='{"alg":"RS256","typ":"JWT"}'
  claim="{\"iss\":\"$client_email\",\"scope\":\"https://www.googleapis.com/auth/devstorage.full_control\",\"aud\":\"$token_uri\",\"iat\":$now,\"exp\":$((now+3600))}"
  jh=$(printf '%s' "$header" | _gcs_b64url)
  jc=$(printf '%s' "$claim" | _gcs_b64url)
  signing_input="$jh.$jc"
  sig=$(printf '%s' "$signing_input" | openssl dgst -sha256 -sign "$pk" | _gcs_b64url)
  jwt="$signing_input.$sig"
  rm -f "$pk"

  resp=$(curl -s -X POST "$token_uri" \
    -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
    --data-urlencode "assertion=$jwt")
  _GCS_TOKEN=$(printf '%s' "$resp" | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null)
  if [[ -z "$_GCS_TOKEN" ]]; then echo "gcs_token: failed: $resp" >&2; return 1; fi
  _GCS_TOKEN_AT=$now
  echo "$_GCS_TOKEN"
}

gcs_make_bucket() {
  local bucket="$1" location="${2:-US}" project token http
  project="$(gcs_project)"
  token="$(gcs_token)" || return 1
  http=$(curl -s -o /tmp/_gcs_mb.json -w "%{http_code}" -X POST \
    "https://storage.googleapis.com/storage/v1/b?project=$project" \
    -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
    -d "{\"name\":\"$bucket\",\"location\":\"$location\",\"storageClass\":\"STANDARD\"}")
  if [[ "$http" == "200" ]]; then echo "created gs://$bucket"; return 0; fi
  if [[ "$http" == "409" ]]; then echo "gs://$bucket already exists"; return 0; fi
  echo "gcs_make_bucket: HTTP $http: $(cat /tmp/_gcs_mb.json)" >&2; return 1
}

gcs_upload() {
  # gcs_upload BUCKET LOCAL_PATH OBJECT_NAME  (resumable upload, streams from disk)
  local bucket="$1" local_path="$2" object="$3" token http session
  token="$(gcs_token)" || return 1
  local enc; enc=$(python3 -c "import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=''))" "$object")

  # Initiate resumable session.
  session=$(curl -s -D - -o /dev/null -X POST \
    "https://storage.googleapis.com/upload/storage/v1/b/$bucket/o?uploadType=resumable&name=$enc" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/octet-stream" \
    | tr -d '\r' | awk -F': ' 'tolower($1)=="location"{print $2}')
  if [[ -z "$session" ]]; then echo "gcs_upload: no session for $object" >&2; return 1; fi

  http=$(curl -s -o /tmp/_gcs_up.json -w "%{http_code}" -X PUT "$session" \
    -H "Content-Type: application/octet-stream" \
    --data-binary "@$local_path")
  if [[ "$http" == "200" || "$http" == "201" ]]; then return 0; fi
  echo "gcs_upload: HTTP $http uploading $object: $(cat /tmp/_gcs_up.json)" >&2; return 1
}
