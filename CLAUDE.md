# bay-area-extremes

Analysis of economic and demographic extremes in the Bay Area, built on public
data from the U.S. Census Bureau (ACS PUMS), BEA, FRED, and the BLS (QCEW).

This file documents how to download each data source. All download routes below
were verified working from this repo's environment on 2026-05-31.

## Quick reference

| Source    | Needs key? | Verified open route                                              |
| --------- | ---------- | ---------------------------------------------------------------- |
| ACS PUMS  | No\*       | Bulk CSV ZIPs at `https://www2.census.gov/.../pums/`             |
| FRED      | No\*       | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>`    |
| BEA       | **Yes**    | `https://apps.bea.gov/api/data` (free UserID required)           |
| QCEW      | No         | `https://data.bls.gov/cew/data/api/<year>/<qtr>/...csv`          |

\* The official JSON APIs (Census Data API, FRED API) require a free key, but
there are key-free bulk/CSV routes that cover most needs. See each section.

> **Environment note:** No data API keys are currently set in this
> environment's environment variables. The key-free routes (ACS PUMS bulk CSV,
> FRED `fredgraph.csv`, QCEW open API) work as-is. BEA and the official
> Census/FRED JSON APIs require you to add a key first (see below).

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

## Conventions

- Put downloaded raw files under `data/raw/` (git-ignored — these are large and
  reproducible from the commands above). Keep this directory out of version
  control; commit the download scripts instead.
- Reference each dataset by source + year (e.g. `acs_pums_2022_1yr`,
  `qcew_2022_annual`) so the provenance is clear.
