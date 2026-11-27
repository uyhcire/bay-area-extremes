# QCEW national health-industry employment and wages by ownership — notes

Output: `qcew_health_national.csv` (4,024 rows, 1997–2025, national `US000` rows only).
Built by `health-income-side/code/11_qcew_health_wages.py` (run with `python3 -I`), run 2026-11-27.
Raw files: `data/raw/health_income/qcew/<YEAR>/<CODE>.csv` (~860 MB total, git-ignored);
per-file URL + HTTP `Last-Modified` in `data/raw/health_income/qcew/_download_log.csv`.

## Sources and URLs

| Years | Route | URL pattern |
| --- | --- | --- |
| 2014–2025 | QCEW open-data slice API, one CSV per industry | `https://data.bls.gov/cew/data/api/<YEAR>/a/industry/<CODE>.csv` |
| 1997–2013 | Bulk zip, annual by industry (slice API returns 404 for these years; 1997–2013 all tested) | `https://data.bls.gov/cew/data/files/<YEAR>/csv/<YEAR>_annual_by_industry.zip` |
| titles for API years | industry titles lookup | `https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv` |

The bulk zips are 60–150 MB each, so they are **not stored whole**: the script reads the zip
central directory and only the ~41 needed members via HTTP Range requests and stores those
member CSVs unmodified. All requests sent `User-Agent: Mozilla/5.0 research-script`; TLS verified.

Cross-check done: for 2014 and 2023, national rows for industries 10, 62, 622, 62412 pulled from
the bulk zip are identical (employment and wages, every ownership) to the API values used here.

## File dates (HTTP Last-Modified)

| Year(s) | Source | Last-Modified |
| --- | --- | --- |
| 1997–2003 | bulk zip | 08 May 2015 |
| 2004–2006 | bulk zip | 07 May 2015 |
| 2007–2009 | bulk zip | 06 May 2015 |
| 2010, 2011 | bulk zip | 06 May 2015, 05 May 2015 |
| 2012 | bulk zip | 30 Apr 2015 |
| 2013 | bulk zip | 01 Jun 2018 |
| 2014 | API | 06 Feb 2018 |
| 2015, 2016 | API | 10 Nov 2017 |
| 2017 | API | 28 Aug 2018 |
| 2018 | API | 06 Sep 2019 |
| 2019 | API | 28 Aug 2020 |
| 2020 | API | 19 Aug 2021 |
| 2021 | API | 31 Aug 2022 |
| 2022 | API | 31 Aug 2023 |
| 2023 | API | 28 Aug 2024 |
| 2024 | API | 02 Sep 2025 |
| 2025 | API | 21 Aug 2026 |

The dates imply each annual file is frozen roughly 8–9 months after the reference year (plus
old re-issues); later-year files do not restate earlier years. 2025 is the newest and has had
no subsequent revision cycle yet.

## Structure of the output

- `own_code`: 0 total covered, 1 federal, 2 state, 3 local, 5 private.
- **Own 0 exists only for industry `10` (total, all industries; agglvl 10).** QCEW publishes no
  all-ownership national total for individual NAICS industries; sum own 1+2+3+5 (subject to
  suppression) if you need one. Own 8 (total government) is not kept; it equals 1+2+3.
- `agglvl_code`: 10 national total; 11 total by ownership; 14 sector; 15 3-digit; 16 4-digit;
  17 5-digit; 18 6-digit — all "by ownership".
- `industry_title`: for 1997–2013 it is the title inside the bulk file; for 2014–2025 it is from
  the current `industry_titles.csv`. Titles therefore change at 2013/2014 for some codes
  (e.g. 6223 "Other hospitals" -> "Specialty (except psychiatric and substance abuse) hospitals";
  6244 "Child day care services" -> "Child care services"). This is a labelling artifact of the
  two sources, not the date of the NAICS revision.
- Industry `92` (public administration) has own 1/2/3 only; `10` has own 0/1/2/3/5.
- `923120` has federal, state and local rows for all 29 years; no private rows (none exist).
- QCEW wages are UI-covered wages and salaries (incl. bonuses, exercised stock options, tips);
  they exclude employer benefit contributions, the self-employed/proprietors, and uncovered workers
  (e.g. some nonprofit/religious hospital staff, students, elected officials). Federal rows come
  from the UCFE program. Federal hospitals (own 1, 622) are essentially VA plus other federal
  civilian-staffed hospitals; uniformed military personnel are not covered.

## NAICS-vintage breaks and other discontinuities

QCEW is not restated to a single NAICS vintage. 1990–2000 data were reconstructed by BLS on a
NAICS 2002 basis; thereafter each year is on the vintage in force (NAICS 2007 from 2007, NAICS
2012 from 2011, NAICS 2017 from 2017, NAICS 2022 from 2022). What shows up in these series:

1. **Pharmacies, NAICS 2022 renumbering.** `44611`/`446110` (Pharmacies and drug stores) exist
   1997–2021 only; `45611`/`456110` (Pharmacies and drug retailers) exist 2022–2025 only. Both
   pairs are in the CSV; no splice was made. Private employment 694,736 (2021, 44611) vs
   733,739 (2022, 45611): the new code's scope is slightly wider, so treat the +5.6% as partly
   definitional.
2. **62412 / 6241 / 624 private, 2013 level shift (not a NAICS revision).** Private 62412
   employment goes 773,674 (2012) -> 1,329,947 (2013), +72%; wages $14.6B -> $20.9B. This is the
   reclassification of publicly funded home-care/personal-assistance workers previously coded to
   private households (NAICS 814110) into 624120. It propagates into private 6241 (+43%), 624
   (+22%) and 62. Pre-/post-2013 home-care wage levels are not comparable. (Attribution to the
   814110 reclassification is from general knowledge of the QCEW series, not verified here
   against a BLS notice.)
3. **62412 local government, 2007:** employment 18,116 -> 32,122 (+77%); local 6241 +25%, local
   624 +19%. Cause not identified.
4. **4242 private, 2018:** employment 200,935 -> 235,459 (+17%). Cause not identified
   (looks like establishment reclassification rather than NAICS 2017, which took effect in 2017).
5. **621 federal, 2010:** employment 12,366 -> 26,001 (+110%) — recoding of federal
   establishments (probably VA outpatient clinics moved out of 622/other codes; not verified).
6. **5417 / 54171 state government, 2006:** employment −23%. **624 / 6241 state, 2018:** −16/−18%.
   **6244 private, 2020:** −16% (pandemic, real).
7. 54171: NAICS 2007 and 2017 re-split the 6-digit children (541711/541712 -> 541713/541714/
   541715); the 5-digit `54171` and 4-digit `5417` totals used here are continuous in scope.
8. 623311/623312: the 2012 revision renamed 623312 from "Homes for the elderly" to "Assisted
   living facilities for the elderly"; codes unchanged.
9. 3391: NAICS 2007/2012 moved some 6-digit pieces (e.g. 339111 laboratory apparatus) out of
   3391; small at national level, not adjusted.

No value was interpolated, spliced or back-cast anywhere.

## Suppressed cells (disclosure_code = 'N')

205 of 4,024 rows are suppressed. In the raw files BLS writes 0 for employment and wages in
these rows (establishment counts are still published); in the output **employment and wages
(and, for uniformity, establishments) are blank** and `disclosure_code` is `N`.
No private-sector (own 5) row and no row for 62, 621, 622, 6221–6223, 623, 624, 62412, 10 or 92
is suppressed. Suppressed cells are all small government cells:

| industry | own | suppressed years |
| --- | --- | --- |
| 3254, 325412 | 3 local | 2001, 2005–2025 |
| 3391 | 3 local | 2008–2011 |
| 44611, 446110 | 2 state | 2007–2009, 2015–2021 |
| 44611, 446110 | 3 local | 2006, 2017–2021 |
| 524114 | 2 state | 2001–2005, 2007–2009 |
| 524114 | 3 local | 2001–2025 |
| 6212 | 2 state | 2001–2021, 2025 |
| 6213 | 2 state | 2001, 2002, 2006–2013, 2022–2025 |
| 6215 | 2 state | 2022, 2023 |
| 6216 | 2 state | 2025 |
| 6219 | 2 state | 2003–2005, 2014–2025 |
| 62191 | 2 state | 2004, 2021 |
| 623311, 623312 | 2 state | 2022–2025 |
| 6242, 6244 | 2 state | 2006–2009, 2014–2020, 2022–2024 |

Consequence: where a 4-digit government cell is suppressed, the 3-digit government total
(e.g. state 621) is still published, so use the 3-digit rows for totals rather than summing
4-digit rows.

## Rows that simply do not exist (no row in the BLS file — left absent, not zero-filled)

Besides the pharmacy code switch: 524114 federal (rows 1997–2011 only), state and local
(2001+ only); 44611 federal (1997–2008 only), state (2007+), local (2001+); 6212 state/local
(2001+); 6213 state (2001+), federal (2009+); 6219 state (15 years), 62191 state (6 years);
623312 federal (28 of 29 years); 3254/325412 federal (2022 only); 4242 federal (2008 only);
6239 federal (2018 only). An absent government row means BLS reported no establishments in that
ownership/industry that year at national level — it is not a suppression.

## Unreachable / not done

- Nothing requested was unreachable. The slice API 404s for 1997–2013 (expected); the bulk zips
  covered those years.
- `45611`/`456110` for <=2021 and `44611`/`446110` for >=2022 return 404 / have no zip member, as
  expected from the NAICS vintage (recorded as `<CODE>.missing` markers in the raw directory).
- The `*_annual_singlefile.zip` route was confirmed reachable (1997, 2013) but not used.

## Sanity anchors (all pass)

- Private NAICS 62 wages 2023: $1,336.7B. Private 622 wages 2023: $422.5B.
- Local government 622 employment: 688,282 (2023), 703,932 (2025).
- Total covered (own 0, industry 10) 2023: 153.1M jobs, $11.08T wages.
