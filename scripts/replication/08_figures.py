#!/usr/bin/env python3
"""Replication figures (Figures 1, 2 [partial], 3, 4 [analog], 5, 6).

Outputs PNGs to output/replication/.
"""
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
WORK = os.path.join(ROOT, "data", "work", "replication")
OUT = os.path.join(ROOT, "output", "replication")
os.makedirs(OUT, exist_ok=True)

ser = pd.read_csv(os.path.join(WORK, "series.csv")).set_index("year").sort_index()

# ---- Figure 1: raw college premium (BA+ vs non-college) ---------------------------
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(ser.index, ser.premium_raw_noncol, lw=2, color="tab:blue")
ax.axvline(2022, color="gray", ls=":", lw=1)
ax.set_title("Figure 1 replication: raw college wage premium, 1979–2026")
ax.set_ylabel("log wage gap, BA+ vs non-college")
ax.set_xlabel("")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_raw_premium.png"), dpi=150)

# ---- Figure 2 (partial): mean schooling at age 30, cohorts observable in ORG ------
YRS = {1: 10.0, 2: 12.0, 3: 14.0, 4: 16.0, 5: 18.0}
rows = []
for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/replication/parquet/*.parquet"))):
    df = pd.read_parquet(f, columns=["year", "age", "educ", "orgwgt"])
    df = df[(df.age == 30) & (df.orgwgt > 0) & df.educ.notna()]
    if len(df) == 0:
        continue
    df["yrs"] = df.educ.map(YRS)
    rows.append(
        {"cohort": int(df.year.iloc[0]) - 30,
         "yrs": np.average(df.yrs, weights=df.orgwgt)}
    )
coh = pd.DataFrame(rows).groupby("cohort", as_index=False).mean()
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(coh.cohort, coh.yrs, lw=2, color="tab:green")
ax.set_title("Figure 2 replication (partial): mean schooling at age 30 by birth cohort\n"
             "(CPS-ORG cohorts only; 1876–1948 cohorts require Katz 2025 series)")
ax.set_ylabel("years of schooling (5-category approximation)")
ax.set_xlabel("birth cohort")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_schooling_cohort.png"), dpi=150)

# ---- Figure 3: exposure vs college share across occupations (2022) ----------------
S = pd.read_parquet(os.path.join(WORK, "sample.parquet"),
                    columns=["year", "educ", "w", "occ", "dv_rating_beta"])
g = S[(S.year == 2022) & S.occ.notna() & S.dv_rating_beta.notna()].copy()
g["col"] = (g.educ >= 4).astype(float)
occ = g.groupby("occ").apply(
    lambda x: pd.Series({"emp": x.w.sum(),
                         "colshare": np.average(x.col, weights=x.w),
                         "E": x.dv_rating_beta.iloc[0]}), include_groups=False)
occ = occ[occ.colshare > 0.005]
fig, ax = plt.subplots(figsize=(8, 5))
ax.scatter(np.log(occ.colshare), occ.E, s=occ.emp / occ.emp.max() * 600,
           alpha=0.35, color="tab:purple", edgecolors="none")
ax.set_xlabel("log college share, 2022")
ax.set_ylabel("AI exposure (Eloundou et al. beta)")
ax.set_title("Figure 3 replication: AI exposure and college intensity across occupations")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_exposure_college.png"), dpi=150)

# ---- Figure 4 analog: actual vs predicted premium ---------------------------------
ces = pd.read_csv(os.path.join(WORK, "ces_fit.csv"), index_col=0)
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(ces.index, ces.actual, lw=2, label="actual (composition-adjusted)")
ax.plot(ces.index, ces.predicted_pre2019_model, lw=2, ls="--",
        label="predicted (CES model fit 1979–2019)")
ax.axvline(2022, color="gray", ls=":", lw=1)
ax.legend()
ax.set_title("Figure 4 analog: actual vs predicted college premium\n"
             "(ORG-only 1979–2026; paper uses spliced 1914–2026 series)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_actual_vs_predicted.png"), dpi=150)

# ---- Figure 5: event-study coefficients (col 4) -----------------------------------
es = pd.read_csv(os.path.join(WORK, "event_study_dv_rating_beta_2022.csv"))
es = es[(es.col == "(4) event study controls")].copy()
es["yr"] = es.term.str.extract(r"(\d{4})").astype(float)
es = es.dropna(subset=["yr"]).sort_values("yr")
base = pd.DataFrame({"yr": [2022], "b": [0.0], "se": [0.0]})
es = pd.concat([es[["yr", "b", "se"]], base]).sort_values("yr")
fig, ax = plt.subplots(figsize=(8, 5))
ax.fill_between(es.yr, es.b - 1.96 * es.se, es.b + 1.96 * es.se,
                alpha=0.2, color="tab:red")
ax.plot(es.yr, es.b, "o-", color="tab:red")
ax.axhline(0, color="k", lw=0.8)
ax.axvline(2022, color="gray", ls=":", lw=1)
ax.set_title("Figure 5 replication: wages and occupational AI exposure\n"
             "(event-study coefficients, controls + occupation-by-industry FE)")
ax.set_ylabel("coefficient on exposure x year (ref. 2022)")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig5_event_study.png"), dpi=150)

# ---- Figure 6: college premium vs P90-P50 -----------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(ser.index, ser.premium_adj, lw=2, label="college premium (comp.-adjusted)")
ax.plot(ser.index, ser.p90 - ser.p50, lw=2, label="P90–P50")
ax.axvline(2022, color="gray", ls=":", lw=1)
ax.legend()
ax.set_title("Figure 6 replication: college premium and upper-tail inequality")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig6_premium_p9050.png"), dpi=150)

print("figures written to", OUT)
