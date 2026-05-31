# Entry № 01 — The costliest of the 20 largest U.S. CSAs

A self-contained report (`index.html`, styled like the recruiting deck) plus the
ranking it is built from (`csa_housing_ranking.csv`, all 184 CSAs).

**Finding.** Among the 20 largest U.S. Combined Statistical Areas, the
**San Jose–San Francisco–Oakland, CA** CSA has the **highest typical home value**
(ZHVI ≈ $1.11M) and the **most extreme price-to-rent ratio** (≈30.3×) in the
country — while ranking only 5th by population and 2nd in rent (behind New York).

## Reproduce

Zillow publishes ZHVI/ZORI at the CBSA ("metro") level, not at the CSA level, so
the CSA view is a roll-up: a Census county→CBSA→CSA crosswalk + county population
(to rank and weight), joined to Zillow's *county* files by 5-digit FIPS. Because
ZHVI/ZORI are typical-value indices, counties are combined as a
**population-weighted mean**, never summed.

```bash
scripts/download_zillow.sh            # County_zhvi.csv, County_zori.csv (+ metro)
scripts/download_csa_crosswalk.sh     # OMB delineation + Census county population
scripts/rank_csa.py                   # writes csa_housing_ranking.csv, prints top 20
cp data/raw/xwalk/csa_housing_ranking.csv reports/csa-housing-ranking/
```

Figures as of: ZHVI/ZORI April 2026 · population 2023 vintage · July 2023 CSA
delineation. Open `index.html` in a browser to view the report.

## Caveats

- County-level ZORI covers ~1,330 of 3,072 counties, so each CSA's rent leans
  toward its more urban counties.
- Since 2000 the Bay Area is up 3.66× — only 3rd among these 20, behind Los
  Angeles (4.23×) and Miami (3.96×).
- Weighting ZHVI by owner-occupied units and ZORI by renter units would be
  marginally more correct; swap the weight in `scripts/rank_csa.py`.
