# bay-area-extremes

Analysis of economic and demographic extremes in the Bay Area, built on public
data from the U.S. Census Bureau (ACS PUMS, CBP, BDS, BPS, LEHD LODES), BEA,
FRED, the BLS (QCEW, LAUS, OEWS), CFPB (HMDA), IRS SOI, FHFA, Zillow, the CDC
(PLACES, USALEEP), IPUMS, and the State of California (CDPH vital statistics,
DOF population).

This file documents how to download each data source. All download routes below
were verified working from this repo's environment on 2026-05-31.

## Quick reference

### Core economic / macro

| Source    | Needs key? | Verified open route                                              |
| --------- | ---------- | ---------------------------------------------------------------- |
| ACS PUMS  | No\*       | Bulk CSV ZIPs at `https://www2.census.gov/.../pums/`             |
| FRED      | No\*       | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`    |
| BEA       | **Yes**    | `https://apps.bea.gov/api/data` (free UserID required)           |
| QCEW      | No         | `https://data.bls.gov/cew/data/api/<year>/<qtr>/...csv`          |

### Housing, income, jobs, mobility, health (county / MSA / tract)

| Source        | Needs key? | Verified open route                                                       |
| ------------- | ---------- | ------------------------------------------------------------------------- |
| HMDA          | No         | `https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?counties=&years=`    |
| IRS SOI       | No         | `https://www.irs.gov/pub/irs-soi/county{in,out}flow<pair>.csv`, `<yy>zpallagi.csv` |
| Zillow        | No         | `https://files.zillowstatic.com/research/public_csvs/...`                 |
| FHFA HPI      | No         | `https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv`   |
| Census BPS    | No         | `https://www2.census.gov/econ/bps/County/co<year>a.txt`                   |
| BLS LAUS      | No\*\*     | `https://download.bls.gov/pub/time.series/la/...`                         |
| BLS OEWS      | No\*\*     | `https://www.bls.gov/oes/special-requests/oesm<yy>ma.zip`                 |
| Census CBP    | No         | `https://www2.census.gov/programs-surveys/cbp/datasets/<year>/cbp<yy>co.zip` |
| Census BDS    | No\*       | `https://www2.census.gov/programs-surveys/bds/tables/time-series/<year>/...` |
| LEHD LODES    | No         | `https://lehd.ces.census.gov/data/lodes/LODES8/<st>/...`                  |
| CDC PLACES    | No         | `https://data.cdc.gov/resource/swc5-untb.csv` (Socrata)                   |
| CDC WONDER    | n/a        | Portal/POST-XML only — see notes (use PLACES for scriptable county health) |
| CDPH vital    | No         | `https://data.chhs.ca.gov/api/3/action/package_show?id=<slug>` (CKAN)     |
| Life exp.     | No         | `https://ftp.cdc.gov/pub/.../NVSS/USALEEP/CSV/<ST>_A.CSV` (tract)         |
| CA DOF pop.   | No         | `https://dof.ca.gov/.../estimates-e1/E-1_<year>_InternetVersion.xlsx`     |
| IPUMS         | **Yes**    | Extract API via `ipumspy` (free key from `account.ipums.org/api_keys`)    |

\* The official JSON APIs (Census Data API, FRED API, Census BDS timeseries)
require a free key, but there are key-free bulk/CSV routes that cover most
needs. See each section.

\*\* No key, but `download.bls.gov` / `www.bls.gov` return **HTTP 403** unless
you send a descriptive `User-Agent` header. The scripts set one.

### Download scripts

Ready-to-run wrappers live in `scripts/`. They write to `data/raw/` (git-ignored),
retry on network errors, and default to Bay Area / California parameters. The
keyless ones run as-is; `download_bea.sh` needs `BEA_API_KEY` exported first.

```bash
# Run everything with default Bay Area / CA parameters (~1.9 GB into data/raw/).
# Continues past failures, SKIPs BEA when BEA_API_KEY is unset, prints a summary.
scripts/download_all.sh           # or: scripts/download_all.sh --list

# Core economic / macro
scripts/download_acs_pums.sh [YEAR] [SPAN] [STATE] [REC]    # default: 2022 1-Year ca p
scripts/download_fred.sh SERIES_ID [SERIES_ID ...]          # e.g. GDP UNRATE SFXRSA
scripts/download_qcew.sh [YEAR] [QTR] [AREA_FIPS ...]       # default: 9 Bay Area counties, annual
scripts/download_bea.sh [TABLE] [LINECODE] [GEOFIPS] [YEAR] # needs BEA_API_KEY

# Housing, income, jobs, mobility, health
scripts/download_hmda.sh [YEAR] [COUNTY_FIPS ...]           # default: Bay Area, 2022
scripts/download_irs_soi.sh [MIGRATION_PAIR] [ZIP_YEAR]     # default: 2122 21
scripts/download_zillow.sh                                  # County+Metro ZHVI, Metro ZORI
scripts/download_fhfa_hpi.sh                                # metro (CBSA) HPI
scripts/download_census_bps.sh [YEAR]                       # county building permits
scripts/download_laus.sh                                    # CA local unemployment (sends UA)
scripts/download_oews.sh [YY]                               # metro occ wages (sends UA)
scripts/download_cbp.sh [YY]                                # county business patterns
scripts/download_bds.sh [YEAR]                              # business dynamics (state x county)
scripts/download_lodes.sh [STATE] [YEAR] [SEG] [JOBTYPE]    # default: ca 2021 S000 JT00
scripts/download_cdc_places.sh [STATE_ABBR]                 # county health, default CA
scripts/download_cdph_vital.sh [DATASET_SLUG ...]           # CDPH deaths + births by county
scripts/download_life_expectancy_tract.sh [ST]              # USALEEP tract life expectancy, default CA
scripts/download_dof_population.sh                          # CA DOF E-1 city/county population
scripts/download_ipums.sh [SAMPLE] [COLLECTION]            # needs IPUMS_API_KEY + ipumspy
```

Each script's header comment documents its arguments and examples.

> **Environment note:** No data API keys are currently set in this
> environment's environment variables. Every source below works key-free from
> this environment **except BEA and IPUMS** and the official Census/FRED JSON
> APIs, which require you to add a key first (see below). The BLS hosts
> (`download.bls.gov`,
> `www.bls.gov`) additionally require a descriptive `User-Agent` header — without
> one they return HTTP 403; the scripts set one.

---

## ACS PUMS (Census Bureau Public Use Microdata Sample)

Person- and household-level microdata. Two ways to get it:

### A. Bulk CSV download — no key required (recommended for full datasets)

Files live under `https://www2.census.gov/programs-surveys/acs/data/pums/`.

Path pattern:

```
https://www2.census.gov/programs-surveys/acs/data/pums/<YEAR>/<1-Year|5-Year>/csv_<p|h><st>.zip
```

- `p` = person records, `h` = housing records
- `<st>` = lowercase 2-letter state abbreviation (e.g. `ca` for California)

Example — California 2022 1-Year person records:

```bash
curl -O "https://www2.census.gov/programs-surveys/acs/data/pums/2022/1-Year/csv_pca.zip"
unzip csv_pca.zip   # -> psam_p06.csv
```

Companion data dictionaries (variable names/codes) are in the same year folder,
e.g. `PUMS_Data_Dictionary_2022.csv`. Browse a folder to see what's available:

```bash
curl "https://www2.census.gov/programs-surveys/acs/data/pums/2022/1-Year/"
```

### B. Census Data API — requires a free key

The JSON API supports server-side filtering by geography/variable but now
**requires an API key** (requests without one 302-redirect to
`api.census.gov/data/missing_key.html`).

1. Get a free key: https://api.census.gov/data/key_signup.html
2. Export it: `export CENSUS_API_KEY=<your-key>`
3. Query (note `&key=` at the end):

```bash
# All California person records, selected variables
curl "https://api.census.gov/data/2022/acs/acs1/pums?get=PWGTP,AGEP,SEX,PINCP&for=state:06&key=$CENSUS_API_KEY"

# Filter to a specific PUMA (Public Use Microdata Area) within a state
curl "https://api.census.gov/data/2022/acs/acs1/pums?get=PWGTP,AGEP,PINCP&for=public%20use%20microdata%20area:00101&in=state:06&key=$CENSUS_API_KEY"
```

Variable list for a dataset:
`https://api.census.gov/data/2022/acs/acs1/pums/variables.json`

Bay Area = state FIPS `06` (California); the nine counties map to a set of PUMAs
(filter with the `public use microdata area` predicate).

---

## FRED (Federal Reserve Economic Data, St. Louis Fed)

Macro/financial time series.

### A. CSV download — no key required (recommended for single series)

```bash
# One series as CSV by its FRED series ID
curl "https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDP" -o GDP.csv
```

Output columns: `observation_date,<SERIES_ID>`. Swap `id=` for any series ID
(find IDs at https://fred.stlouisfed.org/). You can request multiple series by
repeating `id`, and set ranges with `&cosd=YYYY-MM-DD&coed=YYYY-MM-DD`.

### B. FRED API — requires a free key

For metadata, search, and programmatic queries:

1. Get a free key: https://fred.stlouisfed.org/docs/api/api_key.html
2. `export FRED_API_KEY=<your-key>`
3. Query:

```bash
curl "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&file_type=json&api_key=$FRED_API_KEY"
```

---

## BEA (Bureau of Economic Analysis)

GDP-by-state/metro, personal income, regional accounts, etc. **Requires a free
UserID (API key)** — there is no key-free route.

1. Register for a UserID: https://apps.bea.gov/API/signup/
2. `export BEA_API_KEY=<your-userid>`
3. Discover datasets / parameters, then pull data:

```bash
# List available datasets
curl "https://apps.bea.gov/api/data?&UserID=$BEA_API_KEY&method=GETDATASETLIST&ResultFormat=json"

# Example: Regional personal income for San Francisco MSA (CAINC1 table)
curl "https://apps.bea.gov/api/data?&UserID=$BEA_API_KEY&method=GetData&datasetname=Regional&TableName=CAINC1&LineCode=3&GeoFips=41860&Year=ALL&ResultFormat=json"
```

The `Regional` dataset is the relevant one for Bay Area metro/county figures
(`GeoFips=41860` is the San Francisco-Oakland-Berkeley MSA). Use
`method=GetParameterValues` to enumerate valid table names, line codes, and
GeoFips values.

---

## QCEW (BLS Quarterly Census of Employment and Wages)

Establishment counts, employment, and wages by county and industry. The BLS
**open data API requires no key**.

### Single CSV files (slice by area, industry, or size)

```bash
# Annual averages for one area (FIPS), all industries:
#   https://data.bls.gov/cew/data/api/<YEAR>/<QTR>/area/<AREA_FIPS>.csv
#   <QTR> = 1|2|3|4 for a quarter, or "a" for annual averages
curl "https://data.bls.gov/cew/data/api/2022/a/area/06075.csv" -o sf_qcew_2022.csv
```

Bay Area county FIPS codes (use as `<AREA_FIPS>`):

| County        | FIPS  | | County        | FIPS  |
| ------------- | ----- |-| ------------- | ----- |
| Alameda       | 06001 | | San Mateo     | 06081 |
| Contra Costa  | 06013 | | Santa Clara   | 06085 |
| Marin         | 06041 | | Solano        | 06095 |
| Napa          | 06055 | | Sonoma        | 06097 |
| San Francisco | 06075 | |               |       |

Other slice endpoints (same `/api/<YEAR>/<QTR>/` prefix):

- `industry/<NAICS>.csv` — one industry across all areas
- `size/<SIZE_CODE>.csv` — Q1 establishment-size data

Full reference: https://www.bls.gov/cew/downloadable-data-files.htm

---

## HMDA (Home Mortgage Disclosure Act, via CFPB)

Loan-level mortgage application microdata (amounts, applicant income, race/sex,
action taken), geocoded to county and census tract. No key.

The CFPB Data Browser exposes a CSV export API. Filter by county to keep files
manageable (statewide pulls are very large). The endpoint 301-redirects to a
generated file on `files.ffiec.cfpb.gov`, so follow redirects (`curl -L`).

```bash
# One county (San Francisco) for one year
curl -L "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?counties=06075&years=2022" -o hmda_sf_2022.csv

# Multiple counties: comma-separate the FIPS codes
curl -L "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?counties=06001,06085&years=2022"
```

Other filter params: `&actions_taken=`, `&loan_types=`, `&races=`, etc.
Data Browser UI: https://ffiec.cfpb.gov/data-browser/

---

## IRS SOI (Statistics of Income)

No key. Two products used here, both national CSVs (filter to CA / Bay Area
county FIPS yourself):

- **County-to-county migration** — who moved where, with counts and aggregate
  AGI. Filenames use a consecutive-year pair, e.g. `2122` = TY2021→2022.
- **ZIP-code income** — returns, AGI, and components by ZIP and AGI band.
  Filenames use a 2-digit year, e.g. `21zpallagi.csv`. California ZIPs are 94/95.

```bash
curl -O "https://www.irs.gov/pub/irs-soi/countyinflow2122.csv"
curl -O "https://www.irs.gov/pub/irs-soi/countyoutflow2122.csv"
curl -O "https://www.irs.gov/pub/irs-soi/21zpallagi.csv"
```

---

## Zillow Research Data

No key. Public CSVs at `https://files.zillowstatic.com/research/public_csvs/`.
Each file is wide: one row per region, one column per month. Filter to the 9
Bay Area counties / the "San Francisco, CA" and "San Jose, CA" metros.

```bash
# County ZHVI (home values, smoothed + seasonally adjusted, all homes)
curl -O "https://files.zillowstatic.com/research/public_csvs/zhvi/County_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
# Metro ZORI (observed rents)
curl -O "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv"
```

Full catalog (more tiers, bedroom cuts, ZIP level): https://www.zillow.com/research/data/

---

## FHFA House Price Index (HPI)

No key. Repeat-sales home-price index. The metro (CBSA) quarterly
all-transactions file is the directly usable one for the Bay Area
(SF-Oakland-Berkeley CBSA = `41860`).

```bash
curl -O "https://www.fhfa.gov/hpi/download/quarterly_datasets/hpi_at_metro.csv"
```

**The CSV has no header row.** Columns are:
`metro_name, cbsa_code, year, quarter, index_nsa, index_sa` (missing = `-`).
County and state files (filenames change per release) are linked from
https://www.fhfa.gov/data/hpi/datasets

---

## Census Building Permits Survey (BPS)

No key. New privately-owned housing units authorized by building permits, by
county and year — the supply side of the housing story.

```bash
curl -O "https://www2.census.gov/econ/bps/County/co2022a.txt"   # 'a' = annual
```

National fixed-layout CSV with a two-row split header; filter to state FIPS `6`.
Layout docs are in https://www2.census.gov/econ/bps/County/

---

## BLS LAUS (Local Area Unemployment Statistics)

No key, but `download.bls.gov` returns **HTTP 403 without a `User-Agent`** —
send a descriptive one. Monthly labor-force, employment, and unemployment for
counties and metro divisions.

```bash
UA="bay-area-extremes/1.0 (research; eric@distyl.ai)"
# California series observations + the reference files needed to decode them
curl -A "$UA" -O "https://download.bls.gov/pub/time.series/la/la.data.11.California"
curl -A "$UA" -O "https://download.bls.gov/pub/time.series/la/la.series"
curl -A "$UA" -O "https://download.bls.gov/pub/time.series/la/la.area"
```

Series IDs encode area + measure; join on `la.series`/`la.area` to pull the 9
Bay Area counties or the SF/San Jose metro divisions. Single county/metro series
are also on FRED (e.g. `CASANF0URN`). Layout: https://download.bls.gov/pub/time.series/la/la.txt

---

## BLS OEWS (Occupational Employment and Wage Statistics)

No key, but `www.bls.gov` needs a `User-Agent` (else 403). Metro-level wage
estimates by occupation, including the **10/25/50/75/90th wage percentiles** —
directly useful for wage tails. Bay Area MSAs: `41860` (SF-Oakland-Berkeley),
`41940` (San Jose-Sunnyvale-Santa Clara).

```bash
UA="bay-area-extremes/1.0 (research; eric@distyl.ai)"
curl -A "$UA" -O "https://www.bls.gov/oes/special-requests/oesm23ma.zip"   # May 2023 metro
unzip oesm23ma.zip   # -> MSA_M2023_dl.xlsx, BOS_M2023_dl.xlsx (balance of state)
```

Catalog: https://www.bls.gov/oes/tables.htm

---

## Census County Business Patterns (CBP)

No key. Establishment counts, employment, and payroll by county × NAICS
industry.

```bash
curl -O "https://www2.census.gov/programs-surveys/cbp/datasets/2022/cbp22co.zip"
unzip cbp22co.zip   # -> cbp22co.txt
```

Filter to `fipstate==6` and the Bay Area `fipscty` codes. Layout docs are in the
same `datasets/<YEAR>/` folder.

---

## Census BDS (Business Dynamics Statistics)

Firm/establishment births and deaths, job creation/destruction, by year. The
**bulk CSV tables need no key** (the Census Data API `timeseries/bds` route
*does* require one — it 302-redirects to `missing_key.html` without it).

```bash
# State-by-county time series (all years up to 2022 in one file)
curl -O "https://www2.census.gov/programs-surveys/bds/tables/time-series/2022/bds2022_st_cty.csv"
```

Filter to `st==06` and the Bay Area `cty` codes. Catalog:
https://www.census.gov/data/datasets/time-series/econ/bds/bds-datasets.html

---

## Census LEHD LODES (Origin-Destination Employment Statistics)

No key. Block-level jobs data — where people live vs. where they work. Three
file types per state (gzipped CSV), under `LODES8/<st>/`:

```bash
base="https://lehd.ces.census.gov/data/lodes/LODES8/ca"
curl -O "$base/od/ca_od_main_JT00_2021.csv.gz"      # origin-destination pairs
curl -O "$base/wac/ca_wac_S000_JT00_2021.csv.gz"    # workplace area characteristics
curl -O "$base/rac/ca_rac_S000_JT00_2021.csv.gz"    # residence area characteristics
```

`S000` = all jobs; `JT00` = all job types. Aggregate the 15-digit block GEOIDs
up to the 9 Bay Area county FIPS. Schema (LODESTechDoc): https://lehd.ces.census.gov/data/

---

## CDC PLACES (county health measures)

No key. Model-based county-level prevalence of health conditions and behaviors
(obesity, diabetes, no insurance, poor mental health, etc.) via the CDC Socrata
open-data API. Dataset `swc5-untb` is "PLACES: County Data" (long format).

```bash
# All California counties (Socrata caps rows per request — page with $offset)
curl "https://data.cdc.gov/resource/swc5-untb.csv?\$where=stateabbr='CA'&\$limit=50000"
```

Filter to the Bay Area by `locationname` (county) or `locationid` (county FIPS).
Browse: https://data.cdc.gov/d/swc5-untb

> **CDC WONDER** (detailed mortality/natality) is *not* cleanly scriptable: its
> API is a POST/XML interface and county-level queries are frequently blocked
> for privacy (small-cell suppression). For scriptable county health, prefer
> PLACES above or CDPH vital statistics below; use the WONDER web portal
> (https://wonder.cdc.gov/) for ad-hoc cause-of-death pulls.

---

## CDPH vital statistics (CHHS Open Data Portal)

No key. California deaths and births by county (and ZIP), back to 1970/1960.
Published on the CKAN-based CHHS portal `data.chhs.ca.gov`, where **resource
filenames are date-stamped and change every release** — so resolve current
download URLs via the package API instead of hardcoding them.

```bash
# List the CSV resources in a dataset, then download them
curl "https://data.chhs.ca.gov/api/3/action/package_show?id=death-profiles-by-county"
curl "https://data.chhs.ca.gov/api/3/action/package_show?id=live-birth-profiles-by-county"
```

`scripts/download_cdph_vital.sh` does this automatically (parses the JSON for
`format == CSV` resources and downloads each). Other slugs:
`death-profiles-by-zip-code`, `live-birth-by-zip-code`, `statewide-death-profiles`.
Records cover all CA counties; filter to the Bay Area afterward.

---

## Life expectancy by census tract (NCHS USALEEP)

No key. The U.S. Small-area Life Expectancy Estimates Project (2010–2015) — the
standard source CDPH points to for tract-level life expectancy. One file per
state; the `_A` file is life expectancy at birth, `e(0)`, with standard error.

```bash
curl -O "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Datasets/NVSS/USALEEP/CSV/CA_A.CSV"
```

Columns: `Tract ID, STATE2KX, CNTY2KX, TRACT2KX, e(0), se(e(0)), Abridged life table flag`.
`CNTY2KX` = county FIPS (Bay Area: 001 013 041 055 075 081 085 095 097). Layout:
https://www.cdc.gov/nchs/data/nvss/usaleep/Record_Layout_CensusTract_Life_Expectancy.pdf

---

## California DOF population estimates

No key. The CA Dept. of Finance is the **authoritative** source for city/county
population (more current and CA-specific than the Census Bureau). The E-1 table
covers cities, counties, and the state. The filename bumps each year
(`E-1_<YEAR>_InternetVersion.xlsx`), so scrape the landing page for the current
link (the script does this):

```bash
# Landing page lists the current E-1 .xlsx
curl "https://dof.ca.gov/forecasting/demographics/estimates-e1/"
# e.g. as of 2026-05:
curl -O "https://dof.ca.gov/media/docs/forecasting/Demographics/estimates-e1/E-1_2026_InternetVersion.xlsx"
```

Other tables (E-2 components of change, E-5 detail) are linked from
https://dof.ca.gov/forecasting/demographics/estimates/

---

## IPUMS (harmonized census/survey microdata)

**Requires a free API key** — there is no key-free route. IPUMS provides
harmonized microdata across years/collections (USA, CPS, International, ATUS …)
plus NHGIS tract/block-group aggregates. Its edge over the bulk ACS PUMS route
is consistent variable coding across years and the NHGIS geographies.

1. Register (one account spans collections): https://usa.ipums.org/
2. Generate a key: https://account.ipums.org/api_keys
3. `export IPUMS_API_KEY=<your-key>`
4. Install the official client: `pip install ipumspy`

IPUMS is a **job-based extract API**, not a single-URL download: you define an
extract (collection + samples + variables), submit it, wait for the server to
build it, then download the gzipped fixed-width data + DDI (`.xml`) codebook.
`scripts/download_ipums.sh` wraps this with `ipumspy`:

```bash
export IPUMS_API_KEY=<your-key>
scripts/download_ipums.sh                       # IPUMS USA, ACS 2022 1-year, default vars
scripts/download_ipums.sh us2022b usa           # 5-year sample
IPUMS_VARS="AGE SEX STATEFIP PUMA HHINCOME INCTOT" scripts/download_ipums.sh
```

Extracts cover the whole sample (all U.S.); filter to California
(`STATEFIP == 6`) / the Bay Area PUMAs afterward. Read with `ipumspy.readers`
(`read_ipums_ddi` + `read_microdata`). Because microdata overlaps the keyless
ACS PUMS bulk route, reach for IPUMS mainly for multi-year harmonized series or
NHGIS small-area tables.

---

## Conventions

- Put downloaded raw files under `data/raw/` (git-ignored — these are large and
  reproducible from the commands above). Keep this directory out of version
  control; commit the download scripts instead.
- Reference each dataset by source + year (e.g. `acs_pums_2022_1yr`,
  `qcew_2022_annual`) so the provenance is clear.
