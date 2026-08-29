#!/usr/bin/env python3
"""Build the pooled CPS-ORG analysis sample, 1979-2026.

Sample: wage & salary earners age 16-64 with positive hourly earnings (EPI `wage`),
weighted by CPS earnings weights (`orgwgt`), mirroring Section 2.1 of the paper.

Output: data/work/replication/sample.parquet
"""
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "replication", "parquet")
WORK = os.path.join(ROOT, "data", "work", "replication")
os.makedirs(WORK, exist_ok=True)

# years of schooling by 5-category education (for potential experience)
YRS = {1: 10.0, 2: 12.0, 3: 14.0, 4: 16.0, 5: 18.0}

e18 = pd.read_csv(os.path.join(WORK, "exposure_occ18.csv"))
e10 = pd.read_csv(os.path.join(WORK, "exposure_occ10.csv"))
RATINGS = [c for c in e18.columns if c.endswith(("alpha", "beta", "gamma"))]

frames = []
for f in sorted(glob.glob(os.path.join(RAW, "epi_cpsorg_*.parquet"))):
    df = pd.read_parquet(f)
    keep = (
        df["age"].between(16, 64)
        & (df["wage"] > 0)
        & df["wage"].notna()
        & (df["orgwgt"] > 0)
    )
    df = df[keep].copy()

    out = pd.DataFrame(
        {
            "year": pd.to_numeric(df["year"], errors="coerce"),
            "month": pd.to_numeric(df["month"], errors="coerce"),
            "age": pd.to_numeric(df["age"], errors="coerce"),
            "female": pd.to_numeric(df["female"], errors="coerce"),
            "race": pd.to_numeric(df["wbhao"], errors="coerce"),
            "educ": pd.to_numeric(df["educ"], errors="coerce"),
            "lnw": np.log(pd.to_numeric(df["wage"], errors="coerce")),
            "w": pd.to_numeric(df["orgwgt"], errors="coerce"),
        }
    )
    out = out.dropna(subset=["year", "month", "age", "female", "educ", "lnw", "w"])
    df = df.loc[out.index]
    for c in ["year", "month", "age", "female", "educ"]:
        out[c] = out[c].astype(int)
    out["race"] = out["race"].fillna(1).astype(int)
    out = out.reset_index(drop=True)
    df = df.reset_index(drop=True)
    # usual weekly hours (for hours-weighted supply aggregates)
    hrs = pd.Series(np.nan, index=df.index)
    for c in ["hoursu1", "hoursuorg", "hourslw1"]:
        if c in df.columns:
            hrs = hrs.fillna(pd.to_numeric(df[c], errors="coerce"))
    out["hours"] = hrs.clip(upper=99).fillna(40.0)

    out["exp"] = (out["age"] - out["educ"].map(YRS) - 6).clip(lower=0)

    # harmonized 2018 occupation + exposure
    if df.get("occ18") is not None and df["occ18"].notna().any():
        out["occ"] = pd.to_numeric(df["occ18"], errors="coerce")
        out = out.merge(e18.rename(columns={"occ18": "occ"}), on="occ", how="left")
    elif "occ10" in df.columns and df["occ10"].notna().any():
        occ10 = pd.to_numeric(df["occ10"], errors="coerce").rename("occ10")
        tmp = pd.concat([out, occ10], axis=1)
        tmp = tmp.merge(e10, on="occ10", how="left")
        tmp["occ"] = tmp["occ18_modal"]
        out = tmp.drop(columns=["occ10", "occ18_modal"])
    else:
        out["occ"] = np.nan
        for r in RATINGS:
            out[r] = np.nan

    out["ind"] = (
        pd.to_numeric(df["dind03"], errors="coerce")
        if "dind03" in df.columns
        else np.nan
    )
    for c in ["tc_weekpay", "tc_earnhour"]:
        out[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int) \
            if c in df.columns else 0
    frames.append(out)
    print(os.path.basename(f), len(out), flush=True)

full = pd.concat(frames, ignore_index=True)
# event-study year: December 2022 respondents assigned to 2023 (Table 5 note)
full["year_es"] = np.where(
    (full["year"] == 2022) & (full["month"] == 12), 2023, full["year"]
)
full.to_parquet(os.path.join(WORK, "sample.parquet"), index=False)
print("TOTAL", len(full), "obs across", full["year"].nunique(), "years")
print(full.groupby("year").size().to_string())
