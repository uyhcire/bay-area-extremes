# comparison_series.csv -- provenance notes

Built by `health-income-side/code/12_comparison_series.py` (run with `python3 -I`).
Retrieval date for everything below: **2026-11-27**. All requests used
`User-Agent: Mozilla/5.0 research-script`. Every value is read from a file
downloaded in that session; nothing is interpolated, extrapolated or filled.
Raw files: `data/raw/health_income/misc/{bls,kff}/` (git-ignored).

Output: long CSV `series_id, year, value, units, source_url`, 288 rows.

| series_id | what | years in CSV | source URL | vintage |
|---|---|---|---|---|
| CUUR0000SA0 | CPI-U all items, U.S. city avg, NSA, annual average | 1997-2025 | `https://api.bls.gov/publicAPI/v2/timeseries/data/` (POST, `annualaverage=true`, period `M13`) | BLS API as of 2026-11-27; latest monthly obs in payload = Oct 2026 |
| CUUR0000SAM | CPI-U medical care | 1997-2025 | same | same |
| CUUR0000SAM2 | CPI-U medical care services | 1997-2025 | same | same |
| CUUR0000SEMF01 | CPI-U prescription drugs | 1997-2025 | same | same |
| CUUR0000SEMD | CPI-U hospital and related services | 1997-2025 | same | same |
| PCU622110622110 | PPI, general medical and surgical hospitals (optional) | 1997-2025 | same | same |
| PCU621111621111 | PPI, offices of physicians exc. mental health (optional) | 1997-2025 | same | same |
| KFF_EHBS_PREMIUM_SINGLE | KFF EHBS average annual premium, single coverage (USD) | 1999-2026 | `https://files.kff.org/attachment/Tables-EHBS-2026-Section-01.xlsx`, sheet "Figure 1.12" | 2026 survey; file Last-Modified 2026-10-22 |
| KFF_EHBS_PREMIUM_FAMILY | KFF EHBS average annual premium, family coverage (USD) | 1999-2026 | same | same |
| BEA_B230RC_POP | Midperiod population, thousands (NIPA T7.1 line 18) | 1997-2025 | pre-existing local `data/raw/health_income/bea/NipaDataA.txt` (BEA `https://apps.bea.gov/national/Release/TXT/NipaDataA.txt`) | local copy dated 2026-11-27; server Last-Modified 2026-11-25 |

## Route actually used for BLS and what failed

* `fred.stlouisfed.org/graph/fredgraph.csv` -- **unreachable**: tried twice,
  no HTTP response within 25-30 s (curl code 000). Not used.
* `download.bls.gov/pub/time.series/cu/` (directory and
  `cu.data.15.USMedical`) -- **HTTP 403 "Access Denied"** with the generic
  User-Agent. (The repo's other BLS scripts get through with a UA carrying a
  contact e-mail; that was deliberately not sent here.) Not used.
* **Used instead:** BLS Public Data API v2, unregistered (no key), which
  returned HTTP 200 / `REQUEST_SUCCEEDED` and includes the BLS-published
  annual average as period `M13`. Three POSTs (1997-2006, 2007-2016,
  2017-2026), seven series each; raw JSON cached in
  `data/raw/health_income/misc/bls/bls_api_<start>_<end>.json`. The
  unregistered API allows ~25 queries/day, so the script re-uses the cache
  unless run with `--refresh`.
* Only `M13` rows are used. 2026 has no `M13` yet (monthly through Oct 2026),
  so the BLS series end in 2025. No annual value was computed from months.

## Caveats to check before use

* **Index base periods are not in the API payload** (the unregistered API
  returns no catalog metadata), so the `units` column does not assert one.
  In particular **CUUR0000SEMD** comes back as 25.3 (1997) ... 103.692 (2025),
  i.e. not on the 1982-84=100 scale of the other CPI series
  (SAM = 234.6 in 1997). The values are exactly as downloaded; confirm the
  base period on bls.gov before using SEMD in levels (growth rates are
  unaffected by the base).
* BLS annual averages before 2007 are published to one decimal, later years
  to three.
* KFF: values are parsed from cells such as `$2,439*`; the `*` (statistically
  different from the previous year, p<.05) is dropped. Premiums are total
  (employer + worker) average annual premiums for covered workers. Sheet
  source line: "KFF Employer Health Benefits Survey, 2018-2026; Kaiser/HRET
  Survey of Employer-Sponsored Health Benefits, 1999-2017". Landing page
  fetched: `https://www.kff.org/health-costs/2026-employer-health-benefits-survey/`
  (HTTP 200), which links the Section 1-12 table workbooks
  (`Tables-EHBS-2026-Section-NN.xlsx`). **KFF was used; MEPS-IC was not needed
  and was not tested.**
* The KFF workbook cannot be opened by openpyxl (malformed `xWindow`
  attribute); `code/_xlsx_min.py` is a small zip/XML reader used instead.
* Population is the BEA NIPA midperiod series (not Census resident
  population); taken from the BEA flat file already on disk, not re-downloaded.
* Raw-file SHA-256 prefixes at build time: KFF xlsx `98bddf7ed2a5ec1b`,
  BLS JSON `910e858ec2735e35`, `17466fc1252e3cd2`, `cf7d57a41b2588d6`.
