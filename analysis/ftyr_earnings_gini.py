#!/usr/bin/env python3
"""Earnings Gini for full-time, year-round workers, by state, from ACS PUMS.

Universe: persons 16+ who usually worked 35+ hours/week (WKHP >= 35) and
worked 50+ weeks (WKWN >= 50) in the past 12 months, with positive total
earnings (PERNP > 0: wages + self-employment). This matches Census's usual
"full-time, year-round worker" definition; dropping zero/negative earnings
(self-employment losses) keeps the Gini in [0, 1].

Standard errors use the 80 successive-difference replicate weights
(PWGTP1-80): SE = sqrt(4/80 * sum_r (G_r - G)^2).

Usage:
  scripts/download_acs_pums.sh 2024 1-Year us p
  python3 analysis/ftyr_earnings_gini.py [PUMS_DIR] [OUT_CSV]
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

PUMS_DIR = sys.argv[1] if len(sys.argv) > 1 else "data/raw/acs_pums_2024_1-year"
OUT_CSV = sys.argv[2] if len(sys.argv) > 2 else "analysis/output/ftyr_earnings_gini_2024.csv"

REP = [f"PWGTP{i}" for i in range(1, 81)]
COLS = ["STATE", "AGEP", "WKHP", "WKWN", "PERNP", "ADJINC", "PWGTP"] + REP

STATES = {
    1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT", 10: "DE",
    11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID", 17: "IL", 18: "IN",
    19: "IA", 20: "KS", 21: "KY", 22: "LA", 23: "ME", 24: "MD", 25: "MA",
    26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE", 32: "NV",
    33: "NH", 34: "NJ", 35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH",
    40: "OK", 41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD", 47: "TN",
    48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV", 55: "WI",
    56: "WY", 72: "PR",
}


def load_ftyr(pums_dir):
    files = sorted(glob.glob(os.path.join(pums_dir, "psam_p*.csv")))
    if not files:
        sys.exit(f"no psam_p*.csv files in {pums_dir}")
    parts = []
    for f in files:
        for chunk in pd.read_csv(f, usecols=COLS, chunksize=500_000):
            keep = (
                (chunk.AGEP >= 16)
                & (chunk.WKHP >= 35)
                & (chunk.WKWN >= 50)
                & (chunk.PERNP > 0)
            )
            parts.append(chunk.loc[keep])
    df = pd.concat(parts, ignore_index=True)
    df["EARN"] = df.PERNP * df.ADJINC / 1e6
    return df


def gini(x, w):
    """Weighted Gini of sorted x for each weight column in w (n x k)."""
    W = w.sum(axis=0)
    F = (np.cumsum(w, axis=0) - w / 2) / W  # weighted mid-rank
    wx = w * x[:, None]
    return 2 * (wx * F).sum(axis=0) / wx.sum(axis=0) - 1


def wquantile(x, w, q):
    c = np.cumsum(w) / w.sum()
    return x[np.searchsorted(c, q)]


def summarize(g):
    g = g.sort_values("EARN")
    x = g.EARN.to_numpy(float)
    w = g[["PWGTP"] + REP].to_numpy(float)
    est = gini(x, w)
    g0, reps = est[0], est[1:]
    pw = w[:, 0]
    p10, p50, p90 = (wquantile(x, pw, q) for q in (0.1, 0.5, 0.9))
    return pd.Series({
        "gini": g0,
        "gini_se": np.sqrt(4 / 80 * ((reps - g0) ** 2).sum()),
        "workers_weighted": pw.sum(),
        "n_sample": len(x),
        "p10": p10,
        "median": p50,
        "p90": p90,
        "p90_p10": p90 / p10,
        "mean": np.average(x, weights=pw),
    })


def main():
    df = load_ftyr(PUMS_DIR)
    df["state"] = df.STATE.map(STATES)
    by_state = df.groupby("state").apply(summarize, include_groups=False)
    us = summarize(df[df.STATE != 72]).rename("US (50 + DC)")
    out = pd.concat([by_state, us.to_frame().T])
    out = out.sort_values("gini", ascending=False)
    out["rank"] = out.gini.drop(us.name).rank(ascending=False)
    out["rank"] = out["rank"].fillna(0).astype(int)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.round(5).to_csv(OUT_CSV, index_label="state")
    with pd.option_context("display.max_rows", 100, "display.width", 140):
        print(out[["rank", "gini", "gini_se", "median", "p90_p10", "workers_weighted", "n_sample"]]
              .round({"gini": 4, "gini_se": 4, "median": 0, "p90_p10": 2, "workers_weighted": 0}))
    print(f"\nwrote {OUT_CSV}")


if __name__ == "__main__":
    main()
