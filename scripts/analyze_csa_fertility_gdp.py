#!/usr/bin/env python3
"""Fertility vs. per-capita GDP across the 15 largest U.S. CSAs.

Question: is the New York CSA's unusually high fertility (for a top metro)
explained by the same thing as its unusually low per-capita GDP?

Inputs (fetched by scripts/download_csa_fertility.sh into data/raw/csa_fertility/):
  list1_2023.xlsx                    OMB July-2023 CBSA/CSA delineation (county -> CSA)
  co-est2025-alldata.csv             Census PEP Vintage 2025 county births + population
  cc-est2025-agesex-all.csv          Census PEP county population by age x sex
  bea/CAGDP1, CAINC4 __ALL_AREAS     BEA county GDP and personal income components
  pums/psam_pus{a,b}.csv             ACS 2024 1-year PUMS, person records, all U.S.
  2020_Census_Tract_to_2020_PUMA.txt tract -> PUMA (used to place PUMAs in CSAs)

Usage: python3 scripts/analyze_csa_fertility_gdp.py [DATA_DIR]
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

D = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "data", "raw", "csa_fertility")
OUT = os.path.join(D, "out")
os.makedirs(OUT, exist_ok=True)
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
NTOP = 15
NYC = "New York"

# ---------------------------------------------------------------- geography
delin = pd.read_excel(os.path.join(D, "list1_2023.xlsx"), header=2, dtype=str)
delin = delin.dropna(subset=["FIPS State Code", "CSA Code"])
delin["fips"] = delin["FIPS State Code"].str.zfill(2) + delin["FIPS County Code"].str.zfill(3)
delin["csa"] = delin["CSA Title"].str.split("-").str[0].str.split(",").str[0]
fips2csa = delin.set_index("fips")["csa"]

# ---------------------------------------------------------------- PEP: births, women by age
co = pd.read_csv(os.path.join(D, "co-est2025-alldata.csv"), encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
co = co[co.SUMLEV == 50].copy()
co["fips"] = co.STATE + co.COUNTY
co["csa"] = co.fips.map(fips2csa)

cc = pd.read_csv(os.path.join(D, "cc-est2025-agesex-all.csv"), encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
cc["fips"] = cc.STATE + cc.COUNTY
AG = ["1519", "2024", "2529", "3034", "3539", "4044"]
# YEAR 5 = 7/1/2023, 6 = 7/1/2024; BIRTHS2024 covers 7/1/2023-6/30/2024 -> mid-period women
w = cc[cc.YEAR.isin([5, 6])].groupby("fips")[[f"AGE{a}_FEM" for a in AG] + ["POPESTIMATE", "UNDER5_TOT", "AGE65PLUS_TOT"]].mean()
w["u18"] = cc[cc.YEAR.isin([5, 6])].assign(u=lambda d: d.POPESTIMATE - d.AGE18PLUS_TOT).groupby("fips").u.mean()
co = co.join(w, on="fips")

# National age-specific fertility rates, 2023 final (NCHS NVSR 74-1), births per 1,000 women.
US_ASFR = {"1519": 13.1, "2024": 55.4, "2529": 91.0, "3034": 94.9, "3539": 54.3, "4044": 12.5 + 1.1}
US_TFR = 1.621


def fert(g):
    """GFR and an indirectly standardized TFR (national age schedule scaled to local births)."""
    women = sum(g[f"AGE{a}_FEM"].sum() for a in AG)
    expected = sum(g[f"AGE{a}_FEM"].sum() * US_ASFR[a] / 1000 for a in AG)
    b = g.BIRTHS2024.sum()
    return pd.Series({
        "pop_m": g.POPESTIMATE2024.sum() / 1e6,
        "births": b,
        "gfr": 1000 * b / women,
        "tfr_std": US_TFR * b / expected,
        "pct_u18": 100 * g.u18.sum() / g.POPESTIMATE.sum(),
        "pct_65p": 100 * g.AGE65PLUS_TOT.sum() / g.POPESTIMATE.sum(),
    })


top = co.groupby("csa").POPESTIMATE2024.sum().nlargest(NTOP).index.tolist()
F = co[co.csa.isin(top)].groupby("csa").apply(fert, include_groups=False)
us_f = fert(co)

# ---------------------------------------------------------------- BEA: GDP + income
def bea(table, lines):
    f = glob.glob(os.path.join(D, "bea", f"{table}__ALL_AREAS*.csv"))[0]
    b = pd.read_csv(f, encoding="latin-1", dtype=str, skipfooter=4, engine="python")
    b["fips"] = b.GeoFIPS.str.replace('"', "").str.strip()
    b["LineCode"] = b.LineCode.str.strip()
    b = b[b.LineCode.isin([str(x) for x in lines])]
    b["v"] = pd.to_numeric(b["2024"], errors="coerce")
    return b.pivot_table(index=["fips", "GeoName"], columns="LineCode", values="v").reset_index()


gdp = bea("CAGDP1", [3]).rename(columns={"3": "gdp_k"})
inc = bea("CAINC4", [10, 20, 45, 46, 47, 50]).rename(columns={
    "10": "pi_k", "20": "bea_pop", "45": "netearn_k", "46": "dir_k", "47": "transfers_k", "50": "wages_pow_k"})
B = gdp.merge(inc, on=["fips", "GeoName"], how="outer")
B = B[~B.fips.str.endswith("000")].dropna(subset=["gdp_k"])
B["csa"] = B.fips.map(fips2csa)
# BEA merges Virginia independent cities into "County + City" areas (519xx): place by first-named county.
va = delin[delin["FIPS State Code"] == "51"].assign(
    nm=lambda d: d["County/County Equivalent"].str.replace(" County", "", regex=False)).set_index("nm")["csa"]
m = B.fips.str.startswith("519")
B.loc[m, "csa"] = B.loc[m, "GeoName"].str.split(r" \+|,", regex=True).str[0].str.strip().map(va)
# Connecticut: BEA lists both legacy counties and planning regions; only the latter are in fips2csa.

G = B[B.csa.isin(top)].groupby("csa")[["gdp_k", "pi_k", "bea_pop", "netearn_k", "dir_k", "transfers_k", "wages_pow_k"]].sum()
US = B[["gdp_k", "pi_k", "bea_pop", "netearn_k", "dir_k", "transfers_k", "wages_pow_k"]].sum()
for T in (G, US):
    T["gdp_pc"] = T.gdp_k / T.bea_pop
    T["pi_pc"] = T.pi_k / T.bea_pop
    T["netearn_pc"] = T.netearn_k / T.bea_pop
    T["transfers_pc"] = T.transfers_k / T.bea_pop

# ---------------------------------------------------------------- ACS PUMS
t2p = pd.read_csv(os.path.join(D, "2020_Census_Tract_to_2020_PUMA.txt"), dtype=str, encoding="utf-8-sig")
t2p["fips"] = t2p.STATEFP + t2p.COUNTYFP
t2p["csa"] = t2p.fips.map(fips2csa)
# The tract file predates Connecticut's planning regions: Fairfield County ~= the NY-CSA part of CT.
t2p.loc[t2p.fips == "09001", "csa"] = delin[delin.csa == NYC].csa.iloc[0]
t2p["csa"] = t2p.csa.fillna("_none")
t2p["puma"] = t2p.STATEFP + t2p.PUMA5CE
share = t2p.groupby(["puma", "csa"]).size().rename("n").reset_index()
puma2csa = share.sort_values("n").groupby("puma").tail(1).set_index("puma")["csa"]  # majority of tracts
puma2cty = t2p.groupby("puma").fips.agg(lambda s: s.value_counts().index[0])

cols = ["SERIALNO", "STATE", "PUMA", "PWGTP", "AGEP", "SEX", "FER", "RAC1P", "HISP", "NATIVITY", "SCHL",
        "LANP", "ESR", "PINCP", "PERNP", "WKHP", "MAR", "POVPIP", "ADJINC"]
cache = os.path.join(OUT, "pums_slim.pkl")
if os.path.exists(cache):
    P = pd.read_pickle(cache)
else:
    P = pd.concat([pd.read_csv(f, usecols=cols, dtype={"SERIALNO": str, "STATE": str, "PUMA": str})
                   for f in sorted(glob.glob(os.path.join(D, "pums", "psam_pus*.csv")))], ignore_index=True)
    P.to_pickle(cache)
P["puma"] = P.STATE.str.zfill(2) + P.PUMA.str.zfill(5)
P["csa"] = P.puma.map(puma2csa)
P["cty"] = P.puma.map(puma2cty)
adj = P.ADJINC / 1e6
P["inc"] = P.PINCP.fillna(0) * adj
P["earn"] = P.PERNP.fillna(0) * adj
P["emp"] = P.ESR.isin([1, 2, 4, 5])
P["ba"] = P.SCHL >= 21
P["fb"] = P.NATIVITY == 2
P["race"] = np.select(
    [P.HISP > 1, P.RAC1P == 1, P.RAC1P == 2, P.RAC1P == 6], ["Hispanic", "White NH", "Black NH", "Asian NH"], "Other NH")
# Haredi proxy: anyone in the household speaks Yiddish at home (misses English-speaking "yeshivish" Haredim).
yid = P.loc[P.LANP == 1130, "SERIALNO"].unique()
P["yid_hh"] = P.SERIALNO.isin(yid)
P["births"] = (P.FER == 1) * P.PWGTP
P["ag5"] = (P.AGEP // 5) * 5


def tfr(d):
    """Synthetic TFR from ACS 'birth in past 12 months', women 15-49."""
    d = d[(d.SEX == 2) & d.AGEP.between(15, 49)]
    g = d.groupby("ag5")[["births", "PWGTP"]].sum()
    return 5 * (g.births / g.PWGTP).sum()


def tfr_se(d, reps=60, seed=0):
    """Rough SE via household bootstrap (ignores ACS design; good enough for a sanity band)."""
    d = d[(d.SEX == 2) & d.AGEP.between(15, 49)]
    hh = d.SERIALNO.unique()
    idx = d.groupby("SERIALNO").indices
    rng = np.random.default_rng(seed)
    b, wt, ag = d.births.values, d.PWGTP.values, d.ag5.values
    counts = pd.Series(1, index=d.SERIALNO.values).groupby(level=0).size()
    out = []
    pos = pd.Series(np.arange(len(hh)), index=hh)
    hpos = pos.loc[d.SERIALNO.values].values
    for _ in range(reps):
        mult = rng.poisson(1, len(hh))[hpos]
        num = np.bincount(ag, b * mult, 50)
        den = np.bincount(ag, wt * mult, 50)
        out.append(5 * np.nansum(num[15:50:5] / den[15:50:5]))
    return np.std(out)


def prof(d):
    a = d[d.AGEP.between(25, 54)]
    f = d[(d.SEX == 2) & d.AGEP.between(15, 49)]
    wk = d[d.emp]
    wsum = lambda x, c: (x[c] * x.PWGTP).sum()
    return pd.Series({
        "tfr_acs": tfr(d),
        "tfr_ex_yid": tfr(d[~d.yid_hh]),
        "tfr_ba": tfr(d[d.ba]),
        "tfr_noba": tfr(d[~d.ba]),
        "tfr_fb": tfr(d[d.fb]),
        "tfr_native": tfr(d[~d.fb]),
        "tfr_whiteNH": tfr(d[d.race == "White NH"]),
        "tfr_whiteNH_ex_yid": tfr(d[(d.race == "White NH") & ~d.yid_hh]),
        "tfr_hisp": tfr(d[d.race == "Hispanic"]),
        "tfr_black": tfr(d[d.race == "Black NH"]),
        "tfr_asian": tfr(d[d.race == "Asian NH"]),
        "pct_yid_hh": 100 * wsum(d, "yid_hh") / d.PWGTP.sum(),
        "pct_births_yid": 100 * f[f.yid_hh].births.sum() / f.births.sum(),
        "pct_fb_w1549": 100 * wsum(f, "fb") / f.PWGTP.sum(),
        "pct_ba_w2544": 100 * wsum(f[f.AGEP.between(25, 44)], "ba") / f[f.AGEP.between(25, 44)].PWGTP.sum(),
        "pct_ba_25p": 100 * wsum(d[d.AGEP >= 25], "ba") / d[d.AGEP >= 25].PWGTP.sum(),
        "epop_2554": 100 * wsum(a, "emp") / a.PWGTP.sum(),
        "emp_per_cap": wsum(d, "emp") / d.PWGTP.sum(),
        "pct_2564": 100 * d[d.AGEP.between(25, 64)].PWGTP.sum() / d.PWGTP.sum(),
        "inc_pc": wsum(d, "inc") / d.PWGTP.sum(),
        "inc_pc_ex_yid": wsum(d[~d.yid_hh], "inc") / d[~d.yid_hh].PWGTP.sum(),
        "earn_per_worker": wsum(wk, "earn") / wk.PWGTP.sum(),
        "pct_pov": 100 * d[d.POVPIP < 100].PWGTP.sum() / d[d.POVPIP.notna()].PWGTP.sum(),
        "acs_pop": d.PWGTP.sum(),
        "resident_workers": wsum(d, "emp"),
    })


A = P[P.csa.isin(top)].groupby("csa").apply(prof, include_groups=False)
us_a = prof(P)
se = P[P.csa.isin(top)].groupby("csa").apply(tfr_se, include_groups=False).rename("tfr_acs_se")

# ---------------------------------------------------------------- assemble
R = F.join(G).join(A).join(se)
R["gdp_per_res_worker"] = 1000 * R.gdp_k / R.resident_workers
R = R.sort_values("gdp_pc", ascending=False)
US["gdp_per_res_worker"] = 1000 * US.gdp_k / us_a.resident_workers

print("\n=== 1. Headline: 15 largest CSAs, sorted by GDP per capita (2024) ===")
h = R[["pop_m", "gdp_pc", "pi_pc", "gfr", "tfr_std", "tfr_acs", "tfr_acs_se", "pct_u18"]].copy()
h.loc["UNITED STATES"] = [us_f.pop_m, US.gdp_pc, US.pi_pc, us_f.gfr, us_f.tfr_std, us_a.tfr_acs, np.nan, us_f.pct_u18]
print(h.round({"pop_m": 1, "gdp_pc": 1, "pi_pc": 1, "gfr": 1, "tfr_std": 2, "tfr_acs": 2, "tfr_acs_se": 2, "pct_u18": 1}))
for c in ["tfr_std", "gfr", "tfr_acs"]:
    print(f"corr(gdp_pc, {c}) across {NTOP} CSAs: {np.corrcoef(R.gdp_pc, R[c])[0, 1]:+.2f}   "
          f"NYC rank in {c}: {int(R[c].rank(ascending=False)[NYC])}/{NTOP}; in gdp_pc: {int(R.gdp_pc.rank(ascending=False)[NYC])}/{NTOP}")

print("\n=== 2. Why is NYC's GDP per capita lower? GDP/cap = GDP/worker x workers/cap ===")
d = R[["gdp_pc", "gdp_per_res_worker", "emp_per_cap", "epop_2554", "pct_2564", "pct_u18", "pct_65p",
       "earn_per_worker", "pct_ba_25p", "netearn_pc", "transfers_pc", "pct_pov"]].copy()
print(d.round({"gdp_pc": 1, "gdp_per_res_worker": 1, "emp_per_cap": 3, "epop_2554": 1, "pct_2564": 1, "pct_u18": 1,
               "pct_65p": 1, "earn_per_worker": 0, "pct_ba_25p": 1, "netearn_pc": 1, "transfers_pc": 1, "pct_pov": 1}))
rich = [c for c in R.index[:6] if c != NYC]
print("\nNYC vs. each richer CSA: log-gap in GDP/cap split into productivity vs. employment-rate pieces")
for c in R.index:
    if R.gdp_pc[c] > R.gdp_pc[NYC]:
        tot = np.log(R.gdp_pc[c] / R.gdp_pc[NYC])
        pw = np.log(R.gdp_per_res_worker[c] / R.gdp_per_res_worker[NYC])
        # workers/cap = (workers / pop 25-64-ish adults) is messy; just use kids share for the age piece
        kid = np.log((1 - R.pct_u18[c] / 100) / (1 - R.pct_u18[NYC] / 100))
        print(f"  {c:15s} total {tot:+.3f} = GDP/worker {pw:+.3f} + workers/capita {tot - pw:+.3f}"
              f"   (of which under-18 share alone: {kid:+.3f})")
print("\nNYC GDP/cap if it had each richer CSA's under-18 share (workers per adult unchanged):")
for c in R.index:
    if R.gdp_pc[c] > R.gdp_pc[NYC]:
        cf = R.gdp_pc[NYC] * (1 - R.pct_u18[c] / 100) / (1 - R.pct_u18[NYC] / 100)
        print(f"  {c:15s} {R.gdp_pc[NYC]:.1f}k -> {cf:.1f}k  (vs. {c} actual {R.gdp_pc[c]:.1f}k)")

print("\n=== 3. Who is having NYC's babies? ACS synthetic TFR by group ===")
g = R[["tfr_acs", "tfr_ex_yid", "pct_yid_hh", "pct_births_yid", "tfr_ba", "tfr_noba", "tfr_native", "tfr_fb",
       "tfr_whiteNH", "tfr_whiteNH_ex_yid", "tfr_hisp", "tfr_black", "tfr_asian", "pct_ba_w2544", "pct_fb_w1549"]].copy()
g.loc["UNITED STATES"] = us_a[g.columns]
print(g.round(2))
print("\nIncome per capita (ACS) with / without Yiddish-speaking households, NYC: "
      f"{R.inc_pc[NYC]:,.0f} -> {R.inc_pc_ex_yid[NYC]:,.0f} ({100 * (R.inc_pc_ex_yid[NYC] / R.inc_pc[NYC] - 1):+.2f}%)")

print("\n=== 4. NYC CSA by county: births, standardized TFR, GDP per capita ===")
ny = co[co.csa == NYC].copy()
ny["tfr_std"] = [fert(ny[ny.fips == f]).tfr_std for f in ny.fips]
ny = ny.merge(B[["fips", "gdp_k", "bea_pop", "pi_k"]], on="fips", how="left")
ny["gdp_pc"] = ny.gdp_k / ny.bea_pop
ny["pi_pc"] = ny.pi_k / ny.bea_pop
ny["sh_births"] = 100 * ny.BIRTHS2024 / ny.BIRTHS2024.sum()
print(ny.sort_values("tfr_std", ascending=False)[["STNAME", "CTYNAME", "POPESTIMATE2024", "BIRTHS2024", "sh_births", "tfr_std", "gdp_pc", "pi_pc"]]
      .round({"sh_births": 1, "tfr_std": 2, "gdp_pc": 1, "pi_pc": 1}).to_string(index=False))
HAREDI = ["36087", "36071", "34029"]  # Rockland (Monsey), Orange (Kiryas Joel), Ocean (Lakewood)
for label, drop in [("ex Rockland/Orange/Ocean", HAREDI), ("ex those + Brooklyn", HAREDI + ["36047"])]:
    s = ny[~ny.fips.isin(drop)]
    print(f"NYC CSA {label:28s}: TFR {fert(s).tfr_std:.2f}, GDP/cap {s.gdp_k.sum() / s.bea_pop.sum():.1f}k "
          f"(full CSA: {fert(ny).tfr_std:.2f}, {ny.gdp_k.sum() / ny.bea_pop.sum():.1f}k)")

print("\n=== 5. Composition test: NYC TFR if each group kept its own NYC fertility but the CSA had another CSA's mix,")
print("       and vice versa (cells: race/ethnicity x BA x foreign-born x Yiddish-HH; ACS, women 15-49) ===")
W = P[(P.SEX == 2) & P.AGEP.between(15, 49) & P.csa.isin(top)].copy()
W["cell"] = W.race + "|" + W.ba.astype(str) + "|" + W.fb.astype(str) + "|" + W.yid_hh.astype(str)
cellrate = W.groupby(["csa", "cell", "ag5"])[["births", "PWGTP"]].sum()
cellrate["r"] = cellrate.births / cellrate.PWGTP
nyr = cellrate.loc[NYC]


def mix_tfr(rates, weights):
    """TFR using `rates` (cell x age) and `weights` (cell x age women) -- cells missing in rates are dropped."""
    j = weights.to_frame("w").join(rates.r, how="inner")
    a = j.assign(b=j.w * j.r).groupby("ag5")[["b", "w"]].sum()
    return 5 * (a.b / a.w).sum()


rows = []
for c in R.index:
    cr = cellrate.loc[c]
    rows.append({"csa": c, "own_tfr": R.tfr_acs[c],
                 "nyc_rates_x_own_mix": mix_tfr(nyr, cr.PWGTP),
                 "own_rates_x_nyc_mix": mix_tfr(cr, nyr.PWGTP)})
print(pd.DataFrame(rows).set_index("csa").round(2))

print("\n=== 6. Strip the Haredi-heavy population out of BOTH measures (NYC CSA) ===")
N = P[P.csa == NYC]
masks = {
    "full CSA": np.ones(len(N), bool),
    "ex Yiddish-speaking households": ~N.yid_hh.values,
    "ex Rockland/Orange/Ocean": ~N.cty.isin(HAREDI).values,
    "ex both": (~N.yid_hh & ~N.cty.isin(HAREDI)).values,
}
for k, mk in masks.items():
    s = N[mk]
    a = s[s.AGEP.between(25, 54)]
    print(f"  {k:32s} pop share {100 * s.PWGTP.sum() / N.PWGTP.sum():5.1f}%  ACS TFR {tfr(s):.2f}  "
          f"ACS income/cap {(s.inc * s.PWGTP).sum() / s.PWGTP.sum():,.0f}  "
          f"E/pop 25-54 {100 * (a.emp * a.PWGTP).sum() / a.PWGTP.sum():.1f}  "
          f"under-18 {100 * s[s.AGEP < 18].PWGTP.sum() / s.PWGTP.sum():.1f}%")
s = ny[~ny.fips.isin(HAREDI)]
print(f"  BEA personal income/cap: full {ny.pi_k.sum() / ny.bea_pop.sum():.1f}k -> ex 3 counties {s.pi_k.sum() / s.bea_pop.sum():.1f}k")

R.to_csv(os.path.join(OUT, "csa_fertility_gdp.csv"))
print("\nwrote", os.path.join(OUT, "csa_fertility_gdp.csv"))
