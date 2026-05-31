# The Bay Area runs into the top of the OEWS wage scale

**Claim.** Among the 20 largest U.S. metros, **San Francisco–Oakland–Hayward
has the highest share of its workforce earning above the OEWS top-code**
(~$239,200/yr) — and among the 20 largest **CSAs**, the combined
**San Jose–San Francisco–Oakland** megaregion ranks **#1** on the same measure.
The Bay Area is the one place where a mainstream, high-headcount occupation
(software developers) earns so much that the federal wage survey can't print its
upper percentiles.

**Source.** BLS OEWS — Occupational Employment and Wage Statistics, May 2023
metropolitan file (`oesm23ma`, `MSA_M2023_dl.xlsx`). CSA aggregation uses the
OMB 2020 delineation crosswalk (`list1_2020.xls`).

---

## Headline numbers

The two Bay Area metros are the **#1 and #2 highest-paid metros in the country**
on the all-occupation annual mean wage (of 396 metros):

| Rank | Metro | All-occ mean | Median | All-occ P90 |
| ---- | ----- | -----------: | -----: | ----------: |
| 1 | **San Jose–Sunnyvale–Santa Clara** | $113,730 | $81,470 | $215,270 |
| 2 | **San Francisco–Oakland–Hayward** | $97,460 | $72,050 | $193,870 |
| 3 | Washington–Arlington–Alexandria | $88,370 | $65,110 | $168,080 |
| — | *(U.S. all-occupation mean)* | *~$65,470* | — | — |

San Jose's *mean wage across all jobs* is ~74% above the national average and
beats the #3 metro by ~$25k. Its all-occupation 90th-percentile wage ($215,270)
is the highest of any metro. ~31% of San Jose's detailed occupations and ~30% of
SF's have a **median** wage ≥ $100k, vs. 22% in New York and 14% in Chicago.

## Why "top-coded" is the sharpest signal

OEWS does not collect exact salaries; it bins each worker into one of 12 wage
intervals, the highest of which is **open-ended ("$115.00/hr and over")**. Any
mean or percentile that lands in that top interval is suppressed and printed as
`#`. Empirically, the highest hourly value printed anywhere in the May 2023 file
is **$114.95/hr**, confirming the cap at **$115.00/hr = $239,200/yr**.

> Note: the bundled `file_descriptions.xlsx` legend states `#` means
> "> $90.00/hr or $187,200/yr." That figure is stale for this release — the data
> behavior (and the $114.95 max printed value) shows the actual 2023 cap is
> $115.00/hr / $239,200/yr.

In most metros the top interval catches only a few CEOs and surgeons. In the Bay
Area it swallows the upper tail of an *everyday tech job*. San Jose software
developers (SOC 15-1252):

| | annual | hourly |
| --- | ---: | ---: |
| 25th pct | $167,870 | $80.71 |
| median | $199,100 | $95.72 |
| 75th pct | $214,090 | $102.93 |
| **90th pct** | **`#` (≥ $239,200)** | **`#` (≥ $115.00)** |

The mean ($199,800) is the highest of any metro; the 90th percentile is so high
it exceeds what the survey will report.

## Ranking — share of workforce top-coded

The OEWS doesn't publish "% of people above the cap," so it's **estimated** from
each occupation's published percentile cut-points: locate the $115/hr crossing
among P10/P25/P50/P75/P90 (e.g. if P90 is `#` but P75 isn't, 10–25% of that
occupation is top-coded), take the bracket midpoint, then employment-weight
across all occupations. Treat the levels as approximate and the **ranking** as
the robust result.

### 20 largest MSAs

| Rank | MSA | OEWS emp | % top-coded |
| ---- | --- | -------: | ----------: |
| **1** | **San Francisco–Oakland–Hayward, CA** | 2,422,210 | **4.0%** |
| 2 | New York–Newark–Jersey City | 9,495,240 | 2.5% |
| 3 | Boston–Cambridge–Nashua | 2,761,890 | 2.2% |
| 4 | Washington–Arlington–Alexandria | 3,092,070 | 2.2% |
| 5 | Denver–Aurora–Lakewood | 1,590,330 | 1.7% |
| 6 | Chicago–Naperville–Elgin | 4,506,800 | 1.6% |
| 7 | Los Angeles–Long Beach–Anaheim | 6,185,570 | 1.5% |
| 8 | Seattle–Tacoma–Bellevue | 2,079,090 | 1.4% |
| 9 | San Diego–Carlsbad | 1,522,620 | 1.4% |
| 10 | Dallas–Fort Worth–Arlington | 3,966,500 | 1.4% |

*(San Jose is ~6.5% — the single most extreme metro in the country — but at
~1.1M jobs it is smaller than the 20 largest MSAs, so it falls outside this
"largest-20" table.)*

### 20 largest CSAs

| Rank | CSA | OEWS emp | % top-coded |
| ---- | --- | -------: | ----------: |
| **1** | **San Jose–San Francisco–Oakland, CA** | 4,631,920 | **3.8%** |
| 2 | New York–Newark, NY-NJ-CT-PA | 9,845,970 | 2.5% |
| 3 | Washington–Baltimore–Arlington | 4,668,540 | 1.8% |
| 4 | Denver–Aurora, CO | 1,895,980 | 1.7% |
| 5 | Chicago–Naperville, IL-IN-WI | 4,588,830 | 1.5% |
| 6 | Dallas–Fort Worth, TX-OK | 4,017,040 | 1.4% |
| 7 | Seattle–Tacoma, WA | 2,344,770 | 1.3% |
| 8 | Los Angeles–Long Beach, CA | 8,163,150 | 1.3% |

The Bay Area CSA's 3.8% is *lower* than SF–Oakland alone (4.0%) and San Jose
alone (6.5%) because the CSA also folds in lower-wage outer metros (Santa Rosa,
Vallejo, Napa, Santa Cruz, Stockton, Modesto), which add ~1.1M jobs and dilute
the share. The megaregion is enormous, but its extreme pay is concentrated in the
urban core. Washington drops to #3 because the CSA bundles in Baltimore.

## Caveats

- The top-coded share is an estimate from binned percentiles (bracket-midpoint
  interpolation), not a direct count; occupation-wage coverage averages ~94% of
  employment across these areas.
- OEWS has no CSA geography; CSA figures aggregate the 396 MSA files via the OMB
  2020 delineation crosswalk. Aggregation is valid because the method yields an
  estimated *head-count* of top-coded workers per MSA, which sums across a CSA's
  component MSAs.
- All-occupation rows use `OCC_CODE=00-0000`, cross-industry (`NAICS=000000`);
  the 396 areas are all MSAs (`AREA_TYPE=4`), so there is no metro-division
  double-counting.

## Reproduce

```bash
scripts/download_oews.sh 23        # -> data/raw/oews_23/oesm23ma/MSA_M2023_dl.xlsx
# CSA crosswalk (OMB 2020 delineation):
curl -fsSL -A "bay-area-extremes/1.0 (research; eric@distyl.ai)" -o /tmp/list1_2020.xls \
  "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2020/delineation-files/list1_2020.xls"
```

```python
import pandas as pd, numpy as np

raw = pd.read_excel('data/raw/oews_23/oesm23ma/MSA_M2023_dl.xlsx', dtype=str)
df  = raw[raw.NAICS == '000000'].copy()
df['emp'] = pd.to_numeric(df.TOT_EMP, errors='coerce')

CAP  = 115.0   # $/hr top-code = $239,200/yr
pcts = [('H_PCT10', .10), ('H_PCT25', .25), ('H_MEDIAN', .50),
        ('H_PCT75', .75), ('H_PCT90', .90)]

def share_above(row):
    """Estimated share of an occupation's workers earning >= the top-code."""
    pts = []
    for col, cp in pcts:
        v = row[col]
        if v == '#':
            pts.append((cp, 'TC'))
        elif pd.notna(v) and str(v).strip() not in ('', '*', '**'):
            try: pts.append((cp, float(v)))
            except ValueError: pts.append((cp, None))
        else:
            pts.append((cp, None))
    tc  = [cp for cp, v in pts if v == 'TC']
    num = [(cp, v) for cp, v in pts if isinstance(v, float)]
    if not num and not tc:
        return None
    if tc:                                   # some percentile is >= CAP
        cp_t  = min(tc)
        below = [cp for cp, v in num if cp < cp_t]
        cp_b  = max(below) if below else 0.0
        return ((1 - cp_t) + (1 - cp_b)) / 2  # bracket midpoint
    num.sort()                               # no top-code: extrapolate past P90
    (cpA, vA), (cpB, vB) = num[-2], num[-1]
    if vB <= vA:
        return 0.0
    slope = (cpB - cpA) / (np.log(vB) - np.log(vA))
    s = 1 - (cpB + slope * (np.log(CAP) - np.log(vB)))
    return float(min(max(s, 0), 0.10))

det = df[df.O_GROUP == 'detailed'].copy()
det['tc_emp'] = det.apply(share_above, axis=1) * det.emp
tot = df[df.OCC_CODE == '00-0000'][['AREA', 'AREA_TITLE', 'emp']]

# Per-MSA top-coded share, 20 largest metros:
msa = det.dropna(subset=['tc_emp']).groupby('AREA').tc_emp.sum().reset_index()
msa = msa.merge(tot, on='AREA')
msa['pct'] = msa.tc_emp / msa.emp * 100
print(msa.sort_values('emp', ascending=False).head(20)
         .sort_values('pct', ascending=False)[['AREA_TITLE', 'emp', 'pct']]
         .to_string(index=False))

# CSA aggregation:
xw = (pd.read_excel('/tmp/list1_2020.xls', dtype=str, header=2)
        [['CBSA Code', 'CSA Code', 'CSA Title']]
        .dropna(subset=['CSA Code']).drop_duplicates('CBSA Code'))
msa['CSA'] = msa.AREA.map(dict(zip(xw['CBSA Code'], xw['CSA Code'])))
g = msa.dropna(subset=['CSA']).groupby('CSA').agg(tc=('tc_emp','sum'), emp=('emp','sum')).reset_index()
g['title'] = g.CSA.map(dict(zip(xw['CSA Code'], xw['CSA Title'])))
g['pct'] = g.tc / g.emp * 100
print(g.sort_values('emp', ascending=False).head(20)
       .sort_values('pct', ascending=False)[['title', 'emp', 'pct']].to_string(index=False))
```
