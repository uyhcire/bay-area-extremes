#!/usr/bin/env python3
"""Regional (between-metro-region) nominal income inequality by state.

Inputs (downloaded to data/raw/regional_inequality/ if missing):
  bea/CAINC1__ALL_AREAS_1969_2024.csv   BEA CAINC1 bulk zip (key-free)
  list1_2023.xlsx                       OMB/Census CBSA/CSA delineation, July 2023
  CenPop2020_Mean_CO.txt                Census 2020 county centers of population
  CenPop2020_Mean_TR09.txt              Census 2020 CT tract centers of population
  2023_gaz_tracts_09.txt                CT tracts on planning-region GEOIDs
  cz2020.csv                            USDA ERS 2020 commuting zones

Usage: python3 regional_inequality.py [RAW_DIR] [OUT_DIR]
"""
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "data/raw/regional_inequality")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "out")
YEAR = "2024"
H_MAIN = 0.20          # Gaussian kernel bandwidth in ln(km)
BIN = 0.005            # pre-binning width in ln(km)
R_EARTH = 6371.0088

URLS = {
    "CAINC1.zip": "https://apps.bea.gov/regional/zip/CAINC1.zip",
    "list1_2023.xlsx": "https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx",
    "CenPop2020_Mean_CO.txt": "https://www2.census.gov/geo/docs/reference/cenpop2020/county/CenPop2020_Mean_CO.txt",
    "CenPop2020_Mean_TR09.txt": "https://www2.census.gov/geo/docs/reference/cenpop2020/tract/CenPop2020_Mean_TR09.txt",
    "2023_gaz_tracts_09.txt": "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_gaz_tracts_09.txt",
    "cz2020.csv": "https://www.ers.usda.gov/media/6968/2020-commuting-zones.csv",
}

# BEA combination areas -> component Census county FIPS
COMBOS = {
    "15901": ["15009", "15005"],
    "51901": ["51003", "51540"], "51903": ["51005", "51580"],
    "51907": ["51015", "51790", "51820"], "51911": ["51031", "51680"],
    "51913": ["51035", "51640"], "51918": ["51053", "51570", "51730"],
    "51919": ["51059", "51600", "51610"], "51921": ["51069", "51840"],
    "51923": ["51081", "51595"], "51929": ["51089", "51690"],
    "51931": ["51095", "51830"], "51933": ["51121", "51750"],
    "51939": ["51143", "51590"], "51941": ["51149", "51670"],
    "51942": ["51153", "51683", "51685"], "51944": ["51161", "51775"],
    "51945": ["51163", "51530", "51678"], "51947": ["51165", "51660"],
    "51949": ["51175", "51620"], "51951": ["51177", "51630"],
    "51953": ["51191", "51520"], "51955": ["51195", "51720"],
    "51958": ["51199", "51735"],
}
COMP2COMBO = {c: k for k, v in COMBOS.items() for c in v}


def fetch():
    os.makedirs(RAW, exist_ok=True)
    for name, url in URLS.items():
        p = os.path.join(RAW, name)
        if not os.path.exists(p):
            subprocess.run(["curl", "-sSL", "--retry", "4", "-o", p, url], check=True)
    if not os.path.isdir(os.path.join(RAW, "bea")):
        subprocess.run(["unzip", "-o", "-q", os.path.join(RAW, "CAINC1.zip"), "-d", os.path.join(RAW, "bea")], check=True)


def load_bea():
    b = pd.read_csv(os.path.join(RAW, "bea", f"CAINC1__ALL_AREAS_1969_{YEAR}.csv"), encoding="latin-1", dtype=str)
    b = b[b.LineCode.notna()].copy()
    b["fips"] = b.GeoFIPS.str.replace('"', "").str.strip()
    b["line"] = b.LineCode.str.strip()
    b["name"] = b.GeoName.str.replace("*", "", regex=False).str.strip()
    w = b[b.line.isin(["1", "2"])].pivot(index="fips", columns="line", values=YEAR)
    w.columns = ["inc", "pop"]
    w["name"] = b.drop_duplicates("fips").set_index("fips").name
    w = w.reset_index()
    na = w[w.inc.str.contains(r"\(") | w["pop"].str.contains(r"\(")]
    w = w[~w.fips.isin(na.fips)].copy()
    w["inc"] = w.inc.astype(float) * 1000.0
    w["pop"] = w["pop"].astype(float)
    us = w[w.fips == "00000"].iloc[0]
    states = w[w.fips.str.endswith("000") & (w.fips > "00000") & (w.fips < "57000")].copy()
    cty = w[~w.fips.str.endswith("000") & (w.fips < "57000")].copy()
    cty["st"] = cty.fips.str[:2]
    return cty.reset_index(drop=True), states, us, na


def load_centers(cty):
    cp = pd.read_csv(os.path.join(RAW, "CenPop2020_Mean_CO.txt"), dtype=str, encoding="utf-8-sig")
    cp["fips"] = cp.STATEFP + cp.COUNTYFP
    for c in ("POPULATION", "LATITUDE", "LONGITUDE"):
        cp[c] = cp[c].astype(float)
    cp = cp[["fips", "POPULATION", "LATITUDE", "LONGITUDE"]]
    # CT: rebuild planning-region centers from 2020 tract centers of population
    t = pd.read_csv(os.path.join(RAW, "CenPop2020_Mean_TR09.txt"), dtype=str, encoding="utf-8-sig")
    for c in ("POPULATION", "LATITUDE", "LONGITUDE"):
        t[c] = t[c].astype(float)
    g = pd.read_csv(os.path.join(RAW, "2023_gaz_tracts_09.txt"), sep="\t", dtype=str)
    g.columns = [c.strip() for c in g.columns]
    g["tr"] = g.GEOID.str[5:]
    g["la"] = g.INTPTLAT.astype(float)
    g["lo"] = g.INTPTLONG.astype(float)
    pr, unmatched = [], 0
    for r in t.itertuples():
        m = g[g.tr == r.TRACTCE]
        if len(m) == 0:
            unmatched += 1
            m = g
        j = ((m.la - r.LATITUDE) ** 2 + (m.lo - r.LONGITUDE) ** 2).idxmin()
        pr.append(g.GEOID[j][:5])
    t["fips"] = pr
    ct = wmean_centers(t)
    cp = cp[~cp.fips.str.startswith("09")]
    # BEA combination areas: population-weighted mean of component centers
    cp["fips"] = cp.fips.map(lambda f: COMP2COMBO.get(f, f))
    cp = pd.concat([wmean_centers(cp), ct])
    out = cty.merge(cp, on="fips", how="left")
    return out, unmatched


def wmean_centers(df):
    df = df.assign(wl=df.LATITUDE * df.POPULATION, wo=df.LONGITUDE * df.POPULATION)
    a = df.groupby("fips")[["POPULATION", "wl", "wo"]].sum()
    return pd.DataFrame({"fips": a.index, "pop2020": a.POPULATION.values,
                         "lat": (a.wl / a.POPULATION).values, "lon": (a.wo / a.POPULATION).values})


def load_regions(cty):
    d = pd.read_excel(os.path.join(RAW, "list1_2023.xlsx"), header=2, dtype=str).dropna(subset=["FIPS State Code"])
    d["fips"] = (d["FIPS State Code"] + d["FIPS County Code"]).map(lambda f: COMP2COMBO.get(f, f))
    d["metro"] = d["Metropolitan/Micropolitan Statistical Area"].str.startswith("Metropolitan")
    d = d.rename(columns={"CBSA Code": "cbsa", "CSA Code": "csa", "CBSA Title": "cbsa_title", "CSA Title": "csa_title"})
    d = d[["fips", "cbsa", "csa", "cbsa_title", "csa_title", "metro"]].drop_duplicates()
    conflicts = d[d.fips.duplicated(keep=False)]
    d = d.drop_duplicates("fips")
    cz = pd.read_csv(os.path.join(RAW, "cz2020.csv"), dtype=str, encoding="latin-1")
    cz["fips"] = cz.FIPStxt.str.zfill(5).map(lambda f: COMP2COMBO.get(f, f))
    cz = cz[["fips", "CZ2020", "CZName"]].drop_duplicates()
    cz_conf = cz[cz.fips.duplicated(keep=False)]
    cz = cz.drop_duplicates("fips")
    c = cty.merge(d, on="fips", how="left").merge(cz, on="fips", how="left")
    stname = c.st.map(STNAME)
    rem_id, rem_nm = "REM" + c.st, stname + " nonmetro remainder"
    has_csa = c.csa.notna()
    is_metro = c.metro.fillna(False).astype(bool)
    c["reg_csa"] = np.where(has_csa, "CSA" + c.csa.fillna(""), np.where(is_metro, "MSA" + c.cbsa.fillna(""), rem_id))
    c["reg_csa_name"] = np.where(has_csa, c.csa_title, np.where(is_metro, c.cbsa_title, rem_nm))
    c["reg_msa"] = np.where(is_metro, "MSA" + c.cbsa.fillna(""), rem_id)
    c["reg_msa_name"] = np.where(is_metro, c.cbsa_title, rem_nm)
    c["reg_cz"] = "CZ" + c.CZ2020
    c["reg_cz_name"] = c.CZName
    return c, conflicts, cz_conf, set(d.fips) - set(cty.fips)


def haversine_matrix(lat, lon):
    la, lo = np.radians(lat)[:, None], np.radians(lon)[:, None]
    a = np.sin((la - la.T) / 2) ** 2 + np.cos(la) * np.cos(la.T) * np.sin((lo - lo.T) / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def region_y(c, col):
    a = c.groupby(col)[["inc", "pop"]].sum()
    return np.log(c[col].map(a.inc / a["pop"]).values)


class GCurve:
    """Population-product-weighted local linear regression of gap on ln(d),
    computed from fine pre-binned sufficient statistics (bin width BIN)."""

    def __init__(self, lnd, gap, w):
        self.lo = np.floor(lnd.min() / BIN) * BIN
        k = np.floor((lnd - self.lo) / BIN).astype(int)
        n = k.max() + 1
        self.x = self.lo + (np.arange(n) + 0.5) * BIN
        bc = lambda v: np.bincount(k, weights=v, minlength=n)
        self.W, self.WX, self.WXX = bc(w), bc(w * lnd), bc(w * lnd * lnd)
        self.WY, self.WXY = bc(w * gap), bc(w * lnd * gap)

    def fit(self, h, grid=None):
        grid = self.x if grid is None else grid
        out = np.empty(len(grid))
        for i, x0 in enumerate(grid):
            K = np.exp(-0.5 * ((self.x - x0) / h) ** 2)
            s0 = (K * self.W).sum()
            s1 = (K * (self.WX - x0 * self.W)).sum()
            s2 = (K * (self.WXX - 2 * x0 * self.WX + x0 * x0 * self.W)).sum()
            t0 = (K * self.WY).sum()
            t1 = (K * (self.WXY - x0 * self.WY)).sum()
            out[i] = (s2 * t0 - s1 * t1) / (s0 * s2 - s1 * s1)
        return out


def analyse(c, dist, col, power=1, hs=(H_MAIN,)):
    """Returns per-state stats (plus US row) for region column `col`."""
    y = region_y(c, col)
    pop = c["pop"].values
    gap = np.abs(y[:, None] - y[None, :]) ** power
    iu = np.triu_indices(len(c), 1)
    lnd = np.log(dist[iu])
    curve = GCurve(lnd, gap[iu], (pop[:, None] * pop[None, :])[iu])
    ghat = {h: curve.fit(h) for h in hs}
    neg = {h: float(ghat[h].min()) for h in hs}
    rows = []
    groups = [(s, np.where(c.st.values == s)[0]) for s in sorted(c.st.unique())] + [("US", np.arange(len(c)))]
    for s, idx in groups:
        p = pop[idx] / pop[idx].sum()
        pp = p[:, None] * p[None, :]
        D = (pp * gap[np.ix_(idx, idx)]).sum()
        ybar = (p * y[idx]).sum()
        sd = np.sqrt((p * (y[idx] - ybar) ** 2).sum())
        wr = pd.Series(p).groupby(c[col].values[idx]).sum()
        row = dict(st=s, D=D, SD=sd, N=1 / (wr ** 2).sum(), n_regions=len(wr), n_counties=len(idx))
        dd = dist[np.ix_(idx, idx)]
        off = ~np.eye(len(idx), dtype=bool)
        for h in hs:
            gv = np.interp(np.log(dd[off]), curve.x, np.maximum(ghat[h], 0))
            row[f"E_h{h}"] = (pp[off] * gv).sum()
        rows.append(row)
    r = pd.DataFrame(rows)
    r["E"] = r[f"E_h{hs[0]}"]
    r["ratio"] = r.D / r.E
    r["diff"] = r.D - r.E
    return r, curve, ghat, neg, y


def add_ranks(r):
    m = (r.st != "US") & (r.st != "11")
    r.loc[m, "rank_D"] = r.loc[m, "D"].rank(ascending=False, method="min")
    r.loc[m, "rank_ratio"] = r.loc[m, "ratio"].rank(ascending=False, method="min")
    return r


def spearman(a, b):
    return float(np.corrcoef(pd.Series(a).rank(), pd.Series(b).rank())[0, 1])


STNAME = {"01": "Alabama", "02": "Alaska", "04": "Arizona", "05": "Arkansas", "06": "California", "08": "Colorado",
          "09": "Connecticut", "10": "Delaware", "11": "District of Columbia", "12": "Florida", "13": "Georgia",
          "15": "Hawaii", "16": "Idaho", "17": "Illinois", "18": "Indiana", "19": "Iowa", "20": "Kansas",
          "21": "Kentucky", "22": "Louisiana", "23": "Maine", "24": "Maryland", "25": "Massachusetts",
          "26": "Michigan", "27": "Minnesota", "28": "Mississippi", "29": "Missouri", "30": "Montana",
          "31": "Nebraska", "32": "Nevada", "33": "New Hampshire", "34": "New Jersey", "35": "New Mexico",
          "36": "New York", "37": "North Carolina", "38": "North Dakota", "39": "Ohio", "40": "Oklahoma",
          "41": "Oregon", "42": "Pennsylvania", "44": "Rhode Island", "45": "South Carolina", "46": "South Dakota",
          "47": "Tennessee", "48": "Texas", "49": "Utah", "50": "Vermont", "51": "Virginia", "53": "Washington",
          "54": "West Virginia", "55": "Wisconsin", "56": "Wyoming", "US": "United States"}


def main():
    fetch()
    os.makedirs(OUT, exist_ok=True)
    log = []
    P = lambda *a: (print(*a), log.append(" ".join(str(x) for x in a)))

    cty, states, us, na = load_bea()
    P(f"YEAR {YEAR}. BEA county units with data: {len(cty)}; rows with (NA) in {YEAR} dropped as defunct codes: {len(na)}")
    cty, unmatched = load_centers(cty)
    P(f"CT tracts not matched by tract code (assigned to nearest tract): {unmatched}")
    P("counties lacking a center of population:", list(cty[cty.lat.isna()].fips))
    c, conflicts, cz_conf, delin_extra = load_regions(cty)
    P("delineation rows not in BEA county list (PR etc. expected):", sorted(f for f in delin_extra if f < "57000"))
    P("combination areas whose components fall in different CBSA/CSA:", sorted(set(conflicts.fips)))
    P("combination areas whose components fall in different CZs:", sorted(set(cz_conf.fips)))
    P("counties without CZ:", list(c[c.reg_cz.isna()].fips))

    # checks: state totals
    s = c.groupby("st")[["inc", "pop"]].sum().join(states.assign(st=states.fips.str[:2]).set_index("st")[["inc", "pop"]], rsuffix="_bea")
    s["inc_dev"] = s.inc / s.inc_bea - 1
    s["pop_dev"] = s["pop"] / s.pop_bea - 1
    P(f"max |state income dev| {s.inc_dev.abs().max():.2e}; max |state pop dev| {s.pop_dev.abs().max():.2e}")
    P(f"US: county-sum income / BEA US = {c.inc.sum() / us.inc:.6f}; pop = {c['pop'].sum() / us['pop']:.6f}")
    s.to_csv(os.path.join(OUT, "check_state_totals.csv"))
    P("counties with exactly one region (csa/msa/cz):", int(c.reg_csa.notna().sum()), int(c.reg_msa.notna().sum()), int(c.reg_cz.notna().sum()), "of", len(c))
    P("number of regions (csa-based / msa-based / cz):", c.reg_csa.nunique(), c.reg_msa.nunique(), c.reg_cz.nunique())

    dist = haversine_matrix(c.lat.values, c.lon.values)
    iu = np.triu_indices(len(c), 1)
    P(f"pairs of distinct counties: {len(iu[0])}; min distance {dist[iu].min():.2f} km; max {dist[iu].max():.0f} km")

    hs = (H_MAIN, 0.10, 0.40)
    main_r, curve, ghat, neg, y = analyse(c, dist, "reg_csa", 1, hs)
    main_r = add_ranks(main_r)
    P("min of fitted g by bandwidth (negative values clipped to 0):", neg)
    c["y"] = y
    c.to_csv(os.path.join(OUT, "county_assignments.csv"), index=False)

    # region table
    reg = c.groupby(["reg_csa", "reg_csa_name"])[["inc", "pop"]].sum().reset_index()
    reg["pcpi"] = reg.inc / reg["pop"]
    reg.to_csv(os.path.join(OUT, "regions.csv"), index=False)

    main_r.insert(1, "state", main_r.st.map(STNAME))
    main_r.to_csv(os.path.join(OUT, "state_table.csv"), index=False)
    single = main_r[main_r.n_regions == 1]
    P("single-region states and their D:", [(r.state, r.D) for r in single.itertuples()])

    # region-pair contributions
    def state_regions(st):
        k = c[c.st == st]
        a = k.groupby(["reg_csa", "reg_csa_name"]).agg(pop=("pop", "sum"), y=("y", "first")).reset_index()
        a["share"] = a["pop"] / a["pop"].sum()
        a["pcpi"] = np.exp(a.y)
        return a

    top10 = main_r[main_r.rank_D <= 10].sort_values("rank_D")
    rows = []
    for r in top10.itertuples():
        a = state_regions(r.st)
        contrib = 2 * np.abs(a.y.values[:, None] - a.y.values[None, :]) * a.share.values[:, None] * a.share.values[None, :]
        i, j = np.unravel_index(np.argmax(np.triu(contrib, 1)), contrib.shape)
        rows.append(dict(state=r.state, rank_D=int(r.rank_D), D=r.D, region_a=a.reg_csa_name[i], pcpi_a=a.pcpi[i], share_a=a.share[i],
                         region_b=a.reg_csa_name[j], pcpi_b=a.pcpi[j], share_b=a.share[j], pair_contrib=contrib[i, j], pct_of_D=contrib[i, j] / r.D))
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "top10_pairs.csv"), index=False)

    a = state_regions("06")
    a["contrib"] = (np.abs(a.y.values[:, None] - a.y.values[None, :]) * a.share.values[:, None] * a.share.values[None, :]).sum(1)
    a["pct_of_D"] = a.contrib / a.contrib.sum()
    a.sort_values("share", ascending=False).drop(columns=["y"]).to_csv(os.path.join(OUT, "california_regions.csv"), index=False)
    P(f"CA contributions sum {a.contrib.sum():.6f} vs D {main_r[main_r.st == '06'].D.iloc[0]:.6f}")

    # robustness
    m50 = lambda r: r[(r.st != "US") & (r.st != "11")].set_index("st")
    base = m50(main_r)
    rob = []

    def record(label, r):
        r = add_ranks(r)
        r.insert(1, "state", r.st.map(STNAME))
        r.to_csv(os.path.join(OUT, f"robust_{label}.csv"), index=False)
        k = m50(r)
        u = r[r.st == "US"].iloc[0]
        rob.append(dict(variant=label, spearman_D=spearman(base.D, k.D.reindex(base.index)),
                        spearman_ratio=spearman(base.ratio, k.ratio.reindex(base.index)),
                        CA_rank_D=int(k.rank_D["06"]), CA_rank_ratio=int(k.rank_ratio["06"]),
                        CA_D=k.D["06"], US_D=u.D, CA_ratio=k.ratio["06"],
                        top_D=STNAME[k.D.idxmax()], top_ratio=STNAME[k.ratio.idxmax()]))

    record("main_csa", main_r.drop(columns=["state"]).copy())
    record("a_msa", analyse(c, dist, "reg_msa", 1)[0])
    record("b_cz", analyse(c, dist, "reg_cz", 1)[0])
    record("c_squared", analyse(c, dist, "reg_csa", 2)[0])
    for h in hs[1:]:
        r = main_r.drop(columns=["state", "rank_D", "rank_ratio"]).copy()
        r["E"] = r[f"E_h{h}"]
        r["ratio"] = r.D / r.E
        r["diff"] = r.D - r.E
        record(f"bandwidth_{h}", r)
    pd.DataFrame(rob).to_csv(os.path.join(OUT, "robustness.csv"), index=False)

    pd.DataFrame({"ln_d": curve.x, "d_km": np.exp(curve.x), "pair_weight": curve.W,
                  **{f"g_h{h}": np.maximum(ghat[h], 0) for h in hs}}).to_csv(os.path.join(OUT, "g_curve.csv"), index=False)
    plot(curve, ghat, hs, os.path.join(OUT, "g_curve.png"))
    open(os.path.join(OUT, "run_log.txt"), "w").write("\n".join(log) + "\n")


def plot(curve, ghat, hs, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ink, muted, grid = "#1f2328", "#6b7280", "#e5e7eb"
    fig, ax = plt.subplots(figsize=(8, 4.6), dpi=200)
    # raw binned means on coarse bins for reference
    k = np.floor((curve.x - curve.lo) / 0.1).astype(int)
    W = np.bincount(k, curve.W)
    ok = W > 0
    ax.scatter(np.exp(np.bincount(k, curve.WX)[ok] / W[ok]), np.bincount(k, curve.WY)[ok] / W[ok], s=9, color="#9ca3af",
               label="Raw weighted mean, 0.1-wide ln(d) bins", zorder=2, linewidths=0)
    d = np.exp(curve.x)
    ax.plot(d, np.maximum(ghat[hs[0]], 0), color="#2563eb", lw=2, label=f"Local linear fit, h = {hs[0]:.2f}", zorder=3)
    ax.set_xscale("log")
    ax.set_xlim(3, 9000)
    ax.set_ylim(0, None)
    ax.set_xlabel("Great-circle distance between county centers of population (km, log scale)", color=muted, fontsize=9)
    ax.set_ylabel("Expected |log income gap| between regions", color=muted, fontsize=9)
    ax.set_title("g(d): expected regional log income gap by distance, all US county pairs, 2024\n"
                 "CSA/MSA/nonmetro-remainder regions; pairs weighted by product of populations", loc="left", fontsize=10, color=ink)
    ax.grid(True, color=grid, lw=0.6)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color(grid)
    ax.tick_params(colors=muted, labelsize=8)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(path)


if __name__ == "__main__":
    main()
