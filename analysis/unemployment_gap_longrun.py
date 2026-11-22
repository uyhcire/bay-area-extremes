"""Unemployment rate by education, 1979 -> latest month: exactly high school vs BA or more.

  python3 analysis/unemployment_gap_longrun.py    # -> analysis/output/unemployment_gap_longrun.csv

Ages 18-64 (same as the wage-premium sample). NBER ORG extracts for 1979-2024 (the
quarter of the CPS sample in its outgoing months, final weights); Census basic monthly
files (all rotation groups, composite weights) for 2024 onward -- 2024 from both is a
cross-check. Labour-force questions were redesigned in January 1994.
"""
import io, os, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import cps_org_build as b

MORG, OUT = "data/raw/nber_morg", "analysis/output"


def rates(edu, emp, unemp, w, year, source, months):
    r = {"year": year, "source": source, "months": months}
    for k, m in (("hs", edu == 1), ("ba", edu >= 3)):
        r[f"u_{k}"] = 100 * w[m & unemp].sum() / w[m & (emp | unemp)].sum()
        r[f"n_lf_{k}"] = int((m & (emp | unemp)).sum())
    r["gap"] = r["u_hs"] - r["u_ba"]
    return r


def morg(year):
    it = pd.read_stata(f"{MORG}/morg{year % 100:02d}.dta", iterator=True, convert_categoricals=False)
    have = it.variable_labels()
    d = it.read(columns=[c for c in ("age", "gradeat", "gradecp", "grade92", "esr", "lfsr89", "lfsr94", "weight", "intmonth") if c in have])
    d = d[d.age.between(18, 64)]
    if "grade92" in d:
        e = d.grade92; edu = np.select([e <= 38, e == 39, e <= 42, e == 43], [0, 1, 2, 3], 4)
    else:
        yrs = d.gradeat - (d.gradecp == 2); edu = np.select([yrs < 12, yrs == 12, yrs < 16, yrs < 18], [0, 1, 2, 3], 4)
    if "lfsr94" in d:
        emp, un = d.lfsr94.isin([1, 2]), d.lfsr94.isin([3, 4])
    elif "lfsr89" in d:
        emp, un = d.lfsr89.isin([1, 2]), d.lfsr89.isin([3, 4])
    else:
        emp, un = d.esr.isin([1, 2]), d.esr == 3
    return rates(pd.Series(edu, index=d.index), emp, un, d.weight.fillna(0), year, "nber_morg", d.intmonth.nunique())


def census_month(ym):
    y, m = ym
    raw = b.fetch(f"{b.BASE}/{y}/basic/{b.MON[m - 1]}{y % 100:02d}pub.csv")
    if raw is None:
        return None
    keep = {"prtage", "peeduca", "pemlr", "pwcmpwgt"}
    d = pd.read_csv(io.BytesIO(raw), usecols=lambda c: c.lower() in keep, low_memory=False)
    d.columns = d.columns.str.lower()
    d = d.apply(pd.to_numeric, errors="coerce")
    d = d[d.prtage.between(18, 64) & (d.pwcmpwgt > 0)]
    return d.assign(month=m, year=y)


if __name__ == "__main__":
    rows = [morg(y) for y in range(1979, 2025)]
    today = pd.Timestamp.today()
    yms = [(y, m) for y in range(2024, today.year + 1) for m in range(1, 13) if (y, m) < (today.year, today.month)]
    with ThreadPoolExecutor(6) as ex:
        c = pd.concat([x for x in ex.map(census_month, yms) if x is not None], ignore_index=True)
    e = c.peeduca; c["edu"] = np.select([e <= 38, e == 39, e <= 42, e == 43], [0, 1, 2, 3], 4)
    for y, g in c.groupby("year"):
        rows.append(rates(g.edu, g.pemlr.isin([1, 2]), g.pemlr.isin([3, 4]), g.pwcmpwgt, int(y), "census_basic", g.month.nunique()))
    r = pd.DataFrame(rows); r.to_csv(f"{OUT}/unemployment_gap_longrun.csv", index=False)
    pd.set_option("display.width", 200); print(r.round(2).to_string(index=False))
