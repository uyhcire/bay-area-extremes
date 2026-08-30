#!/usr/bin/env python3
"""Is the 2022-2026 college premium decline real? Robustness checks.

Tests the four ways the measured decline could be a data artifact rather than
a real change in relative wages:
  1. sampling noise            -> bootstrap SE / CI on the change
  2. changed topcoding         -> median premium (topcode-immune) and
                                  incidence rates by year x college status
  3. changed earnings imputation -> allocation rates and premium excluding
                                  imputed (hot-deck allocated) earners
  4. partial 2026 year (Jan-Jul) -> Jan-Jul vs full-year premium in past years

Also decomposes the change into college vs non-college real wage movements
(CPI-U deflated) and checks breadth across demographic subgroups.

Outputs: data/work/replication/robustness_{rates,specs,subgroups}.csv
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "replication", "parquet")
WORK = os.path.join(ROOT, "data", "work", "replication")
FLAGS = os.path.join(WORK, "sample_flags.parquet")
CPI = os.path.join(ROOT, "data", "raw", "replication", "CPIAUCSL.csv")


def wmean(x, w):
    return np.average(x, weights=w)


def wquant(x, w, q):
    o = np.argsort(x)
    x, w = np.asarray(x)[o], np.asarray(w)[o]
    c = np.cumsum(w) - 0.5 * w
    return np.interp(q * w.sum(), c, x)


def premium(d, stat="mean"):
    """Raw BA+ vs non-college log wage gap."""
    c = (d.educ >= 4).values
    lw, w = d.lnw.values, d.w.values
    if stat == "mean":
        return wmean(lw[c], w[c]) - wmean(lw[~c], w[~c])
    return wquant(lw[c], w[c], 0.5) - wquant(lw[~c], w[~c], 0.5)


# ---- build the sample carrying imputation / topcode flags -------------------------
if os.path.exists(FLAGS):
    S = pd.read_parquet(FLAGS)
else:
    frames = []
    for f in sorted(glob.glob(os.path.join(RAW, "epi_cpsorg_*.parquet"))):
        df = pd.read_parquet(f, columns=[
            "year", "month", "age", "educ", "wage", "orgwgt",
            "a_earnhour", "a_weekpay", "tc_earnhour", "tc_weekpay"])
        df = df[df.age.between(16, 64) & (df.wage > 0) & df.wage.notna()
                & (df.orgwgt > 0) & df.educ.notna()]
        if not len(df):
            continue
        frames.append(pd.DataFrame({
            "year": df.year.astype(int), "month": df.month.astype(int),
            "educ": df.educ.astype(int), "lnw": np.log(df.wage),
            "w": df.orgwgt.astype(float),
            "alloc": ((df.a_earnhour.fillna(0) == 1)
                      | (df.a_weekpay.fillna(0) == 1)).values,
            "tc": ((df.tc_earnhour.fillna(0) == 1)
                   | (df.tc_weekpay.fillna(0) == 1)).values}))
    S = pd.concat(frames, ignore_index=True)
    S.to_parquet(FLAGS, index=False)

# ---- 1. imputation and topcode incidence by year ---------------------------------
rates = []
for y, d in S.groupby("year"):
    c = (d.educ >= 4).values
    w = d.w.values
    rates.append({"year": y,
                  "alloc_all": wmean(d.alloc.values, w),
                  "alloc_col": wmean(d.alloc.values[c], w[c]),
                  "alloc_non": wmean(d.alloc.values[~c], w[~c]),
                  "tc_col": wmean(d.tc.values[c], w[c]),
                  "tc_non": wmean(d.tc.values[~c], w[~c])})
R = pd.DataFrame(rates).set_index("year")
R.to_csv(os.path.join(WORK, "robustness_rates.csv"))
print("=== imputation (allocation) and topcode rates ===")
print(R.loc[[y for y in [2010, 2019, 2022, 2024, 2026] if y in R.index]].round(3).to_string())
print("\nNote: allocation causes match bias that ATTENUATES the premium, so the\n"
      "2022->2026 fall in allocation rates biases the measured premium UPWARD.")

# ---- 2-4. the change under alternative samples -----------------------------------
SPECS = {
    "baseline (all obs, mean)": (lambda d: d, "mean"),
    "median premium (topcode-immune)": (lambda d: d, "med"),
    "exclude imputed earnings": (lambda d: d[~d.alloc], "mean"),
    "exclude topcoded (BIASED, see note)": (lambda d: d[~d.tc], "mean"),
    "exclude imputed and topcoded (BIASED)": (lambda d: d[~d.alloc & ~d.tc], "mean"),
    "exclude imputed, median": (lambda d: d[~d.alloc], "med"),
    "Jan-Jul months only": (lambda d: d[d.month <= 7], "mean"),
    "Jan-Jul, exclude imputed, median": (
        lambda d: d[(d.month <= 7) & (~d.alloc)], "med"),
}
rows = []
for name, (fn, stat) in SPECS.items():
    a = premium(fn(S[S.year == 2022]), stat)
    b = premium(fn(S[S.year == 2026]), stat)
    rows.append({"spec": name, "y2022": a, "y2026": b, "change": b - a})
SP = pd.DataFrame(rows)
SP.to_csv(os.path.join(WORK, "robustness_specs.csv"), index=False)
print("\n=== premium change under alternative samples ===")
print(SP.round(4).to_string(index=False))
print("\nNote: dropping topcoded observations is NOT a valid check here. College\n"
      "topcode incidence fell from 14.0% (2022) to 7.1% (2026), so the filter\n"
      "deletes twice as much of the college right tail in 2022 as in 2026 and\n"
      "mechanically manufactures a rise. Use the median premium instead.")

# ---- partial-year seasonality -----------------------------------------------------
diffs = []
for y in range(2010, 2026):
    d = S[S.year == y]
    diffs.append(premium(d[d.month <= 7]) - premium(d))
print(f"\nJan-Jul minus full-year premium, 2010-2025: mean {np.mean(diffs):+.4f} "
      f"(sd {np.std(diffs):.4f}) -> 2026 partial year is if anything OVERstated.")

# ---- bootstrap the change ---------------------------------------------------------
rng = np.random.default_rng(11)


def boot(year, n=400):
    d = S[S.year == year]
    lw, w, c = d.lnw.values, d.w.values, (d.educ >= 4).values
    N = len(d)
    out = np.empty(n)
    for i in range(n):
        idx = rng.integers(0, N, N)
        lwi, wi, ci = lw[idx], w[idx], c[idx]
        out[i] = wmean(lwi[ci], wi[ci]) - wmean(lwi[~ci], wi[~ci])
    return out


ch = boot(2026) - boot(2022)
print(f"\n=== bootstrap, 400 reps (resamples individuals; ignores household "
      f"clustering) ===\n  change {ch.mean():+.4f}  SE {ch.std():.4f}  "
      f"t {ch.mean()/ch.std():.1f}  95% CI "
      f"[{np.percentile(ch,2.5):+.4f}, {np.percentile(ch,97.5):+.4f}]  "
      f"P(change>=0) {(ch>=0).mean():.3f}")

# ---- real wage decomposition ------------------------------------------------------
if os.path.exists(CPI):
    cpi = pd.read_csv(CPI, parse_dates=["observation_date"])
    cpi["year"] = cpi.observation_date.dt.year
    cpi["month"] = cpi.observation_date.dt.month
    M = S.merge(cpi[["year", "month", "CPIAUCSL"]], on=["year", "month"], how="left")
    base = cpi[(cpi.year == 2026) & (cpi.month <= 7)].CPIAUCSL.mean()
    M["lnw_real"] = M.lnw - np.log(M.CPIAUCSL / base)
    M = M[M.CPIAUCSL.notna()]
    d22, d26 = M[M.year == 2022], M[M.year == 2026]
    c22, c26 = (d22.educ >= 4).values, (d26.educ >= 4).values
    dc = (wmean(d26.lnw_real.values[c26], d26.w.values[c26])
          - wmean(d22.lnw_real.values[c22], d22.w.values[c22]))
    dn = (wmean(d26.lnw_real.values[~c26], d26.w.values[~c26])
          - wmean(d22.lnw_real.values[~c22], d22.w.values[~c22]))
    print(f"\n=== real (CPI-U deflated) wage change, 2022->2026 ===")
    print(f"  college {dc:+.4f} ({(np.exp(dc)-1)*100:+.1f}%), "
          f"non-college {dn:+.4f} ({(np.exp(dn)-1)*100:+.1f}%)")
    print(f"  college side accounts for {dc/(dc-dn)*100:.0f}% of the "
          f"{dc-dn:+.4f} gap change; the rest is non-college wage GAINS.")

# ---- breadth across subgroups -----------------------------------------------------
base_s = pd.read_parquet(os.path.join(WORK, "sample.parquet"),
                         columns=["year", "age", "female", "race", "educ", "lnw", "w"])
GROUPS = {
    "men": lambda d: d[d.female == 0], "women": lambda d: d[d.female == 1],
    "age 16-29": lambda d: d[d.age < 30],
    "age 30-44": lambda d: d[d.age.between(30, 44)],
    "age 45-64": lambda d: d[d.age >= 45],
    "White": lambda d: d[d.race == 1], "Black": lambda d: d[d.race == 2],
    "Hispanic": lambda d: d[d.race == 3], "Asian": lambda d: d[d.race == 4],
}
sub = [{"group": g, "y2022": premium(fn(base_s[base_s.year == 2022])),
        "y2026": premium(fn(base_s[base_s.year == 2026]))} for g, fn in GROUPS.items()]
SB = pd.DataFrame(sub)
SB["change"] = SB.y2026 - SB.y2022
SB.to_csv(os.path.join(WORK, "robustness_subgroups.csv"), index=False)
print("\n=== breadth: premium change by subgroup ===")
print(SB.round(4).to_string(index=False))
print(f"\n{(SB.change < 0).sum()} of {len(SB)} subgroups decline.")
