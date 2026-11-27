# HCRIS hospital financials — notes

Output: `hcris_hospital_financials.csv` (161 rows: 32 calendar years x ownership class).
Built by `health-income-side/code/10_hcris_hospital_financials.py`
(`python3 -I health-income-side/code/10_hcris_hospital_financials.py`; ~5 min first
run for extraction, ~10 s afterwards). Run on 2026-11-27.

## Which convention the main columns use

**Main (unsuffixed) dollar columns are CALENDAR-YEAR-PRORATED**: each cost report's
amounts are allocated to calendar years in proportion to the days of its reporting
period falling in each year (amount x overlap_days / period_days). Short- and
long-period reports need no annualization under this rule: their dollars are simply
spread over the days they cover.

`*_fyend` columns assign the whole report to the calendar year in which its fiscal
period ENDS (`FY_END_DT`).

- `n_reports` = integer count of used reports whose period ends in that year (FY-end basis).
- `n_report_years` = sum over used reports of (days in that calendar year / days in the
  year), i.e. hospital-years of data behind the prorated columns. This is the
  completeness gauge for the main columns.

All amounts are whole dollars as reported (not thousands). Nothing is grossed up,
interpolated or imputed.

## Sources

Base URL `https://downloads.cms.gov/files/hcris/` (User-Agent `Mozilla/5.0 research-script`).
All 34 files returned HTTP 200; **Last-Modified for every file is Mon, 05 Oct 2026
(23:47–23:51 GMT)**; the CSVs inside are dated 2026-10-02. Total 3.43 GB zipped.
Per-file URL, bytes and Last-Modified are in
`data/raw/health_income/hcris/download_manifest.csv`.

- Form CMS-2552-96: `HOSPFY1995.zip` … `HOSPFY2011.zip` (17 files; `HOSPFY2012.zip` is 404).
  Members: `HOSP_<YYYY>_rpt.csv`, `_nmrc.csv`, `_alpha.csv`, `_rollup.csv`.
- Form CMS-2552-10: `HOSP10FY2010.zip` … `HOSP10FY2026.zip` (17 files).
  Members: `HOSP10_<YYYY>_rpt.csv`, `_nmrc.csv`, `_alpha.csv`.

The file year is the federal fiscal year (Oct–Sep) in which the report period
BEGINS. `HOSPFY1995` has 2 reports, `HOSPFY2011` 35, `HOSP10FY2026` 22. Raw RPT rows
across all files: 183,446. No header rows; RPT columns assumed in the standard HCRIS
order (RPT_REC_NUM, PRVDR_CTRL_TYPE_CD, PRVDR_NUM, NPI, RPT_STUS_CD, FY_BGN_DT,
FY_END_DT, PROC_DT, INITL_RPT_SW, LAST_RPT_SW, TRNSMTL_NUM, FI_NUM, ADR_VNDR_CD,
FI_CREAT_DT, UTIL_CD, NPR_DT, SPEC_IND, FI_RCPT_DT); NMRC = RPT_REC_NUM, WKSHT_CD,
LINE_NUM, CLMN_NUM, ITM_VAL_NUM. Only `_rpt` and `_nmrc` are used.

## Variable definitions (worksheet / line / column)

NMRC codes: line = 5 digits (LLLSS). Column is 4 digits in the 2552-96 files (`0100`)
and 5 digits in the 2552-10 files (`00100`).

| CSV column | 2552-96 | 2552-10 |
|---|---|---|
| net_patient_revenue | G300000 line 00300 col 1 | G300000 line 00300 col 1 |
| total_operating_expenses | G-3 line 00400 | G-3 line 00400 |
| net_income_from_patients | G-3 line 00500 (if blank: line 3 − line 4; 20 reports) | same |
| contributions_donations | G-3 line 00600 | G-3 line 00600 |
| investment_income | G-3 line 00700 | G-3 line 00700 |
| govt_appropriations | G-3 line 02300 | G-3 line 02300 |
| other_income (total other income) | G-3 line 02500 | G-3 line 02500 |
| total_revenue | net_patient_revenue + other_income (derived) | same |
| net_income | G-3 line **03100** | G-3 line **02900** |
| (other expenses, used only for the identity check) | G-3 line 03000 | G-3 line 02800 |
| salaries | A000000 line 10100 (total) col 1 | A000000 line 20000 (total) col 1 |
| depreciation | A700003 (A-7 Part III) line 00500 (total) col 9 | A700003 line 00300 (total) col 9 |
| interest_expense_capital_a7 | A700003 line 00500 col 11 | A700003 line 00300 col 11 |
| ownership | RPT.PRVDR_CTRL_TYPE_CD (= S200000 line 01800 col 1) | RPT.PRVDR_CTRL_TYPE_CD (= S200001 line 02100 col 1) |

Verification of the line map: on every used/deduped report with a G-3 and a net income
cell (175,972 reports) the identity `line 3 − line 4 + total other income − total other
expenses = net income` holds to within $2 for 99.999% (100% of 2552-10; all but 2 of
2552-96 reports). Line 5 equals line 3 − line 4 on all but 1 report. HCRIS does not
store zero cells: a blank component on a filed G-3 is a zero (250 reports have a blank
net-income line; the identity gives exactly 0 for all of them). If the "total other
income" line is blank but component lines 6–24 exist, the components are summed (2 reports).
No report has sublines on lines 6, 7 or 23.

`other_income` includes everything on G-3 lines 6–24 (contributions, investment income,
government appropriations, parking, cafeteria, rental, "other" incl. the 2552-10
line 24.50 COVID-19 PHE funding, etc.). `net_income` is after "other expenses".

### Ownership classes

Type-of-control code list (2552-96 S-2 line 18; 2552-10 S-2 Part I line 21), as I know it
from the form instructions: 1 voluntary nonprofit–church, 2 voluntary nonprofit–other,
3 proprietary–individual, 4 proprietary–corporation, 5 proprietary–partnership,
6 proprietary–other, 7 governmental–federal, 8 governmental–city-county, 9 governmental–county,
10 governmental–state, 11 governmental–hospital district, 12 governmental–city,
13 governmental–other. **I could not download a CMS document in this session to confirm
the list** (guessed documentation URLs under /files/hcris/ returned 404), so treat the
mapping of 7 = federal as stated-from-memory. Consistency checks that did pass: the RPT
field and the S-2 cell agree on all 90,877 reports where both exist; only codes 1–13
occur; code 7 is rare (114 used reports in total, ~4 per year), as expected since VA/DoD
hospitals do not file Medicare cost reports.

Mapping: 1–2 nonprofit; 3–6 forprofit; 7 government_federal; 8–13 government_nonfederal.
Used-report counts by code: 1: 19,120; 2: 71,256; 3: 323; 4: 40,183; 5: 4,750; 6: 3,030;
7: 114; 8: 3,267; 9: 13,467; 10: 4,488; 11: 10,631; 12: 2,332; 13: 1,850.
One 1996 report has no control code; it appears as an extra class `unknown` (rows for
1995 and 1996 only) and is included in `all`. `all` = sum of all classes.

## Dedup

Within a provider (PRVDR_NUM), across both forms, any report whose period overlaps a
preferred report by more than 30 days is dropped. Preference order: has a G-3 >
status rank (4 reopened > 3 settled with audit > 2 settled without audit > 5 amended >
1 as submitted) > form 2552-10 over 2552-96 > later PROC_DT > higher RPT_REC_NUM.

- Dropped 116 reports (115 from 2552-96 files, 1 from 2552-10), carrying $2.43B of net
  patient revenue. 183,330 reports remain.
- 96/10 overlap (FY2010–2011): no provider has the same FY_END_DT in both forms, so
  there is no cross-form double counting at the provider-period level; the 30-day
  overlap rule covers any residual cases.

## Dropped reports (garbage rules) and $ impact

Applied after dedup, in this order (all-years totals):

| Rule | n | NPR | Opex | Other income | Net income |
|---|---|---|---|---|---|
| No G-3 (line 3 or line 4 blank). UTIL_CD: F 4,643 / N 1,393 / L 1,072 | 7,108 | – | – | – | – |
| NPR <= 0 or opex <= 0 | 205 | −$55.4B | $17.0B | $30.5B | +$14.9B |
| abs(net income) > 5 x NPR | 494 | $1.7B | $21.4B | $14.4B | −$6.2B |
| NPR > 2 x opex ("operating margin" > 50%; typically contractual allowances not deducted) | 562 | $203.4B | $63.8B | −$6.1B | +$124.1B |
| opex > 20 x NPR | 149 | $0.1B | $4.4B | $4.2B | −$0.05B |

Used reports: **174,812** (86,801 on 2552-96; 88,011 on 2552-10). No report had
unparseable dates or a period outside 1–550 days. Period lengths of used reports:
164,712 are 330–400 days, 9,769 shorter, 331 longer.

Single worst items: provider 053035 FYE 3/1997 (NPR −$28.6B, net income +$51.5B),
390164 FYE 6/2010 (NPR −$8.2B), 454008 FYE 8/2011 (other income $9.5B on $23M NPR).
The NPR > 2 x opex rule is a judgment call and removes real expenses along with the
bogus revenue (e.g. 390049 FYE 6/2023: NPR $8.9B vs opex $1.1B). By FY-end year, all
rules combined remove the most net income in 1997 ($52.8B, almost all provider 053035),
2011 ($17.5B), 2025 ($12.1B),
2023 ($11.0B), 2014 ($9.2B), 2022 ($7.1B); typical years $1–4B. Full by-year impact:
`data/raw/health_income/hcris/hcris_qa_stats.json` key `dropped_garbage_by_fyend_year`.

**Retained but suspect**: 1,935 reports with NPR between 1.5x and 2x opex are kept; they
carry $277B NPR, $167B opex and $105B of net income over all years, rising from ~$1–2B
of net income per year before 2009 to $6.8B (FYE 2022), $7.5B (2023), $9.6B (2024),
$10.8B (2025). Many are for-profit facilities whose G-3 expenses appear to omit
corporate/home-office costs, so I did not treat them as obvious garbage. Net income in
the output is therefore likely overstated by some part of this amount, and the level of
aggregate net income is sensitive to where this cutoff sits. Also retained: reports
with implausible offsetting entries (e.g. 050055 and 050008, FYE 2013–2014, with
identical opex and other income of about −$2.1B each).

## Coverage and completeness

- **Universe**: every provider filing a hospital cost report (short-term acute, critical
  access, psychiatric, rehabilitation, long-term care, children's, cancer…). About
  5,700–6,000 reports a year. Federal VA/DoD hospitals do not file; `government_federal`
  is a handful of reports and is not a measure of federal hospital spending.
- G-3 is the financial statement of the reporting entity as the provider chose to define
  it: usually the hospital complex including subproviders, hospital-based SNF/HHA/clinics,
  sometimes a wider health system or university unit. It is unaudited for most reports.
- 4,643 full-utilization reports have no G-3 at all (plus 2,465 low/no-utilization
  reports); their revenue is missing from the totals and cannot be quantified from HCRIS.
- **Incomplete calendar years (prorated columns)** — do not use as levels:
  - 1995: sliver only (292 report-years).
  - 1996: ~4,554 report-years vs ~5,800 normal (files start with periods beginning
    on/after 1 Oct 1995).
  - 2025: ~4,425 report-years (77%); 2026: 63.
  - 2024 looks complete on count (5,710 report-years) but most FY2024–2025 reports are
    "as submitted" and subject to revision.
  - First complete year is 1997; last reasonably complete year is 2024.
- **FY-end columns**: 1996 is incomplete (3,288 reports); 2026 has 279 reports; FYE 2025
  has a normal count (5,767) but is nearly all as-submitted. 1995 has none.
- Sanity anchors (class `all`, prorated): NPR $336B in 1998 (anchor $350–400B, slightly
  below), $1,265B in 2022; total margin 4.1% in 1998, 1.35% in 2008, 2.9% in 2022,
  6–8.4% in most other years since 2010.

## Depreciation, interest, salaries

- **salaries**: Worksheet A total line, column 1. Missing on only 32 used reports. Clean.
- **depreciation**: Worksheet A-7 Part III total line, column 9 = capital-related
  depreciation as carried into the cost report (buildings/fixtures + movable equipment).
  This is the Medicare cost-finding figure, close to but not identical with book
  depreciation. **A-7 Part III is absent for most reports in the FY2002, FY2003 and
  FY2004 files** (1,905 / 1,784 / 4,074 reports with the cell vs ~6,050 in neighbouring
  years). The column `a7_opex_coverage` gives the share of operating expenses in reports
  that have the cell; where it is below 0.90 the depreciation and interest cells are
  left **blank rather than estimated**. That blanks calendar years 2002–2004 for `all`
  (coverage 0.29 / 0.12 / 0.45) and some class-years. Elsewhere coverage is 0.95–0.99
  and depreciation runs 3.6–5.7% of operating expenses.
- **interest expense is NOT cleanly available.** `interest_expense_capital_a7` is A-7
  Part III total line column 11: capital-related interest only, after cost-report
  adjustments (notably the offset of investment income against interest), and blank for
  about 45% of reports. It totals only 0.3–1.0% of operating expenses (about $5B in 2022)
  and understates hospitals' actual interest expense. The alternative, Worksheet A
  "interest expense" line (113 on 2552-10) column 2, is populated by only 2,339 of ~5,800
  FY2022 reports ($4.9B) because most providers book interest directly in the capital
  lines or at the home office. G-2 and G-3 carry no interest line. Do not use this column
  as total interest expense; I did not attempt to approximate one.

## Other caveats

- Dollar values are nominal and as reported; no restatement for mergers or provider
  number changes.
- Investment income on G-3 line 7 reflects whatever the provider books there
  (realized/unrealized treatment varies); it is negative in aggregate in 2008 and 2022.
- 2020–2022 other income includes Provider Relief Fund and similar COVID receipts.
- For-profit facility net income is before most parent-company costs and taxes.
- The 2552-96 files contain a `_rollup.csv` that was not used.

## What failed / was not done

- `HOSPFY2012.zip` does not exist (404) — expected, 2552-96 ends with FY2011.
- No CMS layout/documentation file could be fetched to confirm the control-code list
  and the RPT column order; both rest on the standard HCRIS layout plus the internal
  consistency checks above.
- No clean interest expense series (see above). Depreciation unavailable for 2002–2004.
- All 34 data files downloaded and parsed; nothing else failed.

## Files written outside this folder (git-ignored)

`data/raw/health_income/hcris/`: the 34 zips, `download_manifest.csv`,
`hcris_qa_stats.json` (all QA counts quoted here), `extract/*_cells.csv` and
`extract/*_rpt.csv` (cached cell extracts), and
`extract/hcris_report_level_used.csv` (one row per used report, for audit).
