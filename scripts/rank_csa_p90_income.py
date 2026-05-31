#!/usr/bin/env python3
"""Rank the largest U.S. Combined Statistical Areas (CSAs) by the 90th
percentile of *personal* income, using ACS PUMS microdata.

Pipeline (all sources key-free, downloaded to data/raw/):
  1. CSA population (Census Population Estimates, csa-est<VINTAGE>) -> pick the
     N largest CSAs, and a county(FIPS)->CSA lookup (county rows carry STCOU+CSA).
  2. 2020 Census tract -> 2020 PUMA relationship file. Each tract row also gives
     its county, so we map every (state, PUMA) to the CSA holding the plurality
     of its tracts. PUMAs are the finest geography in PUMS; this is the standard
     PUMA-based metro approximation (boundary PUMAs go to their plurality CSA).
  3. ACS 1-Year PUMS person files for every state touching a top-N CSA. For the
     income universe (persons 15+, i.e. PINCP not null) we compute the weighted
     (PWGTP) percentiles of PINCP*ADJINC/1e6, the inflation-adjusted personal
     income in survey-year dollars.

Percentiles use the interpolated (Hazen) weighted-CDF method. Note that PINCP is
rounded/heaped by the Census Bureau at round-number values, so nearby metros can
tie at a heap (e.g. ~$120k); P95/P99 are reported as finer tiebreakers.

Usage:  python3 scripts/rank_csa_p90_income.py [PUMS_YEAR] [TOP_N] [POP_VINTAGE]
Default: 2023 1-Year PUMS, top 20 CSAs, 2024 population vintage.
"""
import os, sys, json, subprocess
import numpy as np
import pandas as pd

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2023
TOP_N = int(sys.argv[2]) if len(sys.argv) > 2 else 20
POP_VINTAGE = int(sys.argv[3]) if len(sys.argv) > 3 else 2024

RAW = os.path.join("data", "raw", "csa_p90_income")
OUTDIR = "analysis"
os.makedirs(RAW, exist_ok=True)
os.makedirs(OUTDIR, exist_ok=True)

FIPS2AB = {1:'al',2:'ak',4:'az',5:'ar',6:'ca',8:'co',9:'ct',10:'de',11:'dc',
12:'fl',13:'ga',15:'hi',16:'id',17:'il',18:'in',19:'ia',20:'ks',21:'ky',22:'la',
23:'me',24:'md',25:'ma',26:'mi',27:'mn',28:'ms',29:'mo',30:'mt',31:'ne',32:'nv',
33:'nh',34:'nj',35:'nm',36:'ny',37:'nc',38:'nd',39:'oh',40:'ok',41:'or',42:'pa',
44:'ri',45:'sc',46:'sd',47:'tn',48:'tx',49:'ut',50:'vt',51:'va',53:'wa',54:'wv',
55:'wi',56:'wy'}


def fetch(url, dest, binary=True):
    if not os.path.exists(dest):
        subprocess.run(["curl", "-s", "--retry", "4", "--max-time", "600",
                        "-o", dest, url], check=True)
    return dest


def main():
    # 1. CSA populations + county->CSA -----------------------------------------
    csa_url = ("https://www2.census.gov/programs-surveys/popest/datasets/"
               f"2020-{POP_VINTAGE}/metro/totals/csa-est{POP_VINTAGE}-alldata.csv")
    csa = pd.read_csv(fetch(csa_url, f"{RAW}/csa-est{POP_VINTAGE}.csv"),
                      encoding="latin-1", dtype=str)
    popcol = f"POPESTIMATE{POP_VINTAGE}"
    csa[popcol] = pd.to_numeric(csa[popcol])
    tot = (csa[csa["LSAD"] == "Combined Statistical Area"]
           [["CSA", "NAME", popcol]].rename(columns={popcol: "pop"})
           .sort_values("pop", ascending=False).reset_index(drop=True))
    topN = tot.head(TOP_N).copy()
    codes = set(topN["CSA"])
    cnty = csa[(csa["LSAD"] == "County or equivalent") & csa["CSA"].notna()
               & (csa["STCOU"].str.len() == 5)]
    county2csa = dict(zip(cnty["STCOU"], cnty["CSA"]))

    # 2. tract->PUMA -> (state,puma)->CSA by plurality of tracts ----------------
    rel_url = ("https://www2.census.gov/geo/docs/maps-data/data/rel2020/"
               "2020_Census_Tract_to_2020_PUMA.txt")
    t = pd.read_csv(fetch(rel_url, f"{RAW}/tract2puma.csv"), dtype=str,
                    encoding="utf-8-sig")
    t.columns = [c.strip() for c in t.columns]
    t["CSA"] = (t["STATEFP"] + t["COUNTYFP"]).map(county2csa)
    t["statefips"] = t["STATEFP"].astype(int)
    t["puma"] = t["PUMA5CE"].astype(int)

    def plurality(g):
        vc = g["CSA"].value_counts(dropna=False)  # NaN = tracts outside any CSA
        top = vc.idxmax()
        return top if isinstance(top, str) else np.nan
    p2c = (t.groupby(["statefips", "puma"]).apply(plurality, include_groups=False)
           .dropna().rename("CSA").reset_index())
    key2csa = {(r.statefips, r.puma): r.CSA for r in p2c.itertuples()}
    states = sorted(p2c[p2c["CSA"].isin(codes)]["statefips"].unique().tolist())

    # 3. PUMS person files for each needed state --------------------------------
    base = (f"https://www2.census.gov/programs-surveys/acs/data/pums/"
            f"{YEAR}/1-Year")
    inc = {c: [] for c in codes}
    wt = {c: [] for c in codes}
    for fips in states:
        ab = FIPS2AB[fips]
        zf = f"{RAW}/csv_p{ab}.zip"
        fetch(f"{base}/csv_p{ab}.zip", zf)
        subprocess.run(["unzip", "-o", "-q", zf, "-d", RAW], check=True)
        pf = f"{RAW}/psam_p{fips:02d}.csv"
        df = pd.read_csv(pf, usecols=["PUMA", "STATE", "ADJINC", "PWGTP", "PINCP"],
                         dtype={"PUMA": "Int32", "STATE": "Int16", "PWGTP": "Int32"})
        df = df[df["PINCP"].notna()]
        df["income"] = df["PINCP"].astype("float64") * df["ADJINC"].astype("float64") / 1e6
        df["CSA"] = [key2csa.get((s, p)) for s, p in
                     zip(df["STATE"].astype(int), df["PUMA"].astype(int))]
        df = df[df["CSA"].isin(codes)]
        for c, g in df.groupby("CSA"):
            inc[c].append(g["income"].to_numpy())
            wt[c].append(g["PWGTP"].to_numpy(dtype="float64"))
        os.remove(zf); os.remove(pf)
        print(f"  {ab.upper()}: {len(df):>8,} person-records", flush=True)

    # 4. weighted interpolated percentiles --------------------------------------
    def wpct(v, w, q):
        o = np.argsort(v); v, w = v[o], w[o].astype("float64")
        cw = np.cumsum(w)
        return float(np.interp(q, (cw - 0.5 * w) / w.sum(), v))

    rows = []
    for c in codes:
        v = np.concatenate(inc[c]); w = np.concatenate(wt[c])
        rows.append({"CSA": c, "p50": wpct(v, w, .5), "p90": wpct(v, w, .9),
                     "p95": wpct(v, w, .95), "p99": wpct(v, w, .99),
                     "n_persons_15plus": int(w.sum()), "n_records": len(v)})
    res = (pd.DataFrame(rows).merge(topN, on="CSA")
           .sort_values("p90", ascending=False).reset_index(drop=True))
    res.insert(0, "rank", res.index + 1)
    out = f"{OUTDIR}/csa_p90_personal_income_{YEAR}.csv"
    res.to_csv(out, index=False)

    pd.set_option("display.width", 200)
    print(f"\nLargest {TOP_N} CSAs ranked by 90th-pctile personal income "
          f"(ACS {YEAR} 1-yr PUMS, persons 15+, {YEAR}$):\n")
    for _, r in res.iterrows():
        print(f"{r['rank']:>2}. P90 ${r['p90']:>9,.0f}  median ${r['p50']:>7,.0f}  "
              f"P95 ${r['p95']:>9,.0f}  pop {r['pop']:>11,}  {r['NAME']}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
