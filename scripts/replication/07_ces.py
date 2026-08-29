#!/usr/bin/env python3
"""CES supply-demand accounting (partial replication of Tables 1-2, Fig 4).

The paper estimates over 1914, 1939, 1949, 1959, 1963-2026 by splicing the
Autor-Goldin-Katz (2020) historical series (openICPSR deposit, login-gated)
with March CPS and CPS-ORG. Those pre-1979 inputs are not key-free, so this
script estimates the same canonical model on the CPS-ORG years (1979-2026):

    ln(wS/wU)_t = a - (1/sigma) ln(LS/LU)_t + trends

with a post-1992 trend break (the only break inside the ORG window used by the
paper's specification), and computes implied relative demand growth
    D_t = ln(LS/LU)_t + sigma * ln(wS/wU)_t
for the paper's post-1979 subperiods, under both the estimated sigma and the
paper's preferred sigma = 1.52.
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

WORK = os.path.join(os.path.dirname(__file__), "..", "..", "data", "work", "replication")
s = pd.read_csv(os.path.join(WORK, "series.csv")).set_index("year").sort_index()

y = s["premium_adj"]
x = s["rel_supply"]
t = s.index.values - 1914

X = pd.DataFrame({
    "rel_supply": x,
    "time": t,
    "time_post1992": np.where(s.index > 1992, s.index - 1992, 0),
}, index=s.index)
m = sm.OLS(y, sm.add_constant(X)).fit(cov_type="HC1")
print(m.summary().tables[1])
sigma_hat = -1 / m.params["rel_supply"]
print(f"\nrelative supply coefficient: {m.params['rel_supply']:.3f} "
      f"(SE {m.bse['rel_supply']:.3f})  implied sigma = {sigma_hat:.2f}")
print("paper (Table 1, col 2, 1914-2026 sample): -0.659 (SE 0.081), sigma = 1.52")

print("\n=== Table 2 analog: 100 x annualized log changes ===")
print(f"{'period':12s} {'rel wage':>9s} {'rel supply':>10s} "
      f"{'demand (sigma=1.52)':>20s} {'demand (sigma est)':>19s}")
for a, b in [(1979, 1999), (1999, 2022), (2022, 2026), (1979, 2026)]:
    dw = (y[b] - y[a]) / (b - a) * 100
    dx = (x[b] - x[a]) / (b - a) * 100
    for sig, lab in [(1.52, "d152"), (sigma_hat, "dhat")]:
        pass
    d152 = dx + 1.52 * dw
    dhat = dx + sigma_hat * dw
    print(f"{a}-{b:<6d} {dw:9.2f} {dx:10.2f} {d152:20.2f} {dhat:19.2f}")
print("paper rows: 1979-1999: 1.19 / 2.28 / 4.09 | 1999-2022: 0.19 / 2.01 / 2.29 "
      "| 2022-2026: -1.31 / 1.44 / -0.55")

# implied demand series (for Fig 4-style plot and the 'first negative' claim)
D = x + 1.52 * y
dd = D.diff()
neg_runs = [(yy, round(v, 4)) for yy, v in dd.items() if v < 0]
print("\nyears with negative implied demand growth (sigma=1.52):", neg_runs)

# Fig 4 analog: fit through 2019, predict forward with actual supply
fit_mask = s.index <= 2019
m19 = sm.OLS(y[fit_mask], sm.add_constant(X[fit_mask])).fit()
pred = m19.predict(sm.add_constant(X))
out = pd.DataFrame({"actual": y, "predicted_pre2019_model": pred})
out.to_csv(os.path.join(WORK, "ces_fit.csv"))
print(f"\npredicted 2026 premium (model fit through 2019): {pred[2026]:.3f} "
      f"vs actual {y[2026]:.3f}  (paper: 0.70 predicted vs 0.63 actual, "
      f"1914-based model)")
