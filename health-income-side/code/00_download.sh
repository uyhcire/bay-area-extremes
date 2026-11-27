#!/usr/bin/env bash
# Download every raw input for the income-side health account into data/raw/health_income/ (git-ignored).
# No API keys are needed.  HCRIS, QCEW and the BLS/KFF comparison series are fetched by scripts 10-12.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RAW="$ROOT/data/raw/health_income"
UA="Mozilla/5.0 research-script"
mkdir -p "$RAW/bea" "$RAW/cms"
get() { # get <url> <dest>
  if [ -s "$2" ]; then echo "have $2"; return; fi
  for i in 1 2 3 4; do
    code=$(curl -sL -m 600 -A "$UA" -o "$2" -w "%{http_code} %{content_type}" "$1") && case "$code" in 200*html*) ;; 200*) echo "ok   $1"; return;; esac
    sleep $((i * 2))
  done
  echo "FAIL $1 ($code)"; rm -f "$2"
}
B="$RAW/bea"
get "https://apps.bea.gov/national/Release/TXT/NipaDataA.txt"                         "$B/NipaDataA.txt"
get "https://apps.bea.gov/national/Release/TXT/SeriesRegister.txt"                    "$B/SeriesRegister.txt"
get "https://apps.bea.gov/national/Release/TXT/TablesRegister.txt"                    "$B/TablesRegister.txt"
get "https://apps.bea.gov/national/FixedAssets/Release/TXT/FixedAssets.txt"           "$B/FixedAssets.txt"
get "https://apps.bea.gov/national/FixedAssets/Release/TXT/SeriesRegister.txt"        "$B/FA_SeriesRegister.txt"
get "https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_inv1.xlsx"         "$B/detailnonres_inv1.xlsx"
get "https://apps.bea.gov/industry/Release/ZIP/GdpByInd.zip"                          "$B/GdpByInd.zip"
get "https://apps.bea.gov/industry/Release/ZIP/UGdpByInd.zip"                         "$B/UGdpByInd.zip"
get "https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip"          "$B/AllTablesIO.zip"
get "https://apps.bea.gov/industry/xls/io-annual/ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx" "$B/ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx"
get "https://apps.bea.gov/industry/release/xlsx/PCEBridge_Summary.xlsx"               "$B/PCEBridge_Summary.xlsx"
get "https://apps.bea.gov/industry/release/xlsx/PCEBridge_Detail.xlsx"                "$B/PCEBridge_Detail.xlsx"
for z in GdpByInd UGdpByInd AllTablesIO; do [ -d "$B/$z" ] || unzip -oq "$B/$z.zip" -d "$B/$z"; done
C="$RAW/cms"
get "https://www.cms.gov/files/zip/national-health-expenditures-type-service-source-funds-cy-1960-2024.zip" "$C/national-health-expenditures-type-service-source-funds-cy-1960-2024.zip"
get "https://www.cms.gov/files/zip/nhe-tables.zip"                                     "$C/nhe-tables.zip"
for z in national-health-expenditures-type-service-source-funds-cy-1960-2024 nhe-tables; do [ -d "$C/$z" ] || unzip -oq "$C/$z.zip" -d "$C/$z"; done
echo "done. Next: python3 -I 10_hcris_hospital_financials.py; python3 -I 11_qcew_health_wages.py; python3 -I 12_comparison_series.py; python3 20_build_accounts.py; python3 30_analysis.py"
