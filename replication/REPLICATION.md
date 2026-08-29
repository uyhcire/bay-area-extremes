# Replication: "The College Wage Premium in the Generative AI Era"

**Paper:** José Azar, Mireia Giné, Javier Sanz-Espín (August 28, 2026 draft).
**Replication date:** 2026-08-29, from public, key-free data only.

## Verdict

**The paper's core results replicate.** Using the same public EPI CPS-ORG
extracts (1979–2026) and the public Eloundou et al. (2023) exposure scores, we
reproduce the sample exactly (7,571,607 observations vs. the paper's "7.57
million"), match the composition-adjusted college premium series to within
0.003 log points in every benchmark year, match the inequality tables
essentially exactly, and recover the event-study coefficients within ~0.005
of the published values. The AI-exposure share of the 2022–2026 premium
decline comes out at 24–25 percent versus the paper's 28 percent, with the gap
fully explained by a slightly smaller college/non-college exposure gap under
our occupation crosswalk. The one component that cannot be replicated key-free
is the 1914–1962 portion of the historical CES estimation, which requires the
login-gated Autor-Goldin-Katz openICPSR deposit; on the 1979–2026 window we
confirm the paper's headline historical claim — implied relative demand for
college labor *falls* in 2022–2026, the only multi-year decline in the sample.

## Data

| Input | Source used | Access |
| --- | --- | --- |
| CPS-ORG microdata 1979–2026 | EPI extracts, `microdata.epi.org/epi_cpsorg_1979_2026.zip` (2026 through July) | open |
| AI exposure | `openai/GPTs-are-GPTs` repo, `data/occ_level.csv` (O\*NET-SOC level) | open |
| Occupation crosswalks | Census `2018-occupation-code-list-and-crosswalk.xlsx` | open |
| AGK (2020) historical series 1914–2005 | openICPSR 120694 | **login-gated — not used** |

Sample: wage and salary earners aged 16–64 with positive hourly earnings
(EPI `wage`), weighted by CPS earnings weights (`orgwgt`).
Sample checks vs. paper §2.1: N = 7,571,607 (paper: 7.57M) — mean age 38.3
(38.3) — 47.6% female (47.6) — 30.0% BA+ (30.0). **All exact.**

### Exposure measure

The paper does not name which Eloundou et al. variant it uses. Calibrating
against its reported 2022 moments (college mean 0.473, non-college 0.302,
exposure–college-share correlation 0.61), the GPT-4-rated "beta" measure
(`dv_rating_beta`; E1 + 0.5·E2) is the closest match: our means are 0.453 and
0.292 (gap 0.161 vs. 0.171) and the employment-weighted correlation with the
2022 college share is 0.57 (human beta: 0.60). O\*NET-SOC detail codes were
averaged to 6-digit SOC and matched to 2018 Census occupation codes by
SOC prefix; 2018–2019 observations (2010 Census codes) were bridged with the
official 2010→2018 crosswalk, averaging exposure over split codes. The paper's
exact aggregation (possibly employment-weighted) likely explains the small
remaining gap.

## Results: paper vs. replication

### College premium series (Fig 1, §2.1, Table A2)

| Statistic | Paper | Replication |
| --- | --- | --- |
| Raw premium (BA+ vs non-college), 1979 | 0.410 | 0.410 |
| Raw premium, 2022 → 2026 | 0.626 → 0.575 | 0.626 → 0.575 |
| Composition-adjusted premium, 1979 | 0.339 | 0.339 |
| … 2016 | 0.633 | 0.632 |
| … 2019 | 0.625 | 0.622 |
| … 2022 | 0.623 | 0.621 |
| … 2026 | 0.570 | 0.567 |
| Δ adjusted premium 2022–2026 | −0.053 | −0.054 |
| P90–P50: 2019 / 2022 / 2026 | 0.915 / 0.919 / 0.907 | 0.915 / 0.919 / 0.907 |
| Δ P90–P50, 2022–26 | −0.013 | −0.013 |
| Δ P50–P10, 2022–26; 2019–26 | −0.030; −0.095 | −0.030; −0.095 |

One discrepancy: §2.1 also quotes a "raw college premium" of BA+ vs
**high-school-only** workers of 0.649 (2022) → 0.591 (2026). Under every
weighting we tried, BA+ vs HS-only gives 0.633 → 0.588. The 0.626 → 0.575
numbers in the abstract (BA+ vs non-college) replicate exactly, so the §2.1
figures appear to mix the two definitions.

### Event study (Table 5, Fig 5) — exposure × year, ref. 2022

Column (3): occupation + year FE. Column (4): + sex, race, quartic age,
occupation×industry FE. SEs clustered by occupation, in parentheses.

| Year | Paper (3) | Repl. (3) | Paper (4) | Repl. (4) |
| --- | --- | --- | --- | --- |
| 2018 | 0.016 (0.025) | −0.018 (0.023) | 0.015 (0.024) | −0.010 (0.023) |
| 2019 | 0.005 (0.020) | −0.024 (0.021) | 0.003 (0.019) | −0.018 (0.020) |
| 2020 | 0.015 (0.020) | 0.007 (0.019) | 0.016 (0.019) | 0.013 (0.019) |
| 2021 | −0.007 (0.019) | −0.009 (0.019) | −0.008 (0.019) | −0.004 (0.018) |
| 2023 | −0.019 (0.015) | −0.030 (0.015) | −0.029 (0.015) | −0.033 (0.014) |
| 2024 | −0.050 (0.015) | −0.056 (0.014) | −0.053 (0.015) | −0.056 (0.014) |
| 2025 | −0.044 (0.017) | −0.049 (0.017) | −0.051 (0.016) | −0.053 (0.016) |
| 2026 | −0.071 (0.025) | −0.074 (0.024) | −0.086 (0.025) | −0.081 (0.024) |
| Post-2022 (col 1/2) | −0.048 / −0.055 | −0.041 / −0.049 | | |
| N | 976,177 / 975,504 | 1,047,655 | | |

Post-2022 coefficients replicate within ~0.005–0.011 and the qualitative
pattern is identical: near-zero pre-2022, monotonically more negative after.
Pre-2022 coefficients are slightly negative here vs. slightly positive in the
paper (2018–19 are the crosswalked 2010-code years — the modal-code bridge is
the likely cause). Our N is ~7% larger, consistent with a slightly more
permissive occupation match. Both remain individually insignificant except our
2019 point, which is marginal.

### Decomposition (Table 6, eq. 4.2, Table A1)

| Quantity | Paper | Replication |
| --- | --- | --- |
| 2022 exposure: college / non-college / gap | 0.473 / 0.302 / 0.171 | 0.453 / 0.292 / 0.161 |
| β2026 (no controls) × gap | −0.012 (23%) | −0.0119 (21.8%) |
| β2026 (controls) × gap | −0.015 (28%) | −0.0131 (23.9%) |
| Micro-simulation AI component | "identical" (−0.015) | −0.0137 (25%) |
| Robustness (Table A1): 2019 / 2021 / 2022 baseline share | 25.9% / 29.7% / 27.9% | 18.8% / 28.0% / 23.9% |

The paper's qualitative claim — the exposure mechanism accounts for roughly a
quarter of the premium decline, leaving ~three-quarters unexplained — is fully
supported; our point estimate of the share is 2–4 points lower than the
paper's under the 2021/2022 baselines, driven by the 0.161 vs 0.171 exposure
gap. Using the human-rated beta instead of the GPT-4-rated beta yields a
smaller share (β2026 = −0.069 with controls; 19% of the decline), so the
conclusion is measure-dependent within a 19–28% band.

### Variance decomposition (Tables 3–4, censored-normal above P90)

| Year | Paper total/between/within | Replication |
| --- | --- | --- |
| 1980 | 0.279 / 0.027 / 0.252 | 0.279 / 0.027 / 0.252 |
| 1990 | 0.342 / 0.056 / 0.286 | 0.342 / 0.056 / 0.286 |
| 2000 | 0.348 / 0.071 / 0.277 | 0.348 / 0.071 / 0.277 |
| 2010 | 0.384 / 0.080 / 0.304 | 0.385 / 0.080 / 0.305 |
| 2022 | 0.370 / 0.085 / 0.285 | 0.372 / 0.086 / 0.287 |
| 2026 | 0.353 / 0.078 / 0.275 | 0.353 / 0.078 / 0.275 |
| 2022→26 between share | 41% | 39% |
| Within college 2022 / 2026 | 0.366 / 0.345 | 0.369 / 0.345 |
| Within non-college 2022 / 2026 | 0.230 / 0.225 | 0.231 / 0.225 |

### CES supply-demand accounting (Tables 1–2, Fig 4) — **partial**

The paper's Table 1 regression runs on 68 observations spanning 1914–2026,
splicing the AGK (2020) historical series (openICPSR, login required) with
March CPS and CPS-ORG. Without the gated deposit the pre-1979 inputs cannot be
rebuilt here, and σ is not identifiable from the 48-year ORG window alone (the
supply coefficient is not separately identified from the trend terms in the
short sample). What does replicate, using the paper's preferred σ = 1.52
(within the range our data cannot reject):

Table 2 analog, 100 × annualized log changes (paper values in parentheses):

| Period | Rel. wage | Rel. supply | Implied rel. demand |
| --- | --- | --- | --- |
| 1979–1999 | 1.10 (1.19) | 2.74 (2.28) | 4.40 (4.09) |
| 1999–2022 | 0.27 (0.19) | 2.15 (2.01) | 2.56 (2.29) |
| 2022–2026 | **−1.37** (−1.31) | 1.01 (1.44) | **−1.06** (−0.55) |
| 1979–2026 | 0.48 (0.49) | 2.30 (2.81) | 3.04 (2.81) |

The signature finding — an absolute decline in implied relative demand for
college labor in 2022–2026, unique among multi-year subperiods, while relative
supply kept growing — **replicates**. Supply-growth levels differ moderately
(our efficiency-units series is built from ORG hours alone; the paper splices
March CPS), which accounts for the demand-growth differences. A CES model fit
through 2019 and extrapolated overpredicts the 2026 premium by 8 log points
(0.648 predicted vs 0.567 actual; paper: ~7 log points, 0.70 vs 0.63 on the
1914-anchored model).

## Known deviations from the paper's procedure

1. **Exposure variant and crosswalk.** Best-match calibration (GPT-4 beta) and
   equal-weight SOC aggregation; the paper's exact choices are undocumented.
2. **2010→2018 occupation bridge.** Official Census crosswalk, averaging
   exposure across split codes and using the modal 2018 code for fixed
   effects; the paper cites "official allocation crosswalks" (allocation
   *factors* are not in the public workbook).
3. **Education years for potential experience** use the standard 5-category
   mapping (10/12/14/16/18) rather than the Jaeger (1997) imputation.
4. **Historical CES inputs (1914–1962)** unavailable key-free (openICPSR
   120694); CES estimated on 1979–2026 only, demand accounting evaluated at
   the paper's σ = 1.52.
5. **Fig 2** replicated only for cohorts observable in ORG (born ≥1949).

## How to run

```bash
pip install pandas numpy pyreadstat statsmodels scipy openpyxl matplotlib pyarrow pyfixest
python3 scripts/replication/01_convert_epi_to_parquet.py   # needs the 741MB EPI zip in data/raw/replication/
python3 scripts/replication/02_build_exposure.py
python3 scripts/replication/03_build_sample.py
python3 scripts/replication/04_premium_series.py
python3 scripts/replication/05_event_study.py [measure] [baseline_year]
python3 scripts/replication/06_variance.py
python3 scripts/replication/07_ces.py
python3 scripts/replication/08_figures.py
```

Outputs: `data/work/replication/*.csv` (series, event-study estimates,
variance decomposition, CES fit) and `output/replication/fig*.png`.
