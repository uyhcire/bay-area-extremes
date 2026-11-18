#!/usr/bin/env python3
"""Nowcast Bay Area county real GDP for a year BEA has not yet published.

BEA publishes county GDP ~12 months after the reference year, but two of its
main ingredients are out ~6 months earlier:

  * state GDP by industry (BEA SAGDP2/SAGDP9; keyless bulk ZIP), and
  * county wages by industry (BLS QCEW annual averages; keyless API).

BEA itself builds county GDP largely by allocating state industry GDP to
counties in proportion to county earnings, so we mimic that:

  real growth[c, i] = (1 + CA real growth[i]) * (wage share[c, i, t] /
                       wage share[c, i, t-1]) ** LAMBDA[i]  - 1

where wage share = county / California QCEW wages in sector i, and LAMBDA is a
shrinkage factor (0 = "county grows like the state sector", 1 = "full
wage-share shift"). Sector growth is aggregated with prior-year nominal county
GDP weights (Laspeyres approximation to BEA's Fisher chaining).

The script backtests every variant on 2018..(last published year) and then
prints the nowcast for TARGET.

With --partial the script instead tracks a year that is still in progress,
using BEA *quarterly* state GDP by industry (SQGDP9) and QCEW first-quarter
wages: year-over-year growth of the quarters published so far, weighted by
county GDP from two years earlier (the latest that would have been published
at that point). It is backtested against BEA's eventual full-year growth.

Usage: scripts/estimate_county_gdp.py [--partial] [TARGET_YEAR] [DATA_DIR]
       (defaults: 2025 (2026 with --partial), data/raw/gdp_nowcast)
"""
import csv
import io
import os
import subprocess
import sys
import zipfile

import pandas as pd

PARTIAL = "--partial" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
TARGET = int(ARGS[0]) if ARGS else (2026 if PARTIAL else 2025)
DATA = ARGS[1] if len(ARGS) > 1 else "data/raw/gdp_nowcast"
FIRST = 2018  # first backtest year (needs QCEW for FIRST-1)

COUNTIES = {
    "06001": "Alameda", "06013": "Contra Costa", "06041": "Marin",
    "06055": "Napa", "06075": "San Francisco", "06081": "San Mateo",
    "06085": "Santa Clara", "06095": "Solano", "06097": "Sonoma",
}
# BEA LineCode -> QCEW industry_code ("GOV" = all government ownerships)
SECTORS = {
    3: "11", 6: "21", 10: "22", 11: "23", 12: "31-33", 34: "42", 35: "44-45",
    36: "48-49", 45: "51", 51: "52", 56: "53", 60: "54", 64: "55", 65: "56",
    69: "61", 70: "62", 76: "71", 79: "72", 82: "81", 83: "GOV",
}
NAMES = {
    3: "Agriculture", 6: "Mining", 10: "Utilities", 11: "Construction",
    12: "Manufacturing", 34: "Wholesale", 35: "Retail", 36: "Transport/whse",
    45: "Information", 51: "Finance/insurance", 56: "Real estate",
    60: "Prof/sci/tech", 64: "Mgmt of companies", 65: "Admin/support",
    69: "Education (private)", 70: "Health care", 76: "Arts/rec",
    79: "Accommodation/food", 82: "Other services", 83: "Government",
}
UA = "bay-area-extremes/1.0 (research script)"


def fetch(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    subprocess.run(["curl", "-sSfL", "--retry", "4", "-A", UA, url, "-o", dest],
                   check=True)


def bea_table(zipname, member_prefix):
    """Long frame (fips, line, year, value) from a BEA regional bulk ZIP."""
    path = os.path.join(DATA, zipname + ".zip")
    fetch(f"https://apps.bea.gov/regional/zip/{zipname}.zip", path)
    with zipfile.ZipFile(path) as z:
        member = next(n for n in z.namelist() if n.startswith(member_prefix))
        text = z.read(member).decode("latin-1")
    rows = [r for r in csv.reader(io.StringIO(text)) if len(r) > 8]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    df["fips"] = df["GeoFIPS"].str.strip().str.strip('"')
    df["line"] = pd.to_numeric(df["LineCode"], errors="coerce")
    years = [c for c in df.columns if c[:4].isdigit()]
    long = df.melt(["fips", "line"], years, "year", "value")
    if ":Q" in years[0]:   # quarterly table: index by (year, quarter)
        long["qtr"] = long["year"].str[-1].astype(int)
        long["year"] = long["year"].str[:4].astype(int)
        long["value"] = pd.to_numeric(long["value"], errors="coerce")
        return long.dropna(subset=["line"]).set_index(
            ["fips", "line", "year", "qtr"])["value"]
    long["year"] = long["year"].astype(int)
    long["value"] = pd.to_numeric(long["value"], errors="coerce")  # (D) -> NaN
    return long.dropna(subset=["line"]).set_index(["fips", "line", "year"])["value"]


def qcew_wages(years, qtr="a"):
    """Series (fips, qcew_industry, year) -> total wages (annual or one qtr)."""
    tag = "" if qtr == "a" else f"q{qtr}"
    col = "total_annual_wages" if qtr == "a" else "total_qtrly_wages"
    out = []
    for y in years:
        for a in ["06000", *COUNTIES]:
            path = os.path.join(DATA, f"qcew_{y}{tag}_{a}.csv")
            fetch(f"https://data.bls.gov/cew/data/api/{y}/{qtr}/area/{a}.csv", path)
            q = pd.read_csv(path, dtype={"area_fips": str, "industry_code": str})
            q = q[q["disclosure_code"].isna()]
            sec = q[(q.own_code == 5) & q.agglvl_code.isin([54, 74])]
            gov = q[q.own_code.isin([1, 2, 3]) & q.agglvl_code.isin([51, 71])]
            w = sec.groupby("industry_code")[col].sum()
            w["GOV"] = gov[col].sum()
            out.append(pd.DataFrame({"fips": a, "year": y, "ind": w.index,
                                     "wages": w.values}))
    return pd.concat(out).set_index(["fips", "ind", "year"])["wages"]


def main():
    cnom = bea_table("CAGDP2", "CAGDP2_CA_")     # county nominal, $thousands
    creal = bea_table("CAGDP9", "CAGDP9_CA_")    # county real, chained $
    sreal = bea_table("SAGDP", "SAGDP9_CA_")     # state real by industry
    last_pub = int(cnom.index.get_level_values("year").max())
    last_state = int(sreal.index.get_level_values("year").max())
    if PARTIAL:
        return partial(cnom, creal, last_pub)
    if TARGET > last_state:
        sys.exit(f"State GDP by industry only runs through {last_state}.")
    wages = qcew_wages(range(FIRST - 1, TARGET + 1))

    def share_ratio(c, line, t):
        ind = SECTORS[line]
        try:
            s1 = wages[(c, ind, t)] / wages[("06000", ind, t)]
            s0 = wages[(c, ind, t - 1)] / wages[("06000", ind, t - 1)]
        except KeyError:
            return 1.0          # suppressed QCEW cell -> assume constant share
        r = s1 / s0
        return r if 0.5 < r < 2.0 else 1.0

    def predict(c, t, lam):
        """Predicted real growth of county c in year t (weights from t-1)."""
        tot_w = cnom[(c, 1, t - 1)]
        state_tot = sreal[("06000", 1, t)] / sreal[("06000", 1, t - 1)] - 1
        acc, used, contrib = 0.0, 0.0, {}
        for line in SECTORS:
            w = cnom.get((c, line, t - 1))
            if w is None or pd.isna(w):
                continue        # (D) cell: falls into the residual below
            gs = sreal[("06000", line, t)] / sreal[("06000", line, t - 1)]
            g = gs * share_ratio(c, line, t) ** lam.get(line, lam["default"]) - 1
            contrib[line] = w / tot_w * g
            acc += contrib[line]
            used += w / tot_w
        acc += (1 - used) * state_tot  # suppressed sectors grow like the state
        return acc, contrib

    def actual(c, t):
        return creal[(c, 1, t)] / creal[(c, 1, t - 1)] - 1

    def region(vals, t):  # nominal-weighted aggregate of county growth rates
        w = pd.Series({c: cnom[(c, 1, t - 1)] for c in COUNTIES})
        return float((pd.Series(vals) * w).sum() / w.sum())

    variants = {
        "state sector growth only (lambda=0)": {"default": 0.0},
        "full wage-share shift (lambda=1)": {"default": 1.0, 56: 0.0},
        "half wage-share shift (lambda=0.5)": {"default": 0.5, 56: 0.0},
    }
    naive = {t: sreal[("06000", 1, t)] / sreal[("06000", 1, t - 1)] - 1
             for t in range(FIRST, TARGET + 1)}

    print(f"County GDP published through {last_pub}; state GDP through "
          f"{last_state}; QCEW through {TARGET}.\n")
    print("=== Backtest: Bay Area (9-county) real GDP growth, % ===")
    bt_years = range(FIRST, last_pub + 1)
    act_reg = {t: region({c: actual(c, t) for c in COUNTIES}, t) for t in bt_years}
    rows = {"ACTUAL (BEA)": act_reg, "naive: CA total growth": naive}
    preds = {}
    for name, lam in variants.items():
        preds[name] = {t: {c: predict(c, t, lam)[0] for c in COUNTIES}
                       for t in range(FIRST, TARGET + 1)}
        rows[name] = {t: region(preds[name][t], t) for t in bt_years}
    bt = pd.DataFrame(rows).T * 100
    bt["MAE"] = (bt[list(bt_years)] - bt.loc["ACTUAL (BEA)", list(bt_years)]
                 ).abs().mean(axis=1)
    print(bt.round(2).to_string(), "\n")

    print("=== Backtest: county-level mean abs error (pp), all county-years ===")
    for name in variants:
        errs = [abs(preds[name][t][c] - actual(c, t))
                for t in bt_years for c in COUNTIES]
        print(f"  {name:40s} {100 * sum(errs) / len(errs):.2f}")
    errs = [abs(naive[t] - actual(c, t)) for t in bt_years for c in COUNTIES]
    print(f"  {'naive: CA total growth':40s} {100 * sum(errs) / len(errs):.2f}\n")

    if TARGET <= last_pub:
        return
    best = min(variants, key=lambda n: bt.loc[n, "MAE"])
    print(f"=== {TARGET} nowcast, real GDP growth % (best backtest variant: "
          f"{best}) ===")
    tab = pd.DataFrame({n: preds[n][TARGET] for n in variants}) * 100
    tab.index = [COUNTIES[c] for c in tab.index]
    tab.loc["BAY AREA (9 counties)"] = [
        100 * region(preds[n][TARGET], TARGET) for n in variants]
    tab[f"actual {last_pub}"] = [100 * actual(c, last_pub) for c in COUNTIES] + [
        100 * act_reg[last_pub]]
    print(tab.round(2).to_string())
    print(f"\nCalifornia total real GDP growth {TARGET}: "
          f"{100 * naive[TARGET]:.2f}%\n")

    print(f"=== {TARGET} sector contributions to Bay Area growth (pp), {best} ===")
    w = pd.Series({c: cnom[(c, 1, TARGET - 1)] for c in COUNTIES})
    con = pd.DataFrame({c: predict(c, TARGET, variants[best])[1]
                        for c in COUNTIES}).fillna(0)
    reg = (con * w).sum(axis=1) / w.sum() * 100
    reg.index = [NAMES[i] for i in reg.index]
    print(reg.sort_values(ascending=False).round(2).to_string())


def partial(cnom, creal, last_pub):
    """Track an in-progress year from quarterly state GDP + Q1 county wages."""
    sq = bea_table("SQGDP", "SQGDP9_CA_").sort_index()
    have = sq[("06000", 1, TARGET)].dropna().index.tolist()   # quarters out
    wages = qcew_wages(range(FIRST - 1, TARGET + 1), qtr=1)
    first = FIRST + 1                                        # needs t-2 weights

    def state_growth(line, t, qs):
        return (sum(sq[("06000", line, t, q)] for q in qs) /
                sum(sq[("06000", line, t - 1, q)] for q in qs))

    def share_ratio(c, line, t):
        ind = SECTORS[line]
        try:
            r = ((wages[(c, ind, t)] / wages[("06000", ind, t)]) /
                 (wages[(c, ind, t - 1)] / wages[("06000", ind, t - 1)]))
        except KeyError:
            return 1.0
        return r if 0.5 < r < 2.0 else 1.0

    def predict(c, t, qs, lam):
        wy = min(t - 2, last_pub)
        tot_w, acc, used = cnom[(c, 1, wy)], 0.0, 0.0
        for line in SECTORS:
            w = cnom.get((c, line, wy))
            if w is None or pd.isna(w):
                continue
            l = 0.0 if line == 56 else lam
            g = state_growth(line, t, qs) * share_ratio(c, line, t) ** l - 1
            acc += w / tot_w * g
            used += w / tot_w
        return acc + (1 - used) * (state_growth(1, t, qs) - 1)

    def region(vals, t):
        w = pd.Series({c: cnom[(c, 1, min(t - 2, last_pub))] for c in COUNTIES})
        return float((pd.Series(vals) * w).sum() / w.sum())

    def actual(c, t):
        return creal[(c, 1, t)] / creal[(c, 1, t - 1)] - 1

    years = range(first, TARGET + 1)
    bt = [t for t in years if t <= last_pub]
    rows = {"ACTUAL full-year (BEA)": {
        t: 100 * region({c: actual(c, t) for c in COUNTIES}, t) for t in bt}}
    preds = {}
    for qs in ([1], have):
        for lam in (0.0, 0.5, 1.0):
            name = f"Q{qs[0]}-Q{qs[-1]} state yoy, lambda={lam}"
            preds[name] = {t: {c: predict(c, t, qs, lam) for c in COUNTIES}
                           for t in years}
            rows[name] = {t: 100 * region(preds[name][t], t) for t in years}
    tab = pd.DataFrame(rows).T[list(years)]
    tab["MAE"] = (tab[bt] - tab.loc["ACTUAL full-year (BEA)", bt]).abs().mean(axis=1)
    tab["bias"] = (tab[bt] - tab.loc["ACTUAL full-year (BEA)", bt]).mean(axis=1)
    print(f"State quarterly GDP through {TARGET} Q{have[-1]}; QCEW wages "
          f"through {TARGET} Q1; county GDP through {last_pub}.\n")
    print("=== Bay Area real GDP, partial-year yoy growth vs eventual "
          "full-year growth, % ===")
    print(tab.round(2).to_string(), "\n")
    best = min(preds, key=lambda n: tab.loc[n, "MAE"])
    print(f"=== {TARGET} partial-year yoy by county, % ({best}) ===")
    out = pd.Series({COUNTIES[c]: 100 * v for c, v in preds[best][TARGET].items()})
    out["BAY AREA (9 counties)"] = tab.loc[best, TARGET]
    print(out.round(2).to_string())
    print(f"\nCalifornia total, same quarters yoy: "
          f"{100 * (state_growth(1, TARGET, have) - 1):.2f}%")


if __name__ == "__main__":
    main()
