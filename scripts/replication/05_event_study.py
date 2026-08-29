#!/usr/bin/env python3
"""AI-exposure event study (Table 5, Figs 3 & 5) and premium decomposition (Table 6, A1).

Specification (paper eq. 4.1), 2018-2026, baseline year 2022:
  ln w_it = sum_tau beta_tau (E_o(i) x 1{t=tau}) + gamma_o + delta_t + e_it
weighted by CPS earnings weights, SEs clustered by occupation. December 2022
respondents are assigned to 2023. Columns (2)/(4) add sex, race, a quartic in
age, and occupation-by-industry fixed effects.
"""
import os
import sys

import numpy as np
import pandas as pd
import pyfixest as pf

WORK = os.path.join(os.path.dirname(__file__), "..", "..", "data", "work", "replication")
MEASURE = sys.argv[1] if len(sys.argv) > 1 else "dv_rating_beta"
BASELINE = int(sys.argv[2]) if len(sys.argv) > 2 else 2022

S = pd.read_parquet(os.path.join(WORK, "sample.parquet"))
D = S[(S.year_es >= 2018) & S.occ.notna() & S[MEASURE].notna()].copy()
D["E"] = D[MEASURE]
D["post"] = (D.year_es >= 2023).astype(int)
D["occ"] = D.occ.astype(int)
print(f"measure={MEASURE} baseline={BASELINE}  N(no controls)={len(D)}")
Dc = D[D.ind.notna()].copy()
Dc["ind"] = Dc.ind.astype(int)
print(f"N(controls)={len(Dc)}")

CTRL = "+ female + C(race) + age + I(age**2) + I(age**3) + I(age**4)"

m1 = pf.feols("lnw ~ post:E | occ + year_es", D, weights="w", vcov={"CRV1": "occ"})
m2 = pf.feols(f"lnw ~ post:E {CTRL} | occ^ind + year_es", Dc, weights="w",
              vcov={"CRV1": "occ"})
m3 = pf.feols(f"lnw ~ i(year_es, E, ref={BASELINE}) | occ + year_es", D,
              weights="w", vcov={"CRV1": "occ"})
m4 = pf.feols(f"lnw ~ i(year_es, E, ref={BASELINE}) {CTRL} | occ^ind + year_es",
              Dc, weights="w", vcov={"CRV1": "occ"})

rows = []
for name, m in [("(1) OLS", m1), ("(2) OLS controls", m2),
                ("(3) event study", m3), ("(4) event study controls", m4)]:
    co, se = m.coef(), m.se()
    for k in co.index:
        if "E" in k:
            rows.append({"col": name, "term": k, "b": co[k], "se": se[k],
                         "N": m._N})
res = pd.DataFrame(rows)
res["term"] = (res.term.str.extract(r"(\d{4})")[0].fillna("post")
               .radd("").str.replace("post", "post2022"))
tab = res.pivot(index="term", columns="col", values=["b", "se"]).round(4)
print(tab.to_string())
res.to_csv(os.path.join(WORK, f"event_study_{MEASURE}_{BASELINE}.csv"), index=False)

# ---- Table 6 / eq (4.2): exposure gap x 2026 coefficient ---------------------------
base = D[D.year_es == BASELINE]
col, non = base.educ >= 4, base.educ < 4
EC = np.average(base.E[col], weights=base.w[col])
EN = np.average(base.E[non], weights=base.w[non])
gap = EC - EN
ser = pd.read_csv(os.path.join(WORK, "series.csv")).set_index("year")
dprem = ser.loc[2026, "premium_adj"] - ser.loc[BASELINE, "premium_adj"]
print(f"\nEC={EC:.3f}  EN={EN:.3f}  gap={gap:.3f}   (paper: 0.473, 0.302, 0.171)")
for name, m in [("no controls (3)", m3), ("controls (4)", m4)]:
    b26 = m.coef().filter(like="2026").iloc[0]
    contrib = b26 * gap
    print(f"beta_2026 {name}: {b26:.3f} -> contribution {contrib:.4f} log pts "
          f"= {100*contrib/dprem:.1f}% of premium change {dprem:.4f}")

# ---- micro-simulation: strip fitted exposure component, recompute adj premium ------
bmap = {int(k.split("::")[1].split(":")[0]): v
        for k, v in m4.coef().items() if k.startswith("year_es::")}
sim = S[S.year.isin([BASELINE, 2026])].copy()
sim["lnw_cf"] = sim.lnw - sim.apply(
    lambda r: bmap.get(int(r.year_es), 0.0) * r[MEASURE]
    if pd.notna(r[MEASURE]) else 0.0, axis=1)
# composition-adjusted premium on actual vs counterfactual wages
EXP_POINTS = [5, 15, 25, 35, 45]
sim["exptier"] = pd.cut(sim["exp"], [-0.01, 9, 19, 29, 39, np.inf], labels=False)
Sall = S.copy()
Sall["exptier"] = pd.cut(Sall["exp"], [-0.01, 9, 19, 29, 39, np.inf], labels=False)
Sall["hrs_w"] = Sall.w * Sall.hours
cell = Sall.groupby(["year", "female", "educ", "exptier"])["hrs_w"].sum().rename("h")
cell = cell / cell.groupby("year").transform("sum")
fixw = cell.groupby(["female", "educ", "exptier"]).mean()


def adj_premium(g, yvar):
    pred = {}
    for sex, gs in g.groupby("female"):
        X_parts, names = [], []
        for e in range(1, 6):
            d = (gs["educ"] == e).astype(float)
            X_parts.append(d); names.append(f"ed{e}")
            for k in range(1, 5):
                X_parts.append(d * gs["exp"] ** k); names.append(f"ed{e}_e{k}")
        for r in range(2, 6):
            X_parts.append((gs["race"] == r).astype(float)); names.append(f"r{r}")
        X = np.column_stack([np.asarray(x, float) for x in X_parts])
        sw = np.sqrt(gs["w"].values)
        beta, *_ = np.linalg.lstsq(X * sw[:, None], gs[yvar].values * sw, rcond=None)
        b = dict(zip(names, beta))
        for e in range(1, 6):
            for tier, xp in enumerate(EXP_POINTS):
                pred[(sex, e, tier)] = b[f"ed{e}"] + sum(
                    b[f"ed{e}_e{k}"] * xp**k for k in range(1, 5))
    pr = pd.Series(pred).rename("yhat")
    pr.index.names = ["female", "educ", "exptier"]
    m_ = pd.concat([pr, fixw.rename("fw")], axis=1).dropna()
    c = m_.loc[m_.index.get_level_values("educ") >= 4]
    h = m_.loc[m_.index.get_level_values("educ") == 2]
    return (np.average(c.yhat, weights=c.fw) - np.average(h.yhat, weights=h.fw))


act = {y: adj_premium(g, "lnw") for y, g in sim.groupby("year")}
cf = {y: adj_premium(g, "lnw_cf") for y, g in sim.groupby("year")}
d_act = act[2026] - act[BASELINE]
d_cf = cf[2026] - cf[BASELINE]
print(f"\nmicro-simulation: actual d(premium) {d_act:.4f}, counterfactual {d_cf:.4f}, "
      f"AI component {d_act - d_cf:.4f} ({100*(d_act-d_cf)/d_act:.0f}%)")
