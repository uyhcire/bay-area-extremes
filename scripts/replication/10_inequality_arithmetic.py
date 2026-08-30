#!/usr/bin/env python3
"""Why did total wage inequality fall so much less than the college premium?

The two-group identity (paper eq. A2) is
    Var(ln w) = pi(1-pi)(muC - muN)^2  +  pi*VarC + (1-pi)*VarN
                \_____ between _____/     \____ within ____/

This script decomposes the 2022->2026 change in total log-wage variance into
(a) the education gap ("price") effect, (b) the college-share (composition)
effect, and (c) within-group compression, and then quantifies what the
CPS-ORG hourly wage sample structurally cannot observe about "overall"
inequality.

Inputs : data/work/replication/variance_decomposition.csv (from 06_variance.py)
         data/work/replication/sample_flags.parquet       (from 09_robustness.py)
         data/raw/replication/wage_share_gdi.csv          (FRED W270RE1A156NBEA)
Output : data/work/replication/inequality_arithmetic.csv
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
WORK = os.path.join(ROOT, "data", "work", "replication")
RAW = os.path.join(ROOT, "data", "raw", "replication")

V = pd.read_csv(os.path.join(WORK, "variance_decomposition.csv"), index_col=0)
a, b = V["2022"], V["2026"]
p0, p1 = a["pi"], b["pi"]
g0, g1 = a["muC_muN"], b["muC_muN"]
vc0, vc1 = a["within_college"], b["within_college"]
vn0, vn1 = a["within_noncollege"], b["within_noncollege"]

between = lambda p, g: p * (1 - p) * g**2
within = lambda p, vc, vn: p * vc + (1 - p) * vn

print("=== 1. LEVERAGE: how much of total variance can the education gap move? ===")
print(f"  between-group variance = pi(1-pi) * gap^2, with pi(1-pi) = {p0*(1-p0):.4f}")
print(f"  gap      {g0:.4f} -> {g1:.4f}  ({g1-g0:+.4f})")
print(f"  between  {between(p0,g0):.4f} -> {between(p1,g1):.4f}  "
      f"({between(p1,g1)-between(p0,g0):+.4f})")
print(f"  between-group is only {a['between']/a['total']*100:.0f}% of total variance; "
      f"the other {100-a['between']/a['total']*100:.0f}% sits WITHIN education groups.")

print("\n=== 2. SHIFT-SHARE: the rising college share offsets the compression ===")
bt_gap = between(p0, g1) - between(p0, g0)
bt_comp = between(p1, g1) - between(p0, g1)
wt_var = within(p0, vc1, vn1) - within(p0, vc0, vn0)
wt_comp = within(p1, vc1, vn1) - within(p0, vc1, vn1)
print(f"  college share pi {p0:.4f} -> {p1:.4f} (+{(p1-p0)*100:.1f} pp)")
print(f"  between: gap effect {bt_gap:+.4f} | composition {bt_comp:+.4f}")
print(f"  within : variance effect {wt_var:+.4f} | composition {wt_comp:+.4f}")
print(f"  composition is inequality-INCREASING: college workers have the higher")
print(f"  internal variance ({vc0:.3f} vs {vn0:.3f}), so moving workers into that")
print(f"  group raises within-variance. Total composition {bt_comp+wt_comp:+.4f}, "
      f"offsetting {abs((bt_comp+wt_comp)/(bt_gap+wt_var))*100:.0f}% of the price compression.")

print("\n=== 3. COUNTERFACTUAL: freeze the education gap at its 2022 value ===")
cf = between(p1, g0) + within(p1, vc1, vn1)
share = abs((b["total"] - cf) / (b["total"] - a["total"])) * 100
print(f"  actual 2026 total {b['total']:.4f}; gap frozen {cf:.4f} "
      f"({b['total']-cf:+.4f})")
print(f"  => the premium collapse explains {share:.0f}% of the observed "
      f"{b['total']-a['total']:+.4f} variance decline.")

print("\n=== 4. WITHIN-GROUP COMPRESSION does the rest ===")
print(f"  within-college    {vc0:.4f} -> {vc1:.4f} ({vc1-vc0:+.4f})")
print(f"  within-noncollege {vn0:.4f} -> {vn1:.4f} ({vn1-vn0:+.4f})")
print(f"  college workers became more equal among themselves; weighted, that is "
      f"{abs((vc1-vc0)*p1/(b['total']-a['total']))*100:.0f}% of the total decline alone.")

pd.DataFrame({
    "component": ["between_gap_effect", "between_composition", "within_variance_effect",
                  "within_composition", "total_observed"],
    "value": [bt_gap, bt_comp, wt_var, wt_comp, b["total"] - a["total"]],
}).to_csv(os.path.join(WORK, "inequality_arithmetic.csv"), index=False)

print("\n=== 5. WHAT THIS SAMPLE STRUCTURALLY CANNOT SEE ===")
for y in [2022, 2026]:
    E = SE = WS = 0.0
    for f in sorted(glob.glob(os.path.join(RAW, "parquet", f"epi_cpsorg_{y}*.parquet"))):
        d = pd.read_parquet(f, columns=["age", "wage", "orgwgt", "cow1", "emp"])
        d = d[d.age.between(16, 64) & (d.orgwgt > 0) & (d.emp == 1)]
        E += d.orgwgt.sum()
        SE += d[d.cow1.isin([6, 7])].orgwgt.sum()
        WS += d[(d.wage > 0) & d.wage.notna()].orgwgt.sum()
    print(f"  {y}: self-employed {SE/E*100:.1f}% of the employed are EXCLUDED; "
          f"{WS/E*100:.1f}% have a usable hourly wage")

S = pd.read_parquet(os.path.join(WORK, "sample_flags.parquet"))
for y in [2022, 2026]:
    d = S[S.year == y]
    c = (d.educ >= 4).values
    print(f"  {y}: topcoded {np.average(d.tc.values, weights=d.w.values)*100:.1f}% overall, "
          f"{np.average(d.tc.values[c], weights=d.w.values[c])*100:.1f}% of college workers "
          f"-> the top is censored, not measured")

ws_path = os.path.join(RAW, "wage_share_gdi.csv")
if os.path.exists(ws_path):
    ws = pd.read_csv(ws_path, parse_dates=["observation_date"])
    ws.columns = ["date", "share"]
    ws["year"] = ws.date.dt.year
    r = ws[ws.year.isin([2000, 2010, 2019, 2022, 2024])].groupby("year").share.mean()
    print("\n  wage & salary share of gross domestic income (FRED W270RE1A156NBEA):")
    print("    " + "  ".join(f"{int(y)}: {v:.1f}%" for y, v in r.items()))
    print(f"    => ~{100-r.iloc[-1]:.0f}% of national income is not wages/salaries and is")
    print("       entirely invisible here (capital income, business income, transfers).")
print("\n  Also missing: annual earnings (hours/weeks/unemployment spells), household")
print("  income, non-workers, and wealth. 'Overall inequality' is NOT answerable here.")
