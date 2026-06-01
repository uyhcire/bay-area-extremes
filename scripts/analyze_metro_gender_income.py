#!/usr/bin/env python3
"""Rank the 20 largest U.S. metros by the ratio of mean female to male
prime-age (25-54) personal income, from 2022 ACS 1-year PUMS.

Supports two geography levels (run both by default):
  * cbsa  -- Metropolitan Statistical Areas (OMB CBSAs, Metro only)
  * csa   -- Combined Statistical Areas

Pipeline (all inputs live under data/raw/, git-ignored but reproducible):
  1. OMB 2023 delineation (list1.xlsx): county -> CBSA / CSA + titles.
  2. County population estimates (co-est.csv, 2024): summed to CBSA/CSA to
     pick the 20 largest metros.
  3. 2020 tract->PUMA file: PUMA(2020) -> metro by tract-count plurality
     (the non-metro bucket competes, so a PUMA only joins a metro when the
     metro holds a plurality of its tracts).
  4. PUMS person records: income = PINCP * ADJINC (2022 $), weighted by
     PWGTP; ratio = mean female / mean male for AGEP 25-54. ADJINC cancels
     in the ratio but is applied so the printed means are correct.

Connecticut note: the 2020 tract->PUMA file uses old CT county FIPS while the
2023 delineation/popest use planning-region FIPS. For the CSA level the only
top-20 CT piece is old Fairfield County -> New York-Newark CSA (patched). No
CT county is in a top-20 MSA, so no patch is needed there.
"""
import glob, os, sys
import pandas as pd

ROOT = "/home/user/bay-area-extremes"
XW = f"{ROOT}/data/raw/xwalk"
PUMS = f"{ROOT}/data/raw/pums"

LEVELS = {
    "cbsa": {"code": "CBSA Code", "title": "CBSA Title", "metro_only": True},
    "csa":  {"code": "CSA Code",  "title": "CSA Title",  "metro_only": False},
}


def load_delineation():
    return pd.read_excel(f"{XW}/list1.xlsx", header=2, dtype=str)


def build(level):
    cfg = LEVELS[level]
    code, titlecol = cfg["code"], cfg["title"]
    deli = load_delineation()
    if cfg["metro_only"]:
        deli = deli[deli["Metropolitan/Micropolitan Statistical Area"]
                    == "Metropolitan Statistical Area"]
    deli = deli.dropna(subset=[code]).copy()
    deli["cty"] = deli["FIPS State Code"].str.zfill(2) + deli["FIPS County Code"].str.zfill(3)
    cty2m = dict(zip(deli["cty"], deli[code]))
    title = dict(zip(deli[code], deli[titlecol]))

    # --- top 20 by population ---
    pop = pd.read_csv(f"{XW}/co-est.csv", encoding="latin-1",
                      dtype={"STATE": str, "COUNTY": str})
    pop = pop[pop["SUMLEV"] == 50].copy()
    pop["cty"] = pop["STATE"].str.zfill(2) + pop["COUNTY"].str.zfill(3)
    pop["m"] = pop["cty"].map(cty2m)
    mpop = pop.dropna(subset=["m"]).groupby("m")["POPESTIMATE2024"].sum()
    top20 = mpop.sort_values(ascending=False).head(20)
    order = list(top20.index)

    # --- PUMA -> metro (tract-count plurality, non-metro competes) ---
    tr = pd.read_csv(f"{XW}/tract_to_puma2020.txt", dtype=str)
    tr.columns = [c.strip().lstrip("﻿") for c in tr.columns]
    tr["cty"] = tr["STATEFP"].str.zfill(2) + tr["COUNTYFP"].str.zfill(3)
    if level == "csa":
        cty2m = dict(cty2m); cty2m["09001"] = "408"   # old Fairfield Co. -> NY CSA
    tr["m"] = tr["cty"].map(cty2m).fillna("NONE")
    tr["pk"] = tr["STATEFP"].str.zfill(2) + tr["PUMA5CE"].str.zfill(5)
    g = tr.groupby(["pk", "m"]).size().reset_index(name="n")
    win = g.loc[g.groupby("pk")["n"].idxmax()]
    puma2m = {r.pk: r.m for r in win.itertuples() if r.m in set(order)}

    return order, title, dict(top20), puma2m


def analyze(level):
    order, title, top20pop, puma2m = build(level)
    cols = ["ST", "PUMA", "SEX", "AGEP", "PINCP", "PWGTP", "ADJINC"]
    agg = {}
    for f in sorted(glob.glob(f"{PUMS}/psam_p*.csv")):
        df = pd.read_csv(f, usecols=cols, dtype={"ST": str, "PUMA": str})
        df = df[(df["AGEP"] >= 25) & (df["AGEP"] <= 54)].copy()
        df["pk"] = df["ST"].str.zfill(2) + df["PUMA"].str.zfill(5)
        df["m"] = df["pk"].map(puma2m)
        df = df.dropna(subset=["m"])
        if df.empty:
            continue
        df["wi"] = df["PWGTP"] * df["PINCP"].fillna(0) * df["ADJINC"] / 1e6
        for (m, sx), r in df.groupby(["m", "SEX"])[["wi", "PWGTP"]].sum().iterrows():
            cur = agg.setdefault(m, {}).setdefault(int(sx), [0.0, 0.0])
            cur[0] += r["wi"]; cur[1] += r["PWGTP"]

    rows = []
    for m in order:
        d = agg.get(m, {}); ml = d.get(1, [0, 0]); fe = d.get(2, [0, 0])
        male = ml[0] / ml[1] if ml[1] else float("nan")
        fem = fe[0] / fe[1] if fe[1] else float("nan")
        rows.append({"code": m, "title": title.get(m, ""), "pop2024": top20pop[m],
                     "mean_female": fem, "mean_male": male, "ratio_f_m": fem / male,
                     "prime_age_pop": ml[1] + fe[1]})
    res = pd.DataFrame(rows).sort_values("ratio_f_m", ascending=False).reset_index(drop=True)
    res.index += 1
    out = f"{XW}/{level}_gender_income_ranking.csv"
    res.to_csv(out)

    d = res.copy()
    d["mean_female"] = d["mean_female"].map("${:,.0f}".format)
    d["mean_male"] = d["mean_male"].map("${:,.0f}".format)
    d["ratio_f_m"] = d["ratio_f_m"].map("{:.3f}".format)
    d["pop2024"] = d["pop2024"].map("{:,}".format)
    print(f"\n=== Top 20 {level.upper()}s by mean female/male prime-age (25-54) personal income ===\n")
    print(d[["title", "ratio_f_m", "mean_female", "mean_male", "pop2024"]].to_string())
    print(f"saved -> {out}")


if __name__ == "__main__":
    levels = sys.argv[1:] or ["cbsa", "csa"]
    for lv in levels:
        analyze(lv)
