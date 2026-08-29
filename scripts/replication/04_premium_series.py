#!/usr/bin/env python3
"""Annual wage-structure series, 1979-2026.

Produces data/work/replication/series.csv with, per year:
  premium_raw_hs      raw college premium: BA+ vs high-school-only mean log wage
  premium_raw_noncol  raw gap: BA+ vs all non-college workers
  premium_adj         composition-adjusted college premium (Appendix A method)
  rel_supply          log college-equivalent / high-school-equivalent labor
                      supply in efficiency units
  p10, p50, p90       weighted percentiles of log hourly wages
Also sample descriptives quoted in Section 2.1.
"""
import os

import numpy as np
import pandas as pd

WORK = os.path.join(os.path.dirname(__file__), "..", "..", "data", "work", "replication")
S = pd.read_parquet(
    os.path.join(WORK, "sample.parquet"),
    columns=["year", "age", "female", "race", "educ", "exp", "lnw", "w", "hours"],
)

print("=== Section 2.1 descriptives ===")
wt = S["w"]
print("N =", len(S))
print("mean age =", round(np.average(S["age"], weights=wt), 1))
print("pct female =", round(100 * np.average(S["female"], weights=wt), 1))
print("pct BA+ =", round(100 * np.average((S["educ"] >= 4), weights=wt), 1))

EXP_POINTS = [5, 15, 25, 35, 45]
S["exptier"] = pd.cut(S["exp"], [-0.01, 9, 19, 29, 39, np.inf], labels=False)


def wmean(x, w):
    return np.average(x, weights=w)


def wpct(x, w, q):
    o = np.argsort(x.values)
    x, w = x.values[o], w.values[o]
    c = np.cumsum(w) - 0.5 * w
    return np.interp(q * w.sum(), c, x)


# ---- fixed hours weights for the composition adjustment ---------------------------
S["hrs_w"] = S["w"] * S["hours"]
cell = S.groupby(["year", "female", "educ", "exptier"])["hrs_w"].sum().rename("h")
cell = cell / cell.groupby("year").transform("sum")          # within-year shares
fixw = cell.groupby(["female", "educ", "exptier"]).mean()     # avg share, 1979-2026

# ---- efficiency-unit prices (fixed over the full period) --------------------------
S["lnw_hrs"] = S["lnw"] * S["hrs_w"]
eff = (
    S.groupby(["female", "educ", "exptier"])
    .apply(lambda g: np.exp(np.average(g["lnw"], weights=g["hrs_w"])), include_groups=False)
    .rename("effprice")
)

rows = []
for year, g in S.groupby("year"):
    rec = {"year": year}

    ba = g["educ"] >= 4
    hs = g["educ"] == 2
    rec["premium_raw_hs"] = wmean(g.loc[ba, "lnw"], g.loc[ba, "w"]) - wmean(
        g.loc[hs, "lnw"], g.loc[hs, "w"]
    )
    rec["premium_raw_noncol"] = wmean(g.loc[ba, "lnw"], g.loc[ba, "w"]) - wmean(
        g.loc[~ba, "lnw"], g.loc[~ba, "w"]
    )
    for q, name in [(0.1, "p10"), (0.5, "p50"), (0.9, "p90")]:
        rec[name] = wpct(g["lnw"], g["w"], q)

    # -- composition-adjusted premium: year-by-sex wage regressions -----------------
    pred = {}
    for sex, gs in g.groupby("female"):
        X_parts, names = [], []
        for e in range(1, 6):
            d = (gs["educ"] == e).astype(float)
            X_parts.append(d)
            names.append(f"ed{e}")
            for k in range(1, 5):
                X_parts.append(d * gs["exp"] ** k)
                names.append(f"ed{e}_exp{k}")
        for r in range(2, 6):
            X_parts.append((gs["race"] == r).astype(float))
            names.append(f"race{r}")
        X = np.column_stack([np.asarray(x, dtype=float) for x in X_parts])
        y = gs["lnw"].values
        sw = np.sqrt(gs["w"].values)
        beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
        b = dict(zip(names, beta))
        for e in range(1, 6):
            for tier, xp in enumerate(EXP_POINTS):
                pred[(sex, e, tier)] = b[f"ed{e}"] + sum(
                    b[f"ed{e}_exp{k}"] * xp**k for k in range(1, 5)
                )

    pr = pd.Series(pred).rename("yhat")
    pr.index.names = ["female", "educ", "exptier"]
    m = pd.concat([pr, fixw.rename("fw")], axis=1).dropna()
    col = m.loc[m.index.get_level_values("educ") >= 4]
    hsx = m.loc[m.index.get_level_values("educ") == 2]
    rec["premium_adj"] = np.average(col["yhat"], weights=col["fw"]) - np.average(
        hsx["yhat"], weights=hsx["fw"]
    )

    # -- relative supply in efficiency units ----------------------------------------
    hrs = g.groupby(["female", "educ", "exptier"])["hrs_w"].sum().rename("hrs")
    me = pd.concat([hrs, eff], axis=1).dropna()
    q = me["hrs"] * me["effprice"]
    ed = q.index.get_level_values("educ")
    LS = q[ed >= 4].sum() + 0.5 * q[ed == 3].sum()
    LU = q[ed <= 2].sum() + 0.5 * q[ed == 3].sum()
    rec["rel_supply"] = np.log(LS / LU)

    rows.append(rec)
    print(year, "adj:", round(rec["premium_adj"], 3), "raw:",
          round(rec["premium_raw_hs"], 3), flush=True)

out = pd.DataFrame(rows).sort_values("year")
out.to_csv(os.path.join(WORK, "series.csv"), index=False)

print("\n=== Key benchmarks vs paper ===")
for y, paper_adj, paper_raw in [(1979, 0.339, 0.410), (2016, 0.633, None),
                                 (2019, 0.625, None), (2022, 0.623, 0.649),
                                 (2026, 0.570, 0.591)]:
    r = out[out.year == y].iloc[0]
    print(f"{y}: adj {r.premium_adj:.3f} (paper {paper_adj}) "
          f"raw {r.premium_raw_hs:.3f} (paper {paper_raw})")
