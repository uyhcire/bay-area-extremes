"""Median college wage premium, 1979 -> latest month.

  python3 analysis/cps_org_build.py                 # Census basic monthly, 2015+ (key-free)
  # NBER ORG extracts 1979-2024 (key-free): https://data.nber.org/morg/annual/morg<yy>.dta
  #   -> data/raw/nber_morg/ ; CPI: fredgraph.csv?id=CPIAUCSL&cosd=1978-01-01 -> data/raw/nber_morg/CPIAUCSL.csv
  python3 analysis/college_premium_longrun.py       # -> analysis/output/college_premium_longrun.csv

Medians are used because the top-code changed four times (weekly cap $999 to 1988,
$1,923 to 1997, $2,884.61 to Mar 2023, then top 3% replaced by their mean). A median
is unaffected by what happens above it, so no top-code adjustment is needed as long
as the (conditional) median lies below the cap.

Two series per year:
  adj  coefficient on BA-or-more (vs exactly high school) from a weighted median
       regression of log hourly wage on education dummies, a quartic in potential
       experience x sex, race/ethnicity and month dummies
  raw  log(median wage, BA or more) - log(median wage, exactly high school)
Sample: wage & salary workers 18-64, non-imputed weekly earnings where the flag exists
(flags are incomplete 1989-93 and absent Jan 1994 - Aug 1995). The NBER May CPS extracts give
1973-78 (one month a year, so noisier; 1979 from both is a cross-check). NBER ORG files are used for
1979-2024, the Census files for 2025+; 2015-2024 from both sources is a cross-check.
"""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import college_premium_cps as cp

MORG = "data/raw/nber_morg"
COLS = ["intmonth", "age", "sex", "race", "ethnic", "gradeat", "gradecp", "grade92", "class", "class94",
        "uhourse", "hourslw", "paidhre", "earnhre", "earnwke", "earnwt", "I25d"]


def cap(y):
    return 999 if y <= 1988 else 1923 if y <= 1997 else 2884


def morg(year, cpi):
    it = pd.read_stata(f"{MORG}/morg{year % 100:02d}.dta", iterator=True, convert_categoricals=False)
    d = it.read(columns=[c for c in COLS if c in it.variable_labels()])
    cls = d["class94"].between(1, 5) if "class94" in d else d["class"].between(1, 4)
    d = d[d.age.between(18, 64) & cls & (d.earnwke > 0) & (d.earnwt > 0)].copy()
    d["date"] = pd.to_datetime(dict(year=year, month=d.intmonth, day=1))
    hours = d.uhourse.where(d.uhourse > 0, d.hourslw); hours = hours.where(hours > 0)
    hourly = (d.paidhre == 1) & (d.earnhre > 0)
    d["w"] = np.where(hourly, d.earnhre / 100.0, d.earnwke / hours)
    d = d[d.w.notna()].copy()
    d["top"] = np.where(hourly[d.index], False, d.earnwke >= cap(year))
    d = d[d.w / (d.date.map(cpi) / cpi[cp.REF]) >= 3.0].copy()
    d["lnw"] = np.log(d.w)
    if "grade92" in d:
        e = d.grade92
        d["edu"] = np.select([e <= 38, e == 39, e <= 42, e == 43], [0, 1, 2, 3], 4)
        yrs = e.map({39: 12, 40: 13, 41: 14, 42: 14, 43: 16, 44: 18, 45: 19, 46: 21}).fillna(10)
    else:
        yrs = d.gradeat - (d.gradecp == 2)
        d["edu"] = np.select([yrs < 12, yrs == 12, yrs < 16, yrs < 18], [0, 1, 2, 3], 4)
    d["exp"] = (d.age - yrs - 6).clip(lower=0)
    d["female"] = (d.sex == 2).astype(float)
    hisp = d.ethnic.between(1, 7) if year < 2003 else d.ethnic.notna()
    d["race"] = np.select([hisp, d.race == 1, d.race == 2], [1, 0, 2], 3)
    d["imputed"] = (d.I25d.fillna(0) > 0) if "I25d" in d else False
    d["wt"] = d.earnwt
    return d[["date", "lnw", "wt", "edu", "exp", "female", "race", "imputed", "top"]]


def may(year, cpi):
    """NBER May CPS extract (1973-78: whole May sample asked usual earnings; non-response not imputed)."""
    d = pd.read_stata(f"data/raw/nber_may/cpsmay{year % 100:02d}.dta", convert_categoricals=False,
                      columns=["x67", "x69", "x70", "x72", "x73", "x85", "x108", "x185", "x186", "x187", "x188", "x80"])
    d = d[d.x67.between(18, 64) & (d.x108 == 1) & (d.x186 > 0) & (d.x80 > 0)].copy()
    d["date"] = pd.Timestamp(year, 5, 1)
    hourly = (d.x187 == 1) & (d.x188 > 0)
    d["w"] = np.where(hourly, d.x188 / 100.0, d.x186 / d.x185.where(d.x185 > 0))
    d = d[d.w.notna()].copy()
    d["top"] = ~hourly[d.index] & (d.x186 >= 999)
    d = d[d.w / (cpi[d.date.iloc[0]] / cpi[cp.REF]) >= 3.0].copy()
    d["lnw"] = np.log(d.w)
    yrs = d.x72 - 1 - (d.x73 == 2)
    d["edu"] = np.select([yrs < 12, yrs == 12, yrs < 16, yrs < 18], [0, 1, 2, 3], 4)
    d["exp"] = (d.x67 - yrs - 6).clip(lower=0)
    d["female"] = (d.x70 == 2).astype(float)
    d["race"] = np.select([d.x85.between(1, 7), d.x69 == 1, d.x69 == 2], [1, 0, 2], 3)
    d["imputed"] = False
    d["wt"] = d.x80
    return d[["date", "lnw", "wt", "edu", "exp", "female", "race", "imputed", "top"]]


def wmedian(x, w):
    i = np.argsort(x.values); c = np.cumsum(w.values[i])
    return x.values[i][np.searchsorted(c, 0.5 * c[-1])]


def estimate(d, year, source):
    full = d; d = d[~d.imputed]
    X = cp.design(d); X = X.loc[:, (X != 0).any()]
    col, hs = d.edu >= 3, d.edu == 1
    return {"year": year, "source": source, "n": len(d), "months": d.date.nunique(),
            "adj": cp.median_reg(d.lnw, X, d.wt),
            "raw": wmedian(d.lnw[col], d.wt[col]) - wmedian(d.lnw[hs], d.wt[hs]),
            "pct_imputed_flag": 100 * np.average(full.imputed, weights=full.wt),
            "pct_college_topcoded": 100 * np.average(d.top[col], weights=d.wt[col]),
            "college_share": 100 * np.average(col, weights=d.wt),
            "hisp_share": 100 * np.average(d.race == 1, weights=d.wt)}


if __name__ == "__main__":
    cpi = pd.read_csv(f"{MORG}/CPIAUCSL.csv", parse_dates=["observation_date"]).set_index("observation_date").CPIAUCSL
    cpi = cpi.reindex(pd.date_range(cpi.index.min(), cpi.index.max(), freq="MS")).interpolate()
    out = f"{cp.OUT}/college_premium_longrun.csv"
    rows = pd.read_csv(out).to_dict("records") if os.path.exists(out) else []      # resumable
    done = {(r["source"], r["year"]) for r in rows}

    def add(frame, y, source):
        if (source, y) in done:
            return
        rows.append(estimate(frame(), y, source)); print(rows[-1], flush=True)
        pd.DataFrame(rows).to_csv(out, index=False)

    if os.path.exists("data/raw/nber_may/cpsmay73.dta"):        # May only; 1979 overlaps the ORG series
        for y in range(1973, 1980):
            add(lambda: may(y, cpi), y, "nber_may")
    for y in range(1979, 2025):
        add(lambda: morg(y, cpi), y, "nber_morg")
    c = cp.load()
    c["lnw"] = np.log(c.w_pub); c["imputed"] = c.prwernal == 1
    c["top"] = ~c.hourly & c.wk_top
    for y in sorted(c.hryear4.unique()):
        add(lambda: c[c.hryear4 == y], int(y), "census_basic")
