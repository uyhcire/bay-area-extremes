#!/usr/bin/env python3
"""Gender per-capita wage-bill ratios under a hybrid matching design (CPS ASEC).

Women are split by education (non-college share s); men in the same
year x age band are split by their own earnings rank into a bottom s share and
a top 1 - s share. The ratio of per-capita wage bills (zeros included) is
compared within each side, decomposed into employment, hours and hourly-wage
terms, benchmarked against an education-only and a within-sex-halves match,
and bootstrapped.

Input:  data/raw/census_cps_asec/cps_asec_harmonized.parquet (build_extract.py)
        data/raw/bls_cpi_u_rs/r-cpi-u-rs-allitems.xlsx       (BLS R-CPI-U-RS)
Output: analysis/gender_wage_ratios/output/

Usage:  python3 analysis/gender_wage_ratios/analysis.py [--reps 200] [--seed 20240]
"""
import argparse
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "output")
EXTRACT = "data/raw/census_cps_asec/cps_asec_harmonized.parquet"
CPI_XLSX = "data/raw/bls_cpi_u_rs/r-cpi-u-rs-allitems.xlsx"

SURVEY_YEARS = [2001, 2010, 2019, 2025]  # earnings years 2000, 2009, 2018, 2024
BASE, LAST = 2000, 2024                   # earnings years compared in Table 2
BANDS = {"25-34": (25, 34), "35-44": (35, 44), "45-54": (45, 54)}
R1_BANDS = {"30-34": (30, 34), "35-44": (35, 44), "45-54": (45, 54)}
POOLED = "25-54 pooled"
DESIGNS = ["main", "B1", "B2"]
SIDES = ["bottom", "top"]
FEMALE, MALE = 2, 1


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
def load(path: str = EXTRACT) -> pd.DataFrame:
    d = pd.read_parquet(path)
    d = d[(d.AGE >= 25) & (d.AGE <= 54)].copy()
    d["INCWAGE"] = d.INCWAGE.where(d.INCWAGE < 99999998, 0).clip(lower=0)
    d["UHRSWORKLY"] = d.UHRSWORKLY.where(d.UHRSWORKLY != 999, 0)
    d["HOURS"] = d.WKSWORK1 * d.UHRSWORKLY
    d["COLLEGE"] = (d.EDUC >= 111).astype(float)
    d["MARRIED"] = d.MARST.isin([1, 2]).astype(float)
    d["EYEAR"] = d.YEAR - 1
    d["BAND"] = pd.cut(d.AGE, [24, 34, 44, 54], labels=list(BANDS)).astype(str)
    return d.reset_index(drop=True)


def cpi_factors(path: str = CPI_XLSX) -> dict:
    """Multiply nominal dollars of earnings year t by f[t] to get 2024 dollars."""
    x = pd.read_excel(path, header=None, skiprows=6)
    x = x[pd.to_numeric(x[0], errors="coerce").notna()]
    avg = dict(zip(x[0].astype(int), x[13].astype(float)))
    return {y - 1: avg[LAST] / avg[y - 1] for y in SURVEY_YEARS}


def winsorize(d: pd.DataFrame, q: float = 0.99) -> pd.DataFrame:
    """R2: cap INCWAGE at the weighted q-th percentile of earners, by year x sex."""
    d = d.copy()
    for _, g in d[d.INCWAGE > 0].groupby(["YEAR", "SEX"]):
        o = np.argsort(g.INCWAGE.to_numpy(), kind="mergesort")
        y, w = g.INCWAGE.to_numpy()[o], g.ASECWT.to_numpy()[o]
        cap = y[np.searchsorted(np.cumsum(w) / w.sum(), q)]
        idx = g.index[g.INCWAGE > cap]
        d.loc[idx, "INCWAGE"] = cap
    return d


# --------------------------------------------------------------------------
# One year x band cell, both sexes sorted by earnings
# --------------------------------------------------------------------------
class Side:
    """Arrays for one sex in one cell, sorted ascending by INCWAGE."""

    def __init__(self, g: pd.DataFrame, rows: np.ndarray):
        o = np.argsort(g.INCWAGE.to_numpy(), kind="mergesort")
        self.rows = rows[o]                       # positions in the year frame
        self.w = g.ASECWT.to_numpy()[o]
        y = g.INCWAGE.to_numpy()[o]
        h = g.HOURS.to_numpy()[o]
        e = (y > 0).astype(float)
        ep = ((y > 0) & (h > 0)).astype(float)
        # Columns of the sufficient statistics matrix (see group_stats).
        self.X = np.column_stack([np.ones_like(y), y, e, ep, h * ep, y * ep,
                                  g.MARRIED.to_numpy()[o]])
        self.college = g.COLLEGE.to_numpy()[o]
        # Contiguous blocks of tied earnings (e.g. all zero earners).
        self.starts = np.flatnonzero(np.r_[True, y[1:] != y[:-1]])
        self.block = np.cumsum(np.r_[True, y[1:] != y[:-1]]) - 1


def rank_split(G: np.ndarray, side: Side, s: np.ndarray) -> np.ndarray:
    """Fraction of each person's weight in the bottom s share of the earnings
    distribution (rows of G are replicate weight vectors). The cutoff block of
    tied earnings is split fractionally and proportionally, so the bottom group
    holds exactly s of the weight."""
    B = np.add.reduceat(G, side.starts, axis=1)
    C = np.cumsum(B, axis=1)
    target = s[:, None] * C[:, -1:]
    f = np.clip((target - (C - B)) / np.where(B > 0, B, 1.0), 0.0, 1.0)
    return f[:, side.block]


def group_stats(Gk: np.ndarray, side: Side) -> dict:
    """Weighted group statistics from replicate weights Gk (R x n)."""
    S0, S1, Se, Sp, Sh, Syp, Sm = (Gk @ side.X).T
    W = S1 / Se
    H = Sh / Sp
    hourly = Syp / Sh
    return {"N": S0, "PC": S1 / S0, "E": Se / S0, "W": W, "H": H,
            "hourly": hourly, "resid": W / (H * hourly), "married": Sm / S0}


def cell_designs(Gf: np.ndarray, Gm: np.ndarray, F: Side, M: Side) -> dict:
    """Group stats for every design x side x sex. Returns {(design, side, sex): stats}."""
    s = (Gf @ (1 - F.college)) / Gf.sum(axis=1)
    half = np.full(len(s), 0.5)
    m_bot = rank_split(Gm, M, s)
    f_half, m_half = rank_split(Gf, F, half), rank_split(Gm, M, half)
    masks = {
        "main": ((1 - F.college, F.college), (m_bot, 1 - m_bot)),
        "B1": ((1 - F.college, F.college), (1 - M.college, M.college)),
        "B2": ((f_half, 1 - f_half), (m_half, 1 - m_half)),
    }
    res = {"s": s}
    for d, ((fb, ft), (mb, mt)) in masks.items():
        for side, fk, mk in (("bottom", fb, mb), ("top", ft, mt)):
            res[(d, side, "f")] = group_stats(Gf * fk, F)
            res[(d, side, "m")] = group_stats(Gm * mk, M)
    return res


def ratios(res: dict, design: str, side: str) -> dict:
    f, m = res[(design, side, "f")], res[(design, side, "m")]
    out = {k: f[k] / m[k] for k in ["PC", "E", "W", "H", "hourly", "resid"]}
    out["R"] = out.pop("PC")
    return out


# --------------------------------------------------------------------------
# Running cells
# --------------------------------------------------------------------------
def build_cells(d: pd.DataFrame, bands: dict, pooled_reweight: bool = False) -> dict:
    """{(year, band): (F, M)} with rows indexing the year's sub-frame."""
    cells = {}
    for year in SURVEY_YEARS:
        yd = d[d.YEAR == year].reset_index(drop=True)
        rows_all = np.arange(len(yd))
        for band, (lo, hi) in bands.items():
            sel = ((yd.AGE >= lo) & (yd.AGE <= hi)).to_numpy()
            sides = []
            for sex in (FEMALE, MALE):
                m = sel & (yd.SEX == sex).to_numpy()
                sides.append(Side(yd[m], rows_all[m]))
            cells[(year, band)] = tuple(sides)
        if pooled_reweight:
            cells[(year, POOLED)] = pooled_cell(d, yd, rows_all)
    return cells


def pooled_cell(d: pd.DataFrame, yd: pd.DataFrame, rows_all: np.ndarray):
    """R3: all 25-54 in one cell, each sex's age-band mix reweighted to its
    earnings-year-2000 shares."""
    base = d[d.YEAR == SURVEY_YEARS[0]]
    sides = []
    for sex in (FEMALE, MALE):
        b = base[base.SEX == sex].groupby("BAND").ASECWT.sum()
        g = yd[yd.SEX == sex].copy()
        c = g.groupby("BAND").ASECWT.sum()
        adj = (b / b.sum()) / (c / c.sum())
        g["ASECWT"] = g.ASECWT * g.BAND.map(adj).astype(float)
        sides.append(Side(g, rows_all[(yd.SEX == sex).to_numpy()]))
    return tuple(sides)


def point(cells: dict) -> dict:
    return {k: cell_designs(F.w[None, :], M.w[None, :], F, M)
            for k, (F, M) in cells.items()}


def bootstrap(d: pd.DataFrame, cells: dict, reps: int, seed: int) -> dict:
    """Resample persons with replacement within each survey year; every
    replicate keeps ASECWT as the analysis weight."""
    rng = np.random.default_rng(seed)
    out = {}
    for year in SURVEY_YEARS:
        n = int((d.YEAR == year).sum())
        counts = np.empty((reps, n), dtype=np.int16)
        for r in range(reps):
            counts[r] = np.bincount(rng.integers(0, n, n), minlength=n)
        for (yr, band), (F, M) in cells.items():
            if yr != year:
                continue
            Gf = counts[:, F.rows] * F.w
            Gm = counts[:, M.rows] * M.w
            out[(yr, band)] = cell_designs(Gf, Gm, F, M)
    return out


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def table1(pt: dict, bs: dict, bands) -> pd.DataFrame:
    rows = []
    for (year, band), res in pt.items():
        if band not in bands:
            continue
        for side in SIDES:
            r = ratios(res, "main", side)
            rb = ratios(bs[(year, band)], "main", side)
            f, m = res[("main", side, "f")], res[("main", side, "m")]
            rows.append({
                "earn_year": year - 1, "band": band, "side": side,
                "s": res["s"][0], "PC_f": f["PC"][0], "PC_m": m["PC"][0],
                "R": r["R"][0], "R_se": rb["R"].std(ddof=1),
                "E_ratio": r["E"][0], "W_ratio": r["W"][0],
                "H_ratio": r["H"][0], "hourly_ratio": r["hourly"][0],
                "resid_ratio": r["resid"][0],
                "E_f": f["E"][0], "E_m": m["E"][0],
            })
    return pd.DataFrame(rows)


def change(res0: dict, res1: dict, design: str, side: str) -> dict:
    a, b = ratios(res0, design, side), ratios(res1, design, side)
    out = {"R0": a["R"], "R1": b["R"], "dR": b["R"] - a["R"],
           "dlnR": 100 * np.log(b["R"] / a["R"])}
    for k in ["E", "H", "hourly", "resid"]:
        out["dln_" + k] = 100 * np.log(b[k] / a[k])
    return out


def table2(pt: dict, bs: dict, bands) -> pd.DataFrame:
    y0, y1 = BASE + 1, LAST + 1
    rows = []
    for band in bands:
        for design in DESIGNS:
            p = {sd: change(pt[(y0, band)], pt[(y1, band)], design, sd) for sd in SIDES}
            b = {sd: change(bs[(y0, band)], bs[(y1, band)], design, sd) for sd in SIDES}
            for sd in SIDES + ["bottom - top"]:
                if sd == "bottom - top":
                    pv = {k: p["bottom"][k] - p["top"][k] for k in p["top"]}
                    bv = {k: b["bottom"][k] - b["top"][k] for k in b["top"]}
                else:
                    pv, bv = p[sd], b[sd]
                row = {"band": band, "design": design, "side": sd}
                for k in pv:
                    row[k] = pv[k][0]
                    row[k + "_se"] = bv[k].std(ddof=1)
                rows.append(row)
    return pd.DataFrame(rows)


def table3(pt: dict, bands) -> pd.DataFrame:
    rows = []
    for (year, band), res in pt.items():
        if band not in bands:
            continue
        for side in SIDES:
            row = {"earn_year": year - 1, "band": band, "side": side}
            for d in DESIGNS:
                row[f"{d}_f"] = res[(d, side, "f")]["married"][0]
                row[f"{d}_m"] = res[(d, side, "m")]["married"][0]
            rows.append(row)
    return pd.DataFrame(rows)


def table4(pt: dict, cpi: dict, bands) -> pd.DataFrame:
    """Real per-capita wage bill (2024 $) for each group, main design."""
    rows = []
    for (year, band), res in pt.items():
        if band not in bands:
            continue
        f = cpi[year - 1]
        for side in SIDES:
            for sex, lab in (("f", "F"), ("m", "M")):
                st = res[("main", side, sex)]
                rows.append({"earn_year": year - 1, "band": band,
                             "group": f"{lab}_{side}", "PC_real": st["PC"][0] * f,
                             "E": st["E"][0], "W_real": st["W"][0] * f})
    t = pd.DataFrame(rows)
    wide = t.pivot_table(index=["band", "group"], columns="earn_year", values="PC_real")
    wide["pct_change_2000_2024"] = 100 * (wide[LAST] / wide[BASE] - 1)
    wide["dln_2000_2024"] = 100 * np.log(wide[LAST] / wide[BASE])
    return t, wide.reset_index()


def robustness(specs: dict) -> pd.DataFrame:
    rows = []
    for spec, (pt, bands) in specs.items():
        for band in bands:
            res0, res1 = pt[(BASE + 1, band)], pt[(LAST + 1, band)]
            row = {"spec": spec, "band": band}
            for sd in SIDES:
                c = change(res0, res1, "main", sd)
                row[f"R_{sd}_{BASE}"] = c["R0"][0]
                row[f"R_{sd}_{LAST}"] = c["R1"][0]
                row[f"dlnR_{sd}"] = c["dlnR"][0]
            row["dlnR_bottom_minus_top"] = row["dlnR_bottom"] - row["dlnR_top"]
            rows.append(row)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Markdown + chart
# --------------------------------------------------------------------------
def fmt_table(df: pd.DataFrame, floatfmt: dict | None = None) -> str:
    floatfmt = floatfmt or {}
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append(format(v, floatfmt.get(c, ".3f")))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def se_str(v, se, f=".3f"):
    return f"{v:{f}} ({se:{f}})"


def write_markdown(t1, t2, t3, t4w, rob, reps, path):
    md = ["# Gender per-capita wage-bill ratios: tables", "",
          "Generated by `analysis.py`. CPS ASEC, ages 25-54, ASECWT-weighted. "
          f"Bootstrap SEs in parentheses ({reps} person-level resamples within year).", ""]

    md += ["## Table 1. Main design, by year x band x side", "",
           "s = weighted share of women without a BA. PC = per-capita wage bill "
           "(nominal $, zeros included). R = PC_f / PC_m. E, W, H, hourly ratios are "
           "female/male employment rate, earnings per earner, annual hours per earner, "
           "and aggregate hourly wage (total earnings / total hours, earners with hours > 0).", ""]
    t = t1.copy()
    t["R (se)"] = [se_str(a, b) for a, b in zip(t.R, t.R_se)]
    t = t[["earn_year", "band", "side", "s", "PC_f", "PC_m", "R (se)", "E_ratio",
           "W_ratio", "H_ratio", "hourly_ratio"]]
    md += [fmt_table(t, {"PC_f": ",.0f", "PC_m": ",.0f"}), ""]

    md += ["## Table 2. Change 2000 -> 2024: main design vs B1 (education only) vs B2 "
           "(within-sex halves)", "",
           "dR = change in R (levels); dlnR = change in ln R x 100 (log points). The "
           "dlnR decomposition: dlnR = dln_E + dln_H + dln_hourly + dln_resid, where "
           "resid captures earners with zero reported hours (zero in this data: every earner reports hours). 'bottom - top' "
           "rows test whether the gap narrowed more at the bottom.", ""]
    t = t2.copy()
    for k, f in [("R0", ".3f"), ("R1", ".3f"), ("dR", ".3f"), ("dlnR", ".1f"),
                 ("dln_E", ".1f"), ("dln_H", ".1f"), ("dln_hourly", ".1f")]:
        t[k] = [se_str(a, b, f) for a, b in zip(t[k], t[k + "_se"])]
    t = t[["band", "design", "side", "R0", "R1", "dR", "dlnR", "dln_E", "dln_H", "dln_hourly"]]
    t = t.rename(columns={"R0": f"R {BASE}", "R1": f"R {LAST}"})
    md += [fmt_table(t), ""]

    md += ["## Table 3. Share currently married (MARST 1-2), by group", "",
           "**Descriptive only.** Men's earnings rank is partly endogenous to marriage "
           "(the marriage premium and selection into marriage), so differences in these "
           "shares are not a causal channel. main/B1/B2 = group definitions as above.", ""]
    md += [fmt_table(t3), ""]

    md += ["## Table 4. Real per-capita wage bill by group (2024 $, CPI-U-RS), main design", "",
           "Shows whether convergence comes from women rising or men falling.", ""]
    t = t4w.copy()
    t.columns = [str(c) for c in t.columns]
    md += [fmt_table(t, {c: ",.0f" for c in t.columns if c.isdigit()} |
                     {"pct_change_2000_2024": ".1f", "dln_2000_2024": ".1f"}), ""]

    md += ["## Table 5. Robustness (main design, point estimates)", "",
           "R1 drops ages 25-29 (youngest band becomes 30-34). R2 winsorizes INCWAGE at the "
           "weighted 99th percentile of earners within year x sex. R3 pools 25-54 with "
           "each sex's age-band mix held at its 2000 shares.", ""]
    md += [fmt_table(rob, {c: ".1f" for c in rob.columns if c.startswith("dln")}), ""]
    with open(path, "w") as fh:
        fh.write("\n".join(md))


def chart(t1: pd.DataFrame, pooled: pd.DataFrame, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"25-34": "#2a78d6", "35-44": "#eb6834", "45-54": "#1baf7a",
              POOLED: "#6b6b6b"}
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    for ax, side in zip(axes, SIDES):
        ends = []
        for band in BANDS:
            g = t1[(t1.band == band) & (t1.side == side)].sort_values("earn_year")
            ax.errorbar(g.earn_year, g.R, yerr=1.96 * g.R_se, color=colors[band],
                        lw=2, marker="o", ms=4, capsize=2, label=band)
            ends.append([g.R.iloc[-1], band, colors[band]])
        g = pooled[pooled.side == side].sort_values("earn_year")
        ax.plot(g.earn_year, g.R, color=colors[POOLED], lw=1.2, ls="--",
                label="25-54 pooled (2000 age mix)")
        ends.append([g.R.iloc[-1], "pooled", colors[POOLED]])
        # Direct labels at the right edge, nudged apart so they never overlap.
        ends.sort()
        orig = [e[0] for e in ends]
        for i in range(1, len(ends)):
            ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.07)
        shift = np.mean(orig) - np.mean([e[0] for e in ends])
        for e in ends:
            e[0] += shift
        for y, text, c in ends:
            ax.annotate(text, (LAST, y), xytext=(8, 0), textcoords="offset points",
                        va="center", color="#52514e", fontsize=8.5)
        ax.axhline(1.0, color="#9a9994", lw=0.8, zorder=0)
        title = ("Bottom: non-college women vs bottom-s men" if side == "bottom"
                 else "Top: college women vs top-(1-s) men")
        ax.set_title(title, fontsize=10, loc="left")
        ax.set_xticks([2000, 2009, 2018, 2024])
        ax.set_xlim(1998, 2028.5)
        ax.set_ylim(0, 1.4)
        ax.grid(axis="y", color="#e6e6e6", lw=0.8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        ax.set_xlabel("Earnings year")
    axes[0].set_ylabel("R = women's / men's per-capita wage bill")
    handles, labels = axes[0].get_legend_handles_labels()
    handles, labels = handles[1:] + handles[:1], labels[1:] + labels[:1]
    fig.legend(handles, labels, frameon=False, fontsize=8.5, ncol=4,
               loc="upper left", bbox_to_anchor=(0.01, 0.94))
    fig.suptitle("Gender per-capita wage-bill ratios, matched groups "
                 "(CPS ASEC, ages 25-54, 95% bootstrap CIs)",
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=160)


# --------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=20240)
    args = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    d = load()
    cpi = cpi_factors()

    cells = build_cells(d, BANDS, pooled_reweight=True)
    pt = point(cells)
    bs = bootstrap(d, cells, args.reps, args.seed)

    t1 = table1(pt, bs, BANDS)
    t1_pooled = table1({k: v for k, v in pt.items() if k[1] == POOLED},
                       {k: v for k, v in bs.items() if k[1] == POOLED}, [POOLED])
    t2 = table2(pt, bs, list(BANDS) + [POOLED])
    t3 = table3(pt, BANDS)
    t4, t4w = table4(pt, cpi, BANDS)

    pt_r1 = point(build_cells(d, R1_BANDS))
    pt_r2 = point(build_cells(winsorize(d), BANDS, pooled_reweight=True))
    rob = robustness({"main": (pt, list(BANDS)), "R1 drop 25-29": (pt_r1, ["30-34"]),
                      "R2 winsorize p99": (pt_r2, list(BANDS)),
                      "R3 pooled, 2000 age mix": (pt, [POOLED]),
                      "R2 + R3": (pt_r2, [POOLED])})

    t1.to_csv(os.path.join(OUT, "table1_main_by_year_band_side.csv"), index=False)
    t1_pooled.to_csv(os.path.join(OUT, "table1b_pooled_2000_age_mix.csv"), index=False)
    t2.to_csv(os.path.join(OUT, "table2_changes_2000_2024.csv"), index=False)
    t3.to_csv(os.path.join(OUT, "table3_married_share.csv"), index=False)
    t4.to_csv(os.path.join(OUT, "table4_real_pc_by_group_long.csv"), index=False)
    t4w.to_csv(os.path.join(OUT, "table4_real_pc_by_group.csv"), index=False)
    rob.to_csv(os.path.join(OUT, "table5_robustness.csv"), index=False)
    write_markdown(t1, t2, t3, t4w, rob, args.reps, os.path.join(OUT, "tables.md"))
    chart(t1, t1_pooled, os.path.join(OUT, "ratios_by_band.png"))
    print(f"Wrote outputs to {OUT}")


if __name__ == "__main__":
    main()
