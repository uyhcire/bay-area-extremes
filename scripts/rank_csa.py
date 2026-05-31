#!/usr/bin/env python3
"""Roll Zillow CBSA-level housing series up to Combined Statistical Areas (CSAs).

Zillow publishes ZHVI (typical home value) and ZORI (typical rent) at the CBSA
("metro") level, not the CSA level. This script aggregates them to CSAs using:

  * the Census/OMB delineation file  (county FIPS -> CBSA -> CSA), and
  * county population estimates       (to rank CSAs and weight the roll-up),

both fetched by scripts/download_csa_crosswalk.sh, joined to Zillow's
*county* files (County_zhvi.csv / County_zori.csv) by 5-digit county FIPS.

ZHVI/ZORI are typical-value indices, so they are aggregated as a
population-weighted mean across the counties in each CSA -- never summed.
(Population is the transparent proxy here; weighting owner units for ZHVI and
renter units for ZORI would be marginally more correct. Swap POP for any other
per-county weight in build_weights() to change this.)

Outputs a CSV ranked by population (largest first) covering every CSA, and
prints the top N to stdout.

Usage:
    scripts/rank_csa.py [--top N] [--out PATH]

Defaults: --top 20, --out data/raw/xwalk/csa_housing_ranking.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XWALK = ROOT / "data/raw/xwalk"
ZILLOW = ROOT / "data/raw/zillow"


def fips5(state, county) -> str:
    return f"{int(state):02d}{int(county):03d}"


def load_crosswalk(path: Path) -> dict[str, tuple[str, str]]:
    """county FIPS -> (csa_code, csa_title); only counties that belong to a CSA."""
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is required: pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    out: dict[str, tuple[str, str]] = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i < 3:  # rows 0-2 are titles + the header on row 2 (0-indexed)
            continue
        csa_code, csa_title = row[2], row[6]
        st, cty = row[9], row[10]
        if not (st and cty and csa_code):
            continue
        out[fips5(st, cty)] = (str(csa_code), str(csa_title))
    return out


def load_population(path: Path) -> dict[str, int]:
    pop: dict[str, int] = {}
    with open(path, encoding="latin-1") as f:
        for d in csv.DictReader(f):
            if d["SUMLEV"] != "050":  # county level only
                continue
            pop[fips5(d["STATE"], d["COUNTY"])] = int(d["POPESTIMATE2023"])
    return pop


def load_county_series(path: Path):
    """Return (latest_by_fips, first2000_by_fips, latest_date_label)."""
    with open(path) as f:
        rows = list(csv.reader(f))
    header, rows = rows[0], rows[1:]
    date_idx = [i for i, c in enumerate(header) if c[:2] == "20" and "-" in c]
    latest: dict[str, float] = {}
    first: dict[str, float] = {}
    for r in rows:
        st, cty = r[7], r[8]  # StateCodeFIPS, MunicipalCodeFIPS
        if not (st and cty):
            continue
        fips = fips5(st, cty)
        for i in reversed(date_idx):
            if r[i]:
                latest[fips] = float(r[i])
                break
        for i in date_idx:
            if r[i]:
                first[fips] = float(r[i])
                break
    return latest, first, header[date_idx[-1]]


def wmean(num: float, wt: float):
    return num / wt if wt else None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out", type=Path,
                    default=XWALK / "csa_housing_ranking.csv")
    args = ap.parse_args()

    fips2csa = load_crosswalk(XWALK / "delineation.xlsx")
    pop = load_population(XWALK / "co-est.csv")
    zhvi, zhvi_2000, zhvi_date = load_county_series(ZILLOW / "County_zhvi.csv")
    zori, _, zori_date = load_county_series(ZILLOW / "County_zori.csv")

    title: dict[str, str] = {}
    P = defaultdict(int)
    zh_n, zh_w = defaultdict(float), defaultdict(float)     # latest ZHVI
    z0_n, z0_w = defaultdict(float), defaultdict(float)     # 2000 ZHVI
    zo_n, zo_w = defaultdict(float), defaultdict(float)     # latest ZORI

    for fips, (code, csa_title) in fips2csa.items():
        title[code] = csa_title
        w = pop.get(fips, 0)        # build_weights(): swap POP here to reweight
        P[code] += w
        if w and fips in zhvi:
            zh_n[code] += zhvi[fips] * w; zh_w[code] += w
        if w and fips in zhvi_2000:
            z0_n[code] += zhvi_2000[fips] * w; z0_w[code] += w
        if w and fips in zori:
            zo_n[code] += zori[fips] * w; zo_w[code] += w

    ranked = sorted(P.items(), key=lambda kv: -kv[1])

    rows = []
    for rank, (code, p) in enumerate(ranked, 1):
        z = wmean(zh_n[code], zh_w[code])
        z0 = wmean(z0_n[code], z0_w[code])
        o = wmean(zo_n[code], zo_w[code])
        rows.append({
            "rank": rank,
            "csa_code": code,
            "csa_title": title[code],
            "population_2023": p,
            "zhvi": round(z) if z else "",
            "zori": round(o) if o else "",
            "price_to_rent": round(z / (o * 12), 1) if (z and o) else "",
            "appreciation_since_2000": round(z / z0, 2) if (z and z0) else "",
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"ZHVI {zhvi_date} · ZORI {zori_date} · pop 2023 · weight=population")
    print(f"Wrote {len(rows)} CSAs to {args.out}\n")
    hdr = f"{'#':>2}  {'CSA':46s} {'Pop(M)':>6} {'wZHVI':>10} {'wZORI':>6} {'P/R':>5} {'x2000':>6}"
    print(hdr)
    for r in rows[: args.top]:
        z = f"${r['zhvi']:,}" if r["zhvi"] != "" else "n/a"
        o = f"${r['zori']:,}" if r["zori"] != "" else "n/a"
        pr = r["price_to_rent"] if r["price_to_rent"] != "" else "n/a"
        ap_ = f"{r['appreciation_since_2000']}x" if r["appreciation_since_2000"] != "" else "n/a"
        print(f"{r['rank']:>2}  {r['csa_title'][:46]:46s} {r['population_2023']/1e6:6.2f} "
              f"{z:>10} {o:>6} {pr!s:>5} {ap_:>6}")


if __name__ == "__main__":
    main()
