#!/usr/bin/env python3
"""Map Eloundou et al. (2023) occupation-level GPT exposure to Census occupation codes.

Inputs (data/raw/replication/):
  occ_level.csv                                 O*NET-SOC exposure (openai/GPTs-are-GPTs)
  2018-occupation-code-list-and-crosswalk.xlsx  Census 2018 occ codes <-> 2018 SOC,
                                                and 2010 -> 2018 census code crosswalk

Outputs (data/work/replication/):
  exposure_occ18.csv   2018 Census occ code -> exposure measures
  exposure_occ10.csv   2010 Census occ code -> exposure measures + modal 2018 code
"""
import os
import re

import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw", "replication")
WORK = os.path.join(os.path.dirname(__file__), "..", "..", "data", "work", "replication")
os.makedirs(WORK, exist_ok=True)

RATINGS = [
    "human_rating_alpha", "human_rating_beta", "human_rating_gamma",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
]

occ = pd.read_csv(os.path.join(RAW, "occ_level.csv"))
occ["soc6"] = occ["O*NET-SOC Code"].str[:7]  # e.g. 11-1011
# collapse O*NET detail codes (.00/.01/...) to 6-digit SOC by simple mean
soc = occ.groupby("soc6")[RATINGS].mean().reset_index()
soc_codes = soc["soc6"].tolist()


def match_soc(census_soc: str) -> list[str]:
    """Return the O*NET 6-digit SOC codes covered by a Census SOC entry."""
    s = str(census_soc).strip()
    if not re.match(r"^\d{2}-[\dX]{4}", s):
        return []
    s = s[:7]
    if "X" in s:
        prefix = s[: s.index("X")]
    elif s in soc_codes:
        return [s]
    elif s.endswith("0"):
        prefix = s[:-1]
    else:
        prefix = s
    while len(prefix) >= 4:  # never broader than "NN-N"
        hits = [c for c in soc_codes if c.startswith(prefix)]
        if hits:
            return hits
        prefix = prefix[:-1].rstrip("0") or prefix[:-1]
    return []


xl = pd.ExcelFile(os.path.join(RAW, "2018-occupation-code-list-and-crosswalk.xlsx"))

# ---- 2018 census code -> exposure -------------------------------------------------
lst = xl.parse("2018 Census Occ Code List", header=4)
lst = lst.rename(columns=lambda c: str(c).strip())
lst = lst[["2018 Census Title", "2018 Census Code", "2018 SOC Code"]].dropna(
    subset=["2018 Census Code", "2018 SOC Code"]
)
# keep detailed rows: 4-digit numeric census codes (headers hold ranges like 0010-0440)
lst = lst[lst["2018 Census Code"].astype(str).str.strip().str.fullmatch(r"\d{4}")]
lst["occ18"] = lst["2018 Census Code"].astype(str).str.strip().astype(int)

rows = []
unmatched = []
for _, r in lst.iterrows():
    socs = []
    for tok in re.split(r"[,;\n]+", str(r["2018 SOC Code"])):
        socs.extend(match_soc(tok))
    if not socs:
        unmatched.append((r["occ18"], r["2018 SOC Code"], r["2018 Census Title"]))
        continue
    sub = soc[soc["soc6"].isin(socs)]
    rows.append({"occ18": r["occ18"], "n_soc": len(socs),
                 **{m: sub[m].mean() for m in RATINGS}})
e18 = pd.DataFrame(rows).groupby("occ18", as_index=False).mean()
e18.to_csv(os.path.join(WORK, "exposure_occ18.csv"), index=False)
print(f"occ18 exposure: {len(e18)} codes; unmatched: {len(unmatched)}")
for u in unmatched[:15]:
    print("  unmatched:", u)

# ---- 2010 census code -> 2018 codes -> exposure -----------------------------------
cw = xl.parse("2010 to 2018 Crosswalk ", header=3)
cw = cw.rename(columns=lambda c: str(c).strip())
cw["occ10"] = pd.to_numeric(cw["2010 Census Code"], errors="coerce").ffill()
cw["occ18"] = pd.to_numeric(cw["2018 Census Code"], errors="coerce")
pairs = cw.dropna(subset=["occ10", "occ18"])[["occ10", "occ18"]].astype(int)

m = pairs.merge(e18, on="occ18", how="left")
e10 = m.groupby("occ10").agg({**{r: "mean" for r in RATINGS},
                              "occ18": "first"}).reset_index()
e10 = e10.rename(columns={"occ18": "occ18_modal"})
e10.to_csv(os.path.join(WORK, "exposure_occ10.csv"), index=False)
print(f"occ10 exposure: {len(e10)} codes "
      f"({e10[RATINGS[1]].notna().sum()} with exposure)")
print(e18[RATINGS].describe().round(3).to_string())
