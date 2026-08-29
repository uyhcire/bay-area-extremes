#!/usr/bin/env python3
"""Between/within-group wage variance, topcode-robust (Tables 3 and 4).

Log wages above each year's (weighted) 90th percentile are treated as
right-censored; censored-normal (Tobit) moments are estimated by weighted MLE
separately by year and college status. Between/within components follow the
two-group identity (paper eq. A2).
"""
import os

import numpy as np
import pandas as pd
from scipy import optimize, stats

WORK = os.path.join(os.path.dirname(__file__), "..", "..", "data", "work", "replication")
S = pd.read_parquet(os.path.join(WORK, "sample.parquet"),
                    columns=["year", "educ", "lnw", "w"])

YEARS = [1980, 1990, 2000, 2010, 2022, 2026]


def wpct(x, w, q):
    o = np.argsort(x)
    x, w = x[o], w[o]
    c = np.cumsum(w) - 0.5 * w
    return np.interp(q * w.sum(), c, x)


def tobit_moments(x, w, c):
    """Weighted MLE of (mu, sigma) for a normal right-censored at c."""
    cens = x >= c
    xo, wo = x[~cens], w[~cens]
    wc = w[cens].sum()

    def nll(theta):
        mu, lnsig = theta
        sig = np.exp(lnsig)
        ll = (wo * (stats.norm.logpdf((xo - mu) / sig) - lnsig)).sum()
        ll += wc * stats.norm.logsf((c - mu) / sig)
        return -ll

    mu0 = np.average(x, weights=w)
    s0 = np.sqrt(np.average((x - mu0) ** 2, weights=w))
    r = optimize.minimize(nll, [mu0, np.log(s0)], method="Nelder-Mead",
                          options={"xatol": 1e-8, "fatol": 1e-6, "maxiter": 5000})
    mu, sig = r.x[0], np.exp(r.x[1])
    return mu, sig**2


rows = {}
for y in YEARS:
    g = S[S.year == y]
    c = wpct(g.lnw.values, g.w.values, 0.90)
    col = g.educ >= 4
    muC, vC = tobit_moments(g.lnw[col].values, g.w[col].values, c)
    muN, vN = tobit_moments(g.lnw[~col].values, g.w[~col].values, c)
    pi = g.w[col].sum() / g.w.sum()
    between = pi * (1 - pi) * (muC - muN) ** 2
    within = pi * vC + (1 - pi) * vN
    rows[y] = {"total": between + within, "between": between, "within": within,
               "within_college": vC, "within_noncollege": vN, "pi": pi,
               "muC_muN": muC - muN}

T = pd.DataFrame(rows)
print(T.round(3).to_string())
T.to_csv(os.path.join(WORK, "variance_decomposition.csv"))

d = T[2026] - T[2022]
print(f"\n2022->2026: total {d['total']:.3f}, between {d['between']:.3f} "
      f"({100*d['between']/d['total']:.0f}%), within {d['within']:.3f} "
      f"({100*d['within']/d['total']:.0f}%)")
print("paper:      total -0.017, between -0.007 (41%), within -0.010 (59%)")
print("paper 2022 col: total .370 between .085 within .285 wC .366 wN .230")
print("paper 2026 col: total .353 between .078 within .275 wC .345 wN .225")
print("paper 1980: .279/.027/.252  1990: .342/.056/.286  2000: .348/.071/.277  "
      "2010: .384/.080/.304")
