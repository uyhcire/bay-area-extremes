#!/usr/bin/env python3
"""Rank the 20 largest U.S. CSAs by the ratio of mean female to male
prime-age (25-54) personal income, using 2022 ACS 1-year PUMS.

Geography: PUMA(2020) -> CSA crosswalk built in data/raw/xwalk/ (tract-count
plurality from the 2020 tract->PUMA file + the OMB 2023 CBSA/CSA delineation).
Income: PINCP * ADJINC, weighted by PWGTP. Sex: SEX 1=male, 2=female.
"""
import glob, os
import pandas as pd

XW = "/home/user/bay-area-extremes/data/raw/xwalk"
PUMS = "/home/user/bay-area-extremes/data/raw/pums"

top20 = pd.read_csv(f"{XW}/top20_csa.csv", dtype={"CSA": str})
top20_pop = dict(zip(top20["CSA"], top20["pop"]))
order = list(top20["CSA"])  # population rank order

p2c = pd.read_csv(f"{XW}/puma2csa.csv", dtype={"pumakey": str, "CSA": str})
p2c = p2c.dropna(subset=["CSA"])
p2c = p2c[p2c["CSA"].isin(set(order))]
puma2csa = dict(zip(p2c["pumakey"], p2c["CSA"]))

# CSA titles from delineation
deli = pd.read_excel(f"{XW}/list1.xlsx", header=2, dtype=str).dropna(subset=["CSA Code"])
csa_title = dict(zip(deli["CSA Code"], deli["CSA Title"]))

cols = ["ST", "PUMA", "SEX", "AGEP", "PINCP", "PWGTP", "ADJINC"]
agg = {}  # CSA -> {sex -> [sum(w*inc), sum(w)]}

for f in sorted(glob.glob(f"{PUMS}/psam_p*.csv")):
    df = pd.read_csv(f, usecols=cols, dtype={"ST": str, "PUMA": str})
    df = df[(df["AGEP"] >= 25) & (df["AGEP"] <= 54)].copy()
    df["pumakey"] = df["ST"].str.zfill(2) + df["PUMA"].str.zfill(5)
    df["CSA"] = df["pumakey"].map(puma2csa)
    df = df.dropna(subset=["CSA"])
    if df.empty:
        continue
    df["inc"] = df["PINCP"].fillna(0) * df["ADJINC"] / 1_000_000.0
    df["w"] = df["PWGTP"]
    df["wi"] = df["w"] * df["inc"]
    grp = df.groupby(["CSA", "SEX"])[["wi", "w"]].sum()
    for (csa, sex), row in grp.iterrows():
        d = agg.setdefault(csa, {})
        cur = d.setdefault(int(sex), [0.0, 0.0])
        cur[0] += row["wi"]; cur[1] += row["w"]
    print(f"  processed {os.path.basename(f)} ({len(df):,} prime-age in-CSA records)")

rows = []
for csa in order:
    d = agg.get(csa, {})
    m = d.get(1, [0, 0]); fnum = d.get(2, [0, 0])
    male = m[0] / m[1] if m[1] else float("nan")
    female = fnum[0] / fnum[1] if fnum[1] else float("nan")
    rows.append({
        "CSA": csa, "title": csa_title.get(csa, ""),
        "pop2024": top20_pop[csa],
        "mean_male": male, "mean_female": female,
        "ratio_f_m": female / male if male else float("nan"),
        "w_male": m[1], "w_female": fnum[1],
    })

res = pd.DataFrame(rows)
res = res.sort_values("ratio_f_m", ascending=False).reset_index(drop=True)
res.index += 1
pd.set_option("display.width", 200)
print("\n=== 20 largest CSAs ranked by mean female/male prime-age (25-54) personal income ===\n")
disp = res.copy()
disp["mean_male"] = disp["mean_male"].map(lambda x: f"${x:,.0f}")
disp["mean_female"] = disp["mean_female"].map(lambda x: f"${x:,.0f}")
disp["ratio_f_m"] = disp["ratio_f_m"].map(lambda x: f"{x:.3f}")
disp["pop2024"] = disp["pop2024"].map(lambda x: f"{x:,}")
print(disp[["title", "ratio_f_m", "mean_female", "mean_male", "pop2024"]].to_string())
res.to_csv(f"{XW}/csa_gender_income_ranking.csv")
print(f"\nsaved -> {XW}/csa_gender_income_ranking.csv")
