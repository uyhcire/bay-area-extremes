#!/usr/bin/env python3
"""Build a Sankey diagram of where the average Bay Area household's income goes,
in real (price-parity-adjusted) dollars, with each leaf compared to the U.S. average.

Inputs (under data/raw/, see CLAUDE.md):
  cex_<YEAR>_2yr/cu-msa-west-2-year-average-<YEAR-1>-<YEAR>.xlsx   scripts/download_cex.sh
  cex_<YEAR>_2yr/cu-region-2-year-average-<YEAR-1>-<YEAR>.xlsx     scripts/download_cex.sh
  bea_marpp/MARPP_MSA_2008_<YEAR>.csv      https://apps.bea.gov/regional/zip/MARPP.zip (key-free)
  bea_sainc/SAINC50__ALL_AREAS_*.csv       https://apps.bea.gov/regional/zip/SAINC.zip (key-free)
  irs_soi/<yy>incyallagi.csv               https://www.irs.gov/pub/irs-soi/<yy>incyallagi.csv
Outputs:
  analysis/income_sankey.json   the computed table
  analysis/income_sankey.html   self-contained page (static SVG + hover tooltips)

Method: nominal CEX dollars per consumer unit are divided by the BEA regional
price parity (RPP) for the matching price category (goods / housing / utilities /
other services; all-items for taxes, saving and giving). U.S. figures are
deflated by the U.S. RPPs (~100) the same way.

Taxes: BLS stopped publishing CEX tax estimates with the 2024 tables, so
  federal tax     = CEX income x (IRS SOI total tax liability / AGI) for the
                    metro's five counties, or for the U.S.
  state and local = federal tax x (BEA state+local personal current taxes /
                    federal personal current taxes) for California, or the U.S.
Net saving is the residual: income - expenditures - taxes.

Usage: python3 analysis/build_income_sankey.py [YEAR]     # default 2024
"""
import csv
import html
import json
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
CEX_DIR = ROOT / "data/raw" / f"cex_{YEAR}_2yr"
RPP_CSV = ROOT / "data/raw/bea_marpp" / f"MARPP_MSA_2008_{YEAR}.csv"
CEX_AREA = "San Francisco"  # CEX column header prefix (San Francisco-Oakland-Hayward)
RPP_FIPS = "41860"          # BEA: San Francisco-Oakland-Fremont MSA (same 5 counties)
SOI_CSV = ROOT / "data/raw/irs_soi" / f"{(YEAR - 1) % 100:02d}incyallagi.csv"  # first of the two CEX years
SOI_COUNTIES = {"001", "013", "041", "075", "081"}  # Alameda, Contra Costa, Marin, SF, San Mateo
SAINC50 = ROOT / "data/raw/bea_sainc"

# (group, leaf label, [CEX item labels summed], RPP category)
# RPP categories: A = all items, G = goods, H = housing, U = utilities, S = other services
LEAVES = [
    ("Housing", "Rent, mortgage interest, property tax", ["Shelter"], "H"),
    ("Housing", "Utilities, fuels, phone & internet", ["Utilities, fuels, and public services"], "U"),
    ("Housing", "Household services (childcare, cleaning…)", ["Household operations"], "S"),
    ("Housing", "Furnishings & household supplies",
     ["Housekeeping supplies", "Household furnishings and equipment"], "G"),
    ("Taxes", "Federal income & self-employment tax", ["__fedtax__"], "A"),
    ("Taxes", "State & local income tax, vehicle fees", ["__statetax__"], "A"),
    ("Saving", "Retirement & Social Security contributions", ["Retirement, pensions, and Social Security"], "A"),
    ("Saving", "Life & other personal insurance", ["Life and other personal insurance"], "A"),
    ("Saving", "Everything left over (net saving)", ["__residual__"], "A"),
    ("Food", "Groceries", ["Food at home"], "G"),
    ("Food", "Restaurants & takeout", ["Food away from home"], "S"),
    ("Food", "Alcohol", ["Alcoholic beverages"], "G"),
    ("Transportation", "Vehicle purchases", ["Vehicle purchases (net outlay)"], "G"),
    ("Transportation", "Gasoline & fuel", ["Gasoline and other fuels"], "G"),
    ("Transportation", "Car insurance, repairs, finance", ["Other vehicle expenses"], "S"),
    ("Transportation", "Transit, flights, rideshare", ["Public and other transportation"], "S"),
    ("Healthcare", "Healthcare (insurance, care, drugs)", ["Healthcare"], "S"),
    ("Everything else", "Entertainment", ["Entertainment"], "S"),
    ("Everything else", "Education", ["Education"], "S"),
    ("Everything else", "Clothing", ["Apparel and services"], "G"),
    ("Everything else", "Gifts & donations", ["Cash contributions"], "A"),
    ("Everything else", "Personal care", ["Personal care products and services"], "S"),
    ("Everything else", "Miscellaneous, reading, tobacco",
     ["Miscellaneous", "Reading", "Tobacco products and smoking supplies"], "S"),
]
GROUPS = ["Housing", "Taxes", "Saving", "Food", "Transportation", "Healthcare", "Everything else"]
RPP_LINES = {"A": "RPPs: All items", "G": "RPPs: Goods", "H": "RPPs: Services: Housing",
             "U": "RPPs: Services: Utilities", "S": "RPPs: Services: Other"}
RPP_NAMES = {"A": "all items", "G": "goods", "H": "housing", "U": "utilities", "S": "other services"}


# ----------------------------------------------------------------------------- data

def norm(s):
    return " ".join(str(s).replace("\xa0", " ").split()).strip().lower()


def read_cex_column(path, col_prefix):
    """Return {normalized item label: mean value} for the column whose header starts with col_prefix."""
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    col = None
    for r in rows[:15]:
        for j, v in enumerate(r):
            if v is not None and norm(v).startswith(norm(col_prefix)):
                col = j
                break
        if col is not None:
            break
    if col is None:
        raise SystemExit(f"{path.name}: no column starting with {col_prefix!r}")
    out = {}
    for i, r in enumerate(rows):
        if not r or r[0] is None:
            continue
        label = norm(r[0])
        val = r[col] if col < len(r) else None
        # Some layouts put the value on a following "Mean" row.
        if not isinstance(val, (int, float)):
            for r2 in rows[i + 1:i + 3]:
                if r2 and r2[0] is not None and norm(r2[0]) == "mean" and isinstance(r2[col], (int, float)):
                    val = r2[col]
                    break
        if isinstance(val, (int, float)) and label not in out and label not in ("mean", "se", "cv(%)", "rse"):
            out[label] = float(val)
    return out


def load_cex():
    ba = read_cex_column(CEX_DIR / f"cu-msa-west-2-year-average-{YEAR - 1}-{YEAR}.xlsx", CEX_AREA)
    us = read_cex_column(CEX_DIR / f"cu-region-2-year-average-{YEAR - 1}-{YEAR}.xlsx", "All consumer units")
    return ba, us


def load_rpp():
    """Average the RPP over the two CEX survey years, for the metro and the U.S."""
    years = [str(YEAR - 1), str(YEAR)]
    out = {"ba": {}, "us": {}}
    with open(RPP_CSV, encoding="latin-1") as f:
        rd = csv.reader(f)
        head = next(rd)
        yi = [head.index(y) for y in years]
        for r in rd:
            if len(r) < len(head):
                continue
            fips = r[0].strip().strip('"').strip()
            who = {"00000": "us", RPP_FIPS: "ba"}.get(fips)
            desc = norm(r[head.index("Description")])
            for k, line in RPP_LINES.items():
                if who and desc == norm(line):
                    out[who][k] = sum(float(r[i]) for i in yi) / len(yi)
    assert all(len(v) == 5 for v in out.values()), out
    return out


def load_tax_rates():
    """Effective federal rate (IRS SOI) and state+local-to-federal ratio (BEA SAINC50)."""
    agg = {"ba": [0.0, 0.0], "us": [0.0, 0.0]}
    with open(SOI_CSV, encoding="latin-1") as f:
        for r in csv.DictReader(f):
            keys = []
            if r["COUNTYFIPS"] == "000":
                keys.append("us")  # state-total rows sum to the U.S.
            elif r["STATEFIPS"] == "06" and r["COUNTYFIPS"] in SOI_COUNTIES:
                keys.append("ba")
            for k in keys:
                agg[k][0] += float(r["A10300"])  # total tax liability
                agg[k][1] += float(r["A00100"])  # adjusted gross income
    fed = {k: t / a for k, (t, a) in agg.items()}

    path = sorted(SAINC50.glob("SAINC50__ALL_AREAS_*.csv"))[-1]
    lines = {"70": "fed", "120": "state", "180": "local"}
    tot = {"ba": {}, "us": {}}
    with open(path, encoding="latin-1") as f:
        rd = csv.reader(f)
        head = next(rd)
        yi = [head.index(str(YEAR - 1)), head.index(str(YEAR))]
        for r in rd:
            if len(r) < len(head):
                continue
            who = {"00000": "us", "06000": "ba"}.get(r[0].strip(' "'))  # California stands in for the metro
            name = lines.get(r[head.index("LineCode")].strip())
            if who and name:
                tot[who][name] = sum(float(r[i]) for i in yi)
    sl = {k: (v["state"] + v["local"]) / v["fed"] for k, v in tot.items()}
    return dict(fed=fed, state_local_per_fed=sl)


def compute(ba, us, rpp, tax):
    for who, d in (("ba", ba), ("us", us)):
        d["__fedtax__"] = d["income before taxes"] * tax["fed"][who]
        d["__statetax__"] = d["__fedtax__"] * tax["state_local_per_fed"][who]
        d["__residual__"] = (d["income before taxes"] - d["average annual expenditures"]
                             - d["__fedtax__"] - d["__statetax__"])

    def get(d, item):
        return d[item] if item.startswith("__") else d[norm(item)]

    leaves = []
    for group, label, items, cat in LEAVES:
        nb = sum(get(ba, i) for i in items)
        nu = sum(get(us, i) for i in items)
        rb, ru = nb / rpp["ba"][cat] * 100, nu / rpp["us"][cat] * 100
        leaves.append(dict(group=group, label=label, cat=cat, rpp=rpp["ba"][cat],
                           nominal_ba=nb, nominal_us=nu, real_ba=rb, real_us=ru,
                           pct=(rb / ru - 1) * 100))
    # The listed leaves must exhaust income exactly (nominal identity).
    for d, k in ((ba, "nominal_ba"), (us, "nominal_us")):
        gap = sum(l[k] for l in leaves) - d["income before taxes"]
        assert abs(gap) < 0.005 * d["income before taxes"], f"{k}: leaves miss income by {gap:,.0f}"
    tot = {k: sum(l[k] for l in leaves) for k in ("nominal_ba", "nominal_us", "real_ba", "real_us")}
    groups = []
    for g in GROUPS:
        ls = [l for l in leaves if l["group"] == g]
        rb, ru = sum(l["real_ba"] for l in ls), sum(l["real_us"] for l in ls)
        groups.append(dict(group=g, real_ba=rb, real_us=ru, nominal_ba=sum(l["nominal_ba"] for l in ls),
                           pct=(rb / ru - 1) * 100))
    meta = dict(year=YEAR, rpp=rpp, tax=tax, totals=tot,
                real_income_pct=(tot["real_ba"] / tot["real_us"] - 1) * 100,
                nominal_income_pct=(tot["nominal_ba"] / tot["nominal_us"] - 1) * 100,
                cu_size_ba=ba.get("people"), cu_size_us=us.get("people"))
    return dict(meta=meta, groups=groups, leaves=leaves)


# --------------------------------------------------------------------------- render

def usd(v):
    return f"${v:,.0f}" if v >= 0 else f"−${-v:,.0f}"


def pct(v):
    return f"+{v:.0f}%" if v >= 0 else f"−{-v:.0f}%"


def ribbon(x0, y0a, y0b, x1, y1a, y1b):
    m = (x0 + x1) / 2
    return (f"M{x0:.1f},{y0a:.1f} C{m:.1f},{y0a:.1f} {m:.1f},{y1a:.1f} {x1:.1f},{y1a:.1f} "
            f"L{x1:.1f},{y1b:.1f} C{m:.1f},{y1b:.1f} {m:.1f},{y0b:.1f} {x0:.1f},{y0b:.1f} Z")


def render_svg(data):
    leaves, groups, tot = data["leaves"], data["groups"], data["meta"]["totals"]
    W, NODE, PAD_T = 1000, 14, 30
    X0, X1, X2 = 96, 340, 570           # left edges of the three node columns
    BAR = 600                           # px height of the income bar
    k = BAR / tot["real_ba"]            # px per real dollar
    G_GAP, L_GAP, L_MIN, GG_GAP = 16, 5, 19, 14  # group gap; leaf gap; min leaf row; gap between leaf groups

    # leaf column: each leaf gets a row at least L_MIN tall so labels never collide
    y, gi_prev = PAD_T, None
    for l in leaves:
        gi = GROUPS.index(l["group"])
        if gi_prev is not None:
            y += GG_GAP if gi != gi_prev else L_GAP
        l["h"] = max(l["real_ba"] * k, 1.5)
        row = max(l["h"], L_MIN)
        l["y"], l["row"], l["gi"] = y + (row - l["h"]) / 2, row, gi
        l["ymid"] = y + row / 2
        y += row
        gi_prev = gi
    H_leaves = y
    # group column: centred on its leaves' span where possible, stacked without overlap
    gh = [g["real_ba"] * k for g in groups]
    total_g = sum(gh) + G_GAP * (len(groups) - 1)
    gy = PAD_T + (H_leaves - PAD_T - total_g) / 2
    for g, h in zip(groups, gh):
        g["y"], g["h"] = gy, h
        gy += h + G_GAP
    inc_y = PAD_T + (H_leaves - PAD_T - BAR) / 2
    H = H_leaves + 14

    o = [f'<svg viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" role="img" '
         f'aria-label="Sankey diagram of Bay Area household income by use, in real dollars">']
    o.append(f'<text class="colhead" x="{X0 + NODE}" y="14" text-anchor="end">Income</text>')
    o.append(f'<text class="colhead" x="{X1}" y="14">Where it goes</text>')
    o.append(f'<text class="colhead" x="{X2 + NODE + 10}" y="14">Real $ per household</text>')
    o.append(f'<text class="colhead" x="{W - 4}" y="14" text-anchor="end">vs. U.S. average</text>')

    # ribbons income -> group
    yy = inc_y
    for i, g in enumerate(groups):
        o.append(f'<path class="rib g{i}" data-tip="g{i}" d="'
                 f'{ribbon(X0 + NODE, yy, yy + g["h"], X1, g["y"], g["y"] + g["h"])}"/>')
        yy += g["h"]
    # ribbons group -> leaf
    for i, g in enumerate(groups):
        yy = g["y"]
        for j, l in enumerate(leaves):
            if l["gi"] != i:
                continue
            hh = l["real_ba"] * k
            o.append(f'<path class="rib g{i}" data-tip="l{j}" d="'
                     f'{ribbon(X1 + NODE, yy, yy + hh, X2, l["y"], l["y"] + l["h"])}"/>')
            yy += hh
    # nodes
    o.append(f'<rect class="node inc" x="{X0}" y="{inc_y:.1f}" width="{NODE}" height="{BAR}" rx="2"/>')
    cy = inc_y + BAR / 2
    o.append(f'<text class="big" x="{X0 - 10}" y="{cy - 8:.0f}" text-anchor="end">{usd(tot["real_ba"])}</text>')
    o.append(f'<text class="sub" x="{X0 - 10}" y="{cy + 10:.0f}" text-anchor="end">real income</text>')
    o.append(f'<text class="sub strong" x="{X0 - 10}" y="{cy + 28:.0f}" text-anchor="end">'
             f'{pct(data["meta"]["real_income_pct"])} vs U.S.</text>')
    for i, g in enumerate(groups):
        o.append(f'<rect class="node g{i}" data-tip="g{i}" x="{X1}" y="{g["y"]:.1f}" width="{NODE}" '
                 f'height="{g["h"]:.1f}" rx="2"/>')
        gm = g["y"] + g["h"] / 2
        if g["h"] >= 30:
            o.append(f'<text class="glabel" x="{X1 - 8}" y="{gm - 3:.1f}" text-anchor="end">{html.escape(g["group"])}</text>')
            o.append(f'<text class="sub" x="{X1 - 8}" y="{gm + 12:.1f}" text-anchor="end">{usd(g["real_ba"])}</text>')
        else:
            o.append(f'<text class="glabel" x="{X1 - 8}" y="{gm + 4:.1f}" text-anchor="end">{html.escape(g["group"])}</text>')
    for j, l in enumerate(leaves):
        o.append(f'<rect class="node g{l["gi"]}" data-tip="l{j}" x="{X2}" y="{l["y"]:.1f}" width="{NODE}" '
                 f'height="{l["h"]:.1f}" rx="1.5"/>')
        ty = l["ymid"] + 4.5
        o.append(f'<text class="llabel" x="{X2 + NODE + 10}" y="{ty:.1f}">{html.escape(l["label"])}'
                 f'<tspan class="lval" dx="8">{usd(l["real_ba"])}</tspan></text>')
        cls = "lpct neg" if l["pct"] < 0 else "lpct"
        o.append(f'<text class="{cls}" x="{W - 4}" y="{ty:.1f}" text-anchor="end">{pct(l["pct"])}</text>')
        # generous invisible hit row
        o.append(f'<rect class="hit" data-tip="l{j}" x="{X2}" y="{l["ymid"] - l["row"] / 2:.1f}" '
                 f'width="{W - X2}" height="{l["row"]:.1f}"/>')
    o.append("</svg>")
    return "\n".join(o)


def render_table(data):
    r = ['<table><thead><tr><th>Use of income</th><th class="n">Bay Area, nominal</th>'
         '<th class="n">Price level<br>(U.S. = 100)</th><th class="n">Bay Area, real</th>'
         '<th class="n">U.S., real</th><th class="n">Bay Area vs U.S.</th></tr></thead><tbody>']
    for i, g in enumerate(data["groups"]):
        r.append(f'<tr class="grow"><td><span class="sw g{i}"></span>{html.escape(g["group"])}</td>'
                 f'<td class="n">{usd(g["nominal_ba"])}</td><td class="n"></td><td class="n">{usd(g["real_ba"])}</td>'
                 f'<td class="n">{usd(g["real_us"])}</td><td class="n">{pct(g["pct"])}</td></tr>')
        for l in data["leaves"]:
            if l["group"] != g["group"]:
                continue
            r.append(f'<tr><td class="ind">{html.escape(l["label"])}</td><td class="n">{usd(l["nominal_ba"])}</td>'
                     f'<td class="n">{l["rpp"]:.0f} <span class="dim">{RPP_NAMES[l["cat"]]}</span></td>'
                     f'<td class="n">{usd(l["real_ba"])}</td><td class="n">{usd(l["real_us"])}</td>'
                     f'<td class="n">{pct(l["pct"])}</td></tr>')
    t = data["meta"]["totals"]
    r.append(f'<tr class="grow tot"><td>Total income</td><td class="n">{usd(t["nominal_ba"])}</td><td class="n"></td>'
             f'<td class="n">{usd(t["real_ba"])}</td><td class="n">{usd(t["real_us"])}</td>'
             f'<td class="n">{pct(data["meta"]["real_income_pct"])}</td></tr></tbody></table>')
    return "\n".join(r)


def render_page(data):
    m, t = data["meta"], data["meta"]["totals"]
    y0, y1 = m["year"] - 1, m["year"]
    tips = {}
    for i, g in enumerate(data["groups"]):
        tips[f"g{i}"] = dict(t=g["group"], gi=i, a=usd(g["real_ba"]), b=usd(g["real_us"]), p=pct(g["pct"]),
                             s=f'{g["real_ba"] / t["real_ba"] * 100:.0f}% of real income')
    for j, l in enumerate(data["leaves"]):
        tips[f"l{j}"] = dict(t=l["label"], gi=GROUPS.index(l["group"]), a=usd(l["real_ba"]), b=usd(l["real_us"]),
                             p=pct(l["pct"]),
                             s=f'{usd(l["nominal_ba"])} nominal ÷ {l["rpp"]:.0f} ({RPP_NAMES[l["cat"]]} prices)')
    legend = "".join(f'<span class="lg"><span class="sw g{i}"></span>{html.escape(g)}</span>'
                     for i, g in enumerate(GROUPS))
    tpl = (Path(__file__).parent / "income_sankey.template.html").read_text()
    rep = {
        "{{SVG}}": render_svg(data), "{{TABLE}}": render_table(data), "{{LEGEND}}": legend,
        "{{TIPS}}": json.dumps(tips, ensure_ascii=False),
        "{{YEARS}}": f"{y0}–{str(y1)[2:]}",
        "{{NOM_BA}}": usd(t["nominal_ba"]), "{{NOM_US}}": usd(t["nominal_us"]),
        "{{REAL_BA}}": usd(t["real_ba"]), "{{REAL_US}}": usd(t["real_us"]),
        "{{NOM_PCT}}": pct(m["nominal_income_pct"]), "{{REAL_PCT}}": pct(m["real_income_pct"]),
        "{{RPP_ALL}}": f'{m["rpp"]["ba"]["A"]:.0f}', "{{RPP_H}}": f'{m["rpp"]["ba"]["H"]:.0f}',
        "{{RPP_U}}": f'{m["rpp"]["ba"]["U"]:.0f}', "{{RPP_G}}": f'{m["rpp"]["ba"]["G"]:.0f}',
        "{{RPP_S}}": f'{m["rpp"]["ba"]["S"]:.0f}',
        "{{SOI_YEAR}}": str(y0),
        "{{FED_BA}}": f'{m["tax"]["fed"]["ba"] * 100:.1f}%', "{{FED_US}}": f'{m["tax"]["fed"]["us"] * 100:.1f}%',
        "{{SL_BA}}": f'{m["tax"]["state_local_per_fed"]["ba"]:.2f}', "{{SL_US}}": f'{m["tax"]["state_local_per_fed"]["us"]:.2f}',
    }
    for a, b in rep.items():
        tpl = tpl.replace(a, b)
    return tpl


def main():
    ba, us = load_cex()
    data = compute(ba, us, load_rpp(), load_tax_rates())
    out = Path(__file__).parent
    page = render_page(data)  # render adds layout keys to leaves; dump clean numbers only
    keep = ("group", "label", "cat", "rpp", "nominal_ba", "nominal_us", "real_ba", "real_us", "pct")
    clean = dict(meta=data["meta"],
                 groups=[{k: g[k] for k in ("group", "nominal_ba", "real_ba", "real_us", "pct")} for g in data["groups"]],
                 leaves=[{k: l[k] for k in keep} for l in data["leaves"]])
    (out / "income_sankey.json").write_text(json.dumps(clean, indent=1))
    (out / "income_sankey.html").write_text(page)
    print(f"real income: Bay Area {usd(data['meta']['totals']['real_ba'])} vs U.S. "
          f"{usd(data['meta']['totals']['real_us'])} ({pct(data['meta']['real_income_pct'])})")
    for l in data["leaves"]:
        print(f"  {l['label'][:46]:46s} {usd(l['real_ba']):>9s}  {pct(l['pct']):>6s}")


if __name__ == "__main__":
    main()
