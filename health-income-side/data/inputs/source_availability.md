# Candidate data sources -- availability and vintage (tested 2026-11-27)

Every row was tested in this session with `curl -A "Mozilla/5.0 research-script"`
(HEAD or GET) through the session proxy; TLS verification on. "LM" =
`Last-Modified` response header. Nothing here is from memory: where a page
could not be fetched, the row says so. Downloaded files are under
`data/raw/health_income/misc/` (git-ignored, untrusted).

## Summary table

| # | Source | URL tested | HTTP / reachable? | Latest data year / release seen | Coverage | Usefulness for an income-side health account |
|---|---|---|---|---|---|---|
| 1a | BEA-BLS integrated industry-level production account (KLEMS) | `https://www.bea.gov/data/special-topics/integrated-industry-level-production-account-klems` ; file `https://www.bea.gov/sites/default/files/2026-04/BEA-BLS-industry-level-production-account-1997-2024.xlsx` | 200 / 200 (464,519 bytes; LM 2026-04-24) | Data through **2024** (April 2026 release) | 1997-2024 (levels); contributions 1998-2024; research tables 1947-2016; archive zips 2021, 2022 | High. Sheets give nominal Gross Output, Value Added and compensation of labor (college / non-college), capital (IT, software, R&D, art, other), energy, materials, services by industry. **Health detail is only 3 rows: 621 Ambulatory; "622HO" Hospitals *and* nursing & residential care combined; 624 Social assistance** -- hospitals cannot be separated from 623. |
| 1b | BLS total factor productivity / KLEMS tables (NAICS 62x) | `https://www.bls.gov/productivity/tables/` ; `.../tables/home.htm` ; `https://download.bls.gov/pub/time.series/mp/` | **403 Access Denied** (all three) with the generic UA | not observable | not observable | Unknown from this environment. BLS web/flat-file hosts reject the generic UA; `api.bls.gov` does work (200) but series IDs for health-industry TFP were not verified. |
| 2 | BEA Health Care Satellite Account | `https://www.bea.gov/data/special-topics/health-care` | 200 | Blended & MEPS accounts **2000-2021** (files dated 2023-12 / 2024-01); "BEA Data Applying NHEA Framework **1959-2023**" (LM 2024-04-09) | 2000-2021 (disease-based); 1959-2023 (NHEA-framework table) | Medium. Disease-based spending/price indexes are expenditure-side; the NHEA-framework workbook and `hcsa-comparison-methodology-table-sept-2023.xlsx` are useful bridges between NIPA and NHEA categories. Files: `/sites/default/files/2023-12/2021-blended-account-release-table-rebate.xlsx`, `/2024-01/2021-detail-disease-blended-net-of-rebates.xlsx`, `/2023-12/2021-meps-account-release-table-net-of-rebates.xlsx`, `/2024-04/1959-2023-BEA-Data-Applying-NHEA-Framework.xlsx`, `/2023-08/health-care-satellite-account-documentation.zip`. |
| 3 | BEA import matrices | `https://apps.bea.gov/industry/xls/io-annual/ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx` | 200, real xlsx (812,967 bytes; LM 2024-09-26) | 2023 | 1997-2023 (summary); `..._DET_2017.xlsx` 200 (LM 2024-05-23) | High for import leakage of intermediate inputs. |
| 3' | ... 1997-2024 version | `.../ImportMatrices_Before_Redefinitions_SUM_1997-2024.xlsx` | **Soft 404**: HTTP 200 but `content-type: text/html`, 28,185 bytes (an HTML error page) | -- | -- | **Not found.** NB the existing local file `data/raw/health_income/bea/ImportMatrices_Before_Redefinitions_SUM_1997-2024.xlsx` is that same 28,185-byte HTML page, not a workbook -- do not use it. `https://www.bea.gov/industry/input-output-accounts-data` (200, "last modified 6/13/25") no longer lists files: it says IO tables "have been migrated" to the Input-Output Interactive Data Application (`https://apps.bea.gov/iTable/?reqid=1602&step=2&Categories=Core&isURI=1`). Static bundles `https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip` and `AllTablesSUP.zip` are 200 but LM 2024-09-26 (1997-2023 vintage). Directory listing `.../xls/io-annual/` is 403. Whether iTable serves 2024 import matrices was not tested (JavaScript app). |
| 4 | Census Service Annual Survey (NAICS 62) | `https://www.census.gov/programs-surveys/sas/data/tables.html` ; `https://www2.census.gov/programs-surveys/sas/tables/time-series/` | 200 / 200 | **2022** SAS is the "Latest Data" (page dated August 31, 2026; table files LM 2026-11-23) | 2013-2022 (latest); 1998-2012 (historical); see detail below | High. Revenue and total expenses by NAICS 62 industry **split taxable vs tax-exempt**; detailed expenses (payroll, benefits, depreciation, purchased services, etc.). Employer firms only for the tax-status tables. Downloaded -- see paths below. |
| 5 | Economic Census 2022, sector 62 | `https://www2.census.gov/programs-surveys/economic-census/data/2022/sector62/` ; `https://api.census.gov/data/2022.json` | 200 / 200 | Sector-62 files posted 2024-11 to 2026-04 | 2022 | Medium-high (benchmark year). Bulk zips: `EC2262BASIC.zip` (11M, 2024-12-05; summary statistics incl. revenue/payroll), `EC2262TYPEPAYER.zip` (revenue by type of payer), `EC2262PATIENT.zip`, `EC2262HOSP.zip` (government hospitals ownership), `EC2262GRANT.zip` (grants/contributions), `EC2262TELEMEDS.zip`. API datasets `ecnbasic`, `ecntypepayer`, `ecnpatient`, `ecnhosp`, `ecngrant`, `ecntelemeds`, `ecnexpbyaux` are listed (the Census API itself needs a key). No sector-62 *expenses* file was seen in the sector62 folder. |
| 6 | CMS Medical Loss Ratio public use files | `https://www.cms.gov/marketplace/resources/data/medical-loss-ratio-data-systems-resources` | 200 | **2024** reporting year (`mlr-public-use-file-2024.zip` 200, 7.3 MB, LM 2025-11-21); 2025 file -> 404 | 2011-2024, one zip per year | High for insurers (NAICS 5241 health): premiums, claims, admin costs, taxes/fees by issuer/state/market. URL patterns: 2019-2024 `https://www.cms.gov/files/zip/mlr-public-use-file-<YYYY>.zip`; 2018 `/cciio/resources/data-resources/downloads/public-use-file-2018.zip`; 2011, 2013-2017 `/cciio/resources/data-resources/downloads/mlr_datafilespuf_<release-date>.zip` (20121127, 20140630, 20151118, 20161019, 20171019, 20181205); 2012 `.../mlr-2012-public-use-file-puf.zip`. |
| 7a | IRS SOI corporation complete report (Pub 16), Table 1 by **minor industry** | `https://www.irs.gov/statistics/soi-tax-stats-corporation-income-tax-returns-complete-report-publication-16` ; file `https://www.irs.gov/pub/irs-soi/23co01ccr.xlsx` | 200 / 200 (LM 2026-10-28) | **Tax year 2023** | `<yy>co01ccr.xlsx` 2014-2023; older Table 1 at `https://www.irs.gov/statistics/soi-tax-stats-returns-of-active-corporations-table-1`: `<yy>co01ccr.xls` 2006-2013, `<yy>co01accr.xls` 2004-2005, `<yy>co01nr.xls` 1998-2003, `97co01tabl.xls`, `<yy>crtb01.xls` 1995-96, `94co01mi.xls` | High for corporate income/deductions/profits. The 2023 Table 1 has rows: Health care and social assistance; Offices of health practitioners and outpatient care centers (physicians, dentists, other practitioners, outpatient care centers); Miscellaneous health care and social assistance; **Hospitals, nursing, and residential care facilities (combined)**; Insurance carriers and related activities. I.e. not clean 621/622/623 and 5241 is not separated from other insurance at this level. Other complete-report tables follow `<yy>co<NN>ccr.xlsx` (e.g. 21, 22, 24a, 32, 33, 51, 53, 54, 61, 62) for 2014-2023. |
| 7b | IRS SOI corporation source book (Pub 1053) | `https://www.irs.gov/statistics/soi-tax-stats-corporation-source-book-publication-1053` | 200 | Landing page links 2013 sections (`13cosbsec<N>.zip/.pdf`) and `14sb0<N>lr.xlsx`, plus per-year pages 2000-2012 and a "Download all source data" page (`/statistics/soi-tax-stats-corporation-source-book-data-file`, not fetched) | at least 2000-2014 visible from the landing page; later years not confirmed | Medium: balance sheet / income statement by minor industry and asset size. Latest year not established in this session. |
| 7c | IRS SOI partnership statistics by sector/industry | `https://www.irs.gov/statistics/soi-tax-stats-partnership-statistics-by-sector-or-industry` | 200 | **2023** | `<yy>pa01.xlsx`..`pa06`, `pa23` 2015-2023; `<yy>pa0N.xls` 2004-2014; `<yy>pa02ig.xls` 1993-2001 | High for partnership net income (physician/dental practices). Industry detail inside the files not inspected. |
| 7d | IRS SOI S-corporation statistics | `https://www.irs.gov/statistics/soi-tax-stats-s-corporation-statistics` | 200 | Tables on this page: `<yy>co24ccr.xlsx` etc. 2014-2017; PDFs `<yy>scorp.pdf` 1995-2003; figures 2004-2007 | patchy on this page (latest seen 2017); S-corp tables for later years are within the complete report (e.g. `<yy>co24accr.xlsx` to 2023) | Medium-high (S-corps are a large share of physician practices). |
| 7e | IRS SOI Form 990 annual extracts | `https://www.irs.gov/statistics/soi-tax-stats-annual-extract-of-tax-exempt-organization-financial-data` | 200; `25eoextract990.zip` 200 (59 MB, LM 2026-11-12) | Extract labelled **2025** (calendar year of IRS processing; contains mostly earlier tax years -- not opened) | `<yy>eoextract990.zip` 2018-2025; `<yy>eofinextract990.zip` 2012-2017; EZ and PF variants; doc `<yy>eofinextractdoc.xlsx` | High for nonprofit hospitals/health systems: revenue, expenses, compensation, depreciation, net income. Needs NTEE/EIN filtering (not in scope here). |
| 8 | SEC EDGAR XBRL frames API | `https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2023.json` | **200** with the generic UA (JSON, 410 KB) | CY2023 frame returned | per concept/period | Medium: firm-level revenue/profit for listed insurers, hospital chains, pharma. `https://www.sec.gov/dera/data/financial-statement-data-sets` and `https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q3.zip` returned **403** with the generic UA (no contact e-mail was sent, per instructions), so the bulk financial-statement data sets were not reachable. |
| 9 | OECD ICIO / TiVA | `https://www.oecd.org/en/data/datasets/inter-country-input-output-tables.html` ; `https://www.oecd.org/sti/ind/inter-country-input-output-tables.htm` ; `https://www.oecd.org/en/data/datasets/trade-in-value-added.html` | **403** (Cloudflare "Just a moment..." challenge) on all oecd.org pages; `stats.oecd.org` 405 (HEAD) / 404 on an old fileview link | ICIO edition and year coverage **could not be read**. SDMX API `https://sdmx.oecd.org/public/rest/dataflow/all` is 200 and lists **"Trade in Value Added (TiVA) 2026 edition"** dataflows (`OECD.STI.PIE, DSD_TIVA_MAINLV@DF_MAINLV` v1.2 etc.) and ICIO-based GHG footprint 2023 / 2025 editions | not observable (an `availableconstraint` query returned 500) | Low-medium: only needed for foreign value added embodied in health inputs. Bulk ICIO zip links not located from this environment. |
| 10 | BEA-CMS NHEA vs NIPA/GDP reconciliation | (a) `https://apps.bea.gov/scb/pdf/2010/09%20September/0910_healthcare.pdf` (Hartman, Kornfeld & Catlin, SCB Sept 2010, 11 pp) ; (b) `https://www.bea.gov/sites/default/files/papers/BEA-WP2020-8.pdf` (Kornfeld, Hartman, Espinosa, Butler & Catlin, BEA WP2020-8, June 2020, 36 pp) | 200 / 200, both downloaded and text-extracted | (b) is the most recent update found (linked from the BEA health-care page); covers **2007-2018** | (a) 1997-2008 era data as of early 2010; (b) 2007-2018 | Essential. See summary below. |
| 11 | CMS NHEA methodology ("definitions, sources and methods") | `https://www.cms.gov/files/document/definitions-sources-methods.pdf` | 200 (658,261 bytes; LM 2026-01-13) | "Methodology Paper, **2024**", last updated January 2026, NHE 1960-2024; 45 pp | 1960-2024 | Essential. See extracts below. |
| 12 | MedPAC / AHA aggregate hospital margins | `https://www.medpac.gov/document-type/data-book/` ; `https://www.medpac.gov/document-type/report/` ; `https://www.aha.org/guidesreports/trendwatch-chartbook` ; `https://www.aha.org/statistics/fast-facts-us-hospitals` | 200 / 200 / 200 / 200 | MedPAC **July 2026 Data Book** and **March 2026** / June 2026 Reports to the Congress are listed; AHA page links "AHA issues latest TrendWatch Chartbook" (2026-01-05) | not inspected | Cross-check only. MedPAC PDFs are public (margins are in the March report hospital chapter / data book; the PDFs were not downloaded). AHA chartbook PDF sits behind an `ams.aha.org` store link / member login; archive page `/data-insights/aha-trendwatch-chartbooks-2000-2018`. |

## 4. Service Annual Survey -- files and what was downloaded

Directory `https://www2.census.gov/programs-surveys/sas/tables/time-series/`:

* `sas-latest/` (2022 SAS, 2017 NAICS basis): `Table1.xlsx` revenue, employer +
  nonemployer, 2013-2022; **`Table2.xlsx` revenue by tax status, employer
  firms, 2013-2022**; **`Table3.xlsx` total expenses (by tax status), employer
  firms, 2013-2022**; `Table4.xlsx` sources of revenue, 2013-2022;
  **`Table5.xlsx` selected (detailed) expenses, 2020-2022**; `Table6`-`Table9`,
  `Table11` (patient visits), `Table12` (EHR expenses), `Table13` (inpatient
  days / inpatient & outpatient revenue), `Table15` (telemedicine);
  all-tables workbooks `sas-22.xlsx` (2026-08-31), `Table-22.xlsx`
  (2026-11-23), earlier vintages `sas-21.xlsx`, `sas-20.xlsx`, `sas-19.xlsx`,
  `sas-17.xlsx`, `sas-16.xlsx`, `sas-14.xls`, `sas-12.xlsx`, `sas-22-2012.xlsx`.
  (The task described "Table 4" as revenue by tax status; in the current
  numbering that is **Table 2**, and Table 4 is sources of revenue.)
* `sas-2016-historical/`: `table1h`, `table2h`, `table3h` (.xls/.xlsx),
  `table5h.xls` -- Table 2 "Estimated Revenue by Tax Status for Employer
  Firms: **1998 Through 2012**", Table 3 "Estimated Expense ...: 1998 Through
  2012" (many pre-2009 cells are `NA`/`S` for some sectors; NAICS 62 rows are
  present).
* `sas-2007-historical/`: `table1h.xls`, `table2h.xls`, `table3h.xls`,
  `table5h.xls` (legacy .xls; downloaded but not parsed -- no `xlrd`).
* Older annual folders `https://www2.census.gov/programs-surveys/sas/tables/`
  `1992/ 1994/ ... 2013/`; SIC-basis reports 1985-1998 and NAICS-basis yearly
  pages 1999-2022 are linked from the tables page.

So the tax-status revenue/expense series is available **1998-2022** by
splicing the historical (1998-2012) and latest (2013-2022) files. No 2023 or
2024 SAS tables were found.

Downloaded to `data/raw/health_income/misc/census_sas/`:
`Table1.xlsx`, `Table2.xlsx`, `Table3.xlsx`, `Table4.xlsx`, `Table5.xlsx`,
`sas-2016-historical_table2h.xlsx`, `sas-2016-historical_table3h.xlsx`,
`sas-2007-historical_table2h.xls`, `sas-2007-historical_table3h.xls`.
Tables 2 and 3 each have 142 NAICS-62x rows with tax status in
{All Establishments, exempt from federal income tax, subject to federal income
tax}, down to 6-digit (621111, 622118/622119 ..., 6231, 6232 ...). Table 5 has
298 NAICS-62x rows.

**Flag:** the public `Table1`-`Table4.xlsx` files re-posted 2026-11-23 contain
a first sheet named `CUI` reading "CUI//SP-CENS / Disclosure Prohibited: Title
13 U.S.C. / Disclosure Prohibited - Federal Tax Information Protected by Title
26 U.S.C.", while the data sheet itself says the Census Bureau "has reviewed
this data product to ensure appropriate access, use, and disclosure avoidance
protection". They are served from the public Census site without
authentication, and `Table5.xlsx` (LM 2026-09-01) has no such cover sheet
(`sas-22.xlsx` was not downloaded, so not checked). This looks like a stray internal cover sheet, but it is worth a
human look before redistributing those four files; the all-tables workbook
`sas-22.xlsx` (2026-08-31) may be an alternative. No values from them are used anywhere yet.

## 10. NHEA vs GDP reconciliation -- what the fetched documents say

Source: BEA WP2020-8 (June 2020), text extracted with `pdftotext`
(`data/raw/health_income/misc/pdf/BEA-WP2020-8.pdf`). Page numbers are PDF
pages. The 2010 SCB article (same title, 11 pp) was also fetched; the 2020
paper describes itself as "an update of the previous reconciliation that was
released in 2010" (p.1). No update later than June 2020 was found on the BEA
health-care page.

* Totals are close: "usually differing by less than 2 percent annually";
  "Well over 90 percent of the total estimated expenditures in the two
  accounts consist of the same expenditures" (p.1). For 2018: health spending
  in GDP (as the authors define it) $3,712.5 bn vs NHEA $3,649.5 bn,
  difference $63.1 bn (p.14). Table 4 (p.21) shows NHEA minus GDP going from
  +32.3 (2007) to -63.1 (2018).
* Five sources of discrepancy (p.3): classification of industries/goods;
  treatment of government facilities and expenditures; adjustments to
  estimate final commodity demand; treatment of NPISHs; different data sources
  and methods.
* Hospitals (p.8, Table 11 p.28): NHE exceeds HCE "by 4 to 10 percent of the
  HCE"; 2018 NHE 1,191.8 vs HCE 1,095.4 = +96.4. Reasons: NHE includes
  government outlays for government-owned hospitals (federal hospitals 60.5 in
  2018); BEA removes "nonpatient revenue and revenue for hospital-based home
  health and nursing home care" (adjustments to final commodity demand -52.0
  in 2018).
* Physician/clinical: NHE 725.6 vs HCE physicians & labs 597.0 = +128.5,
  offset by other professional services 103.9 vs 218.8 = -114.9 (outpatient
  care centers classified differently) (Table 19, p.36).
* Prescription drugs: NHE 335.0 vs PCE 433.8 = -98.8; "CMS subtracts rebates
  (roughly $108 billion in 2018) ... BEA does not" (p.14, Table 12 p.29).
* Net cost of insurance: NHE 258.5 vs HCE net health insurance 228.7 = +29.8;
  HCE also includes income-loss insurance and workers' compensation; NHE
  removes the net cost of private plans administering Medicare Advantage /
  Medicaid managed care (counted as government program administration)
  (p.10, Table 15 p.32). (The prose on p.10 says the HCE estimate "exceeds"
  the NHE one, but Tables 4, 15 and 19 show NHE larger in every year.)
* Investment: NHE structures & equipment incl. software 121.8 vs GDP 152.9 =
  -31.1 ("BEA also uses a broader measure of software that includes
  own-account as well as purchased software", p.11). Research: NHE 52.6 vs
  GDP health R&D 123.8 = -71.2, because BEA includes private pharmaceutical
  R&D ($75.1 bn) and CMS does not (p.14, Table 17 p.34).
* Government administration & public health: NHE 141.1 vs health-related
  government consumption expenditures 202.8 = -61.8 (GDP side includes VA
  hospitals etc., consumption of fixed capital) (Table 19, p.36).
* NHEA-only: "Other health, residential, and personal care" $191.6 bn in
  2018. GDP-only: final consumption expenditures of NPISHs $71.2 bn in 2018
  (6.4 in 2007) (Table 4 p.21).
* NPISH treatment (p.5): in the NHEA nonprofit care "is measured as total net
  revenue, which includes nonpatient and nonoperating revenue"; in GDP, NPISH
  final consumption is gross output less sales and own-account investment.
* Hospital data source (p.5, p.8): at the time, BEA used Census (EC/SAS +
  government finance) and CMS used AHA; line 16 of Table 11 shows AHA-based
  nonfederal revenue below the Census-based figure by 11-29 bn per year.

## 11. CMS NHEA Methodology Paper, 2024 -- definitions (PDF page refs)

File: `data/raw/health_income/misc/pdf/definitions-sources-methods.pdf`
(title "National Health Expenditure Accounts (NHEA): Methodology Paper, 2024
-- Definitions, Sources, and Methods", "Last Updated: January 2026", NHE
1960-2024). Printed page numbers equal PDF page numbers.

* **Hospital care (p.7)** -- yes, includes non-patient and non-operating
  revenue: "Expenditures for hospital care include revenue received by all
  U.S. hospitals for all services rendered (NAICS 622). This includes net
  patient revenues (gross charges less contractual adjustments, bad debts, and
  charity care). It also includes government tax appropriations, non-patient
  operating revenue such as receipts from cafeterias, gift shops and parking
  lots, and non-operating revenue, such as interest income, contributions, and
  grants." Hospital-based nursing home, home health, hospice and inpatient
  pharmacy are also in hospital care. Sources now: "Economic Census (EC),
  Services Annual Survey (SAS), and the Quarterly Servies Survey (QSS)";
  "benchmarked to the 2012 and 2017 Economic Census"; AHA is the benchmark
  only for 1960-2007 (AHA growth used through 2021). More generally (p.4) PHC
  "represent[s] all revenues received by health care providers ... as well as
  all non-patient and non-operating revenue, grants, subsidies, and
  philanthropy".
* **Net cost of health insurance (p.23; footnote 68 on p.43)** -- renamed:
  "Non-medical insurance expenditures are defined as the difference between
  private health insurance expenditures and benefits incurred, and include
  administrative costs, additions to reserves, rate credits and dividends,
  premium taxes and fees, and net underwriting gains or losses." Footnote 68:
  "This category was formerly labeled 'Net cost of health insurance'." Private
  estimate from A.M. Best plus MEPS-IC for self-insured plans.
* **Government administration (pp.23-24)** -- "the administrative costs of
  health care programs such as Medicare and Medicaid"; Medicare: federal
  salaries and expenses for Parts A, B, D plus non-medical insurance
  expenditures of private Part C and Part D plans; Medicaid: "federal and
  state and local salaries and expenses of the program, as well as non-medical
  insurance expenditures that are incurred by the private plans that insure
  Medicaid enrollees"; also CHIP, DoD, VA and other programs.
* **Investment (pp.4, 26-27)** -- NHE = HCE "plus investment, which is the sum
  of medical sector purchases of structures and equipment and expenditures for
  non-commercial medical research". Structures: "the value of new construction
  put in place by non-retail medical establishments ... Maintenance and
  repairs are excluded" (p.26; ACES 1993-2022, Medicare cost reports and
  Census construction data for 2023-24). Equipment -- **yes, includes
  software**: "the value of new capital equipment (including software)
  purchased or put in place by non-retail medical establishments during the
  year. This definition is not limited to specific medical equipment or
  devices" (p.27). Private data exclude NAICS 624 and parts of 623 (623312,
  623990).
* **Research (p.26)** -- "Non-commercial research encompasses healthcare
  research conducted by non-profit entities. This includes research funded by
  federal and state governments, academic institutions, and nonprofit
  organizations ... It excludes research funded by for-profit firms."
* **Other health, residential, and personal care (p.9)** -- "spending for
  services provided in non-traditional settings including residential mental
  health and substance abuse facilities, residential intellectual and
  developmental disability facilities, Medicaid home and community-based
  waivers, school health, worksite health care, and some ambulance services."
  Private ambulance revenue excludes "private payment to government operated
  establishments due to a lack of source data".

## Tooling notes

* `pdftotext` (`/usr/bin/pdftotext`) and `pypdf` are both available;
  `pdftotext -layout` was used.
* `openpyxl` fails on the KFF workbook; `health-income-side/code/_xlsx_min.py`
  (zip + XML) was used for all xlsx inspection. `xlrd` is not installed, so
  legacy `.xls` files were downloaded but not opened.
* Unreachable from this environment with the generic UA: `fred.stlouisfed.org`
  (timeout x2), `download.bls.gov` and `www.bls.gov` (403), `www.oecd.org`
  (403 Cloudflare challenge), `www.sec.gov` bulk data sets (403).
