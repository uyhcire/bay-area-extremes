#!/usr/bin/env python3
"""Rank the top-30 U.S. metros by gross operating surplus relative to personal income.

BEA publishes gross operating surplus (GOS) only at the state level (SAGDP7), so
metro GOS is derived county-by-county as a residual of the GDP income components:

    GOS = GDP  -  compensation of employees  -  TOPI

where TOPI (taxes on production and imports less subsidies) is not published
below the state level and is estimated for each county as
county GDP x its state's TOPI share of state GDP. TOPI is a small (~3-9% of
GDP) and geographically stable term, so the estimate perturbs GOS only
slightly. Counties are aggregated to metropolitan statistical areas with the
OMB July 2023 delineations (the vintage BEA uses for the 2024 estimates),
after remapping the Virginia independent-city and Kalawao, HI combinations
BEA folds into single county units.

Inputs (all keyless):
  - BEA bulk zips: CAGDP2 (county GDP), CAINC6N (county compensation),
    CAINC1 (county personal income + population)
    from https://apps.bea.gov/regional/zip/<TABLE>.zip
  - BEA state SAGDP2 (GDP) and SAGDP3 (TOPI less subsidies) via the
    iTablecore JSON endpoint that backs https://apps.bea.gov/itable/
    (the bulk zips do not carry the SAGDP component tables)
  - OMB/Census CBSA delineation file list1_2023.xlsx

Usage:  python3 scripts/metro_gos_pi_ratio.py [YEAR]     # default 2024
Needs:  pandas, openpyxl. Writes analysis/metro_gos_pi_ratio_<YEAR>.{csv,md}
and downloads raw inputs to data/raw/ (git-ignored).
"""
import io
import json
import pathlib
import re
import subprocess
import sys
import urllib.request
import zipfile

import pandas as pd

YEAR = sys.argv[1] if len(sys.argv) > 1 else "2024"
ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis"

BEA_ZIP = "https://apps.bea.gov/regional/zip/{}.zip"
DELINEATION_URL = ("https://www2.census.gov/programs-surveys/metro-micro/geographies/"
                   "reference-files/2023/delineation-files/list1_2023.xlsx")
ITABLE_API = "https://apps.bea.gov/iTablecore/data/app/GetSteps"

# BEA folds Virginia independent cities (and Kalawao, HI) into combined county
# units; map each Census county FIPS to its BEA unit.
BEA_COMBINED = {
    "51901": ["51003", "51540"],           # Albemarle + Charlottesville
    "51903": ["51005", "51580"],           # Alleghany + Covington
    "51907": ["51015", "51790", "51820"],  # Augusta, Staunton + Waynesboro
    "51911": ["51031", "51680"],           # Campbell + Lynchburg
    "51913": ["51035", "51640"],           # Carroll + Galax
    "51918": ["51053", "51570", "51730"],  # Dinwiddie, Colonial Heights + Petersburg
    "51919": ["51059", "51600", "51610"],  # Fairfax, Fairfax City + Falls Church
    "51921": ["51069", "51840"],           # Frederick + Winchester
    "51923": ["51081", "51595"],           # Greensville + Emporia
    "51929": ["51089", "51690"],           # Henry + Martinsville
    "51931": ["51095", "51830"],           # James City + Williamsburg
    "51933": ["51121", "51750"],           # Montgomery + Radford
    "51939": ["51143", "51590"],           # Pittsylvania + Danville
    "51941": ["51149", "51670"],           # Prince George + Hopewell
    "51942": ["51153", "51683", "51685"],  # Prince William, Manassas + Manassas Park
    "51944": ["51161", "51775"],           # Roanoke + Salem
    "51945": ["51163", "51530", "51678"],  # Rockbridge, Buena Vista + Lexington
    "51947": ["51165", "51660"],           # Rockingham + Harrisonburg
    "51949": ["51175", "51620"],           # Southampton + Franklin
    "51951": ["51177", "51630"],           # Spotsylvania + Fredericksburg
    "51953": ["51191", "51520"],           # Washington + Bristol
    "51955": ["51195", "51720"],           # Wise + Norton
    "51958": ["51199", "51735"],           # York + Poquoson
    "15901": ["15009", "15005"],           # Maui + Kalawao
}
CENSUS_TO_BEA = {c: b for b, comps in BEA_COMBINED.items() for c in comps}


def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=300) as r:
        dest.write_bytes(r.read())
    return dest


def bea_county_table(table, linecode, year):
    """One line of a BEA county bulk table as fips -> value (counties only)."""
    path = download(BEA_ZIP.format(table), RAW / "bea_regional" / f"{table}.zip")
    zf = zipfile.ZipFile(path)
    csv_name = [n for n in zf.namelist() if "ALL_AREAS" in n][0]
    df = pd.read_csv(zf.open(csv_name), encoding="latin-1", dtype=str)
    df["GeoFIPS"] = df["GeoFIPS"].str.strip().str.strip('"')
    df = df[(df["LineCode"] == str(linecode)) & (df["GeoFIPS"].str.len() == 5)
            & ~df["GeoFIPS"].str.endswith("000")]
    return pd.DataFrame({"fips": df["GeoFIPS"].values,
                         "val": pd.to_numeric(df[year], errors="coerce").values})


def bea_state_table(tableid, year):
    """One year of a BEA state iTable (all states) as {2-digit fips: value}."""
    data = [["isuri", "1"], ["tableid", str(tableid)], ["major_area", "0"],
            ["state", "0"], ["area", "XX"], ["statistic", "1"],
            ["unit_of_measure", "levels"], ["year", year], ["yearbegin", "-1"],
            ["year_end", "-1"], ["classification", "naics"]]
    body = json.dumps({"appid": 70, "steps": [30], "data": data})
    out = subprocess.run(["curl", "-s", "-X", "POST", ITABLE_API,
                          "-H", "Content-Type: application/json", "--data", body],
                         capture_output=True, text=True, timeout=300, check=True)
    resp = json.loads(out.stdout)
    step30 = [s for s in resp["Steps"] if s["Number"] == 30][0]
    prompt = [p for p in step30["Prompts"] if p["Name"] == "Selected_Income_data"][0]
    tbl = json.loads(json.loads(prompt["PromtData"])["Table"])
    unit = 1e6 if "Millions" in tbl["Sub_Title"] else 1e3
    hdr = int(tbl["Number_Of_Header_Rows"])
    out = {}
    for row in tbl["Data_Rows"][hdr:]:
        fips = row[0]["CV"].strip()
        if len(fips) == 5 and fips.endswith("000") and fips != "00000":
            out[fips[:2]] = float(row[2]["CV"].replace(",", "")) * unit
    return out


def main():
    gdp = bea_county_table("CAGDP2", 1, YEAR).rename(columns={"val": "gdp"})    # $000
    comp = bea_county_table("CAINC6N", 1, YEAR).rename(columns={"val": "comp"})  # $000
    pi = bea_county_table("CAINC1", 1, YEAR).rename(columns={"val": "pi"})       # $000
    pop = bea_county_table("CAINC1", 2, YEAR).rename(columns={"val": "pop"})     # persons

    st_gdp = bea_state_table(505, YEAR)   # SAGDP2, state GDP ($)
    st_topi = bea_state_table(506, YEAR)  # SAGDP3, state TOPI less subsidies ($)
    topi_share = {st: st_topi[st] / st_gdp[st] for st in st_gdp if st in st_topi}

    delin = pd.read_excel(
        download(DELINEATION_URL, RAW / "census_delineation" / "list1_2023.xlsx"),
        skiprows=2, dtype=str)
    delin = delin[delin["Metropolitan/Micropolitan Statistical Area"]
                  == "Metropolitan Statistical Area"]
    delin["fips"] = (delin["FIPS State Code"].str.zfill(2)
                     + delin["FIPS County Code"].str.zfill(3))
    delin = delin[~delin["fips"].str.startswith("72")]  # no BEA county data for PR
    delin["fips"] = delin["fips"].map(lambda f: CENSUS_TO_BEA.get(f, f))
    cbsa = (delin[["CBSA Code", "CBSA Title", "fips"]]
            .rename(columns={"CBSA Code": "cbsa", "CBSA Title": "title"})
            .drop_duplicates())
    multi = cbsa.groupby("fips")["cbsa"].nunique()
    assert (multi <= 1).all(), f"BEA unit in two CBSAs: {multi[multi > 1]}"

    c = gdp.merge(comp, on="fips", how="outer").merge(pi, on="fips", how="outer") \
           .merge(pop, on="fips", how="outer")
    c["topi_est"] = c["gdp"] * c["fips"].str[:2].map(topi_share)

    m = cbsa.merge(c, on="fips", how="left")
    agg = m.groupby(["cbsa", "title"]).agg(
        gdp=("gdp", "sum"), comp=("comp", "sum"), pi=("pi", "sum"),
        pop=("pop", "sum"), topi=("topi_est", "sum"),
        n_na=("gdp", lambda s: int(s.isna().sum()))).reset_index()
    agg["gos"] = agg["gdp"] - agg["comp"] - agg["topi"]
    agg["gos_pi"] = agg["gos"] / agg["pi"]
    agg["gos_gdp"] = agg["gos"] / agg["gdp"]

    top30 = agg.sort_values("pop", ascending=False).head(30)
    bad = top30[top30["n_na"] > 0]
    if len(bad):
        print("WARNING: top-30 metros with missing county data:\n",
              bad[["title", "n_na"]].to_string())
    top30 = top30.sort_values("gos_pi", ascending=False).reset_index(drop=True)

    OUT.mkdir(exist_ok=True)
    csv_path = OUT / f"metro_gos_pi_ratio_{YEAR}.csv"
    md_path = OUT / f"metro_gos_pi_ratio_{YEAR}.md"
    top30.to_csv(csv_path, index=False)

    lines = [
        f"# Gross operating surplus vs. personal income, top-30 U.S. metros ({YEAR})",
        "",
        "Top 30 metropolitan statistical areas by population, ranked by the ratio of",
        "gross operating surplus (GOS) to personal income. GOS is derived from BEA",
        "county accounts as GDP (CAGDP2) minus compensation of employees (CAINC6N)",
        "minus taxes on production and imports less subsidies (TOPI); BEA does not",
        "publish TOPI below the state level, so it is estimated as county GDP times",
        "the state TOPI share (SAGDP3/SAGDP2). Personal income and population are",
        "from CAINC1. Counties are aggregated to metros with the OMB July 2023",
        "delineations. Dollar figures in billions.",
        "",
        "| # | Metro area | Pop. (M) | GDP | Compensation | GOS | Personal income | GOS/PI | GOS/GDP |",
        "|--:|------------|---------:|----:|----:|----:|----:|------:|------:|",
    ]
    for i, r in top30.iterrows():
        lines.append(
            f"| {i+1} | {r['title']} | {r['pop']/1e6:.2f} | {r['gdp']/1e6:,.0f} "
            f"| {r['comp']/1e6:,.0f} | {r['gos']/1e6:,.0f} | {r['pi']/1e6:,.0f} "
            f"| {r['gos_pi']*100:.1f}% | {r['gos_gdp']*100:.1f}% |")
    lines += [
        "",
        "Notes: GOS numerator is place-of-production, personal income denominator is",
        "place-of-residence. San Juan, PR is excluded (BEA county accounts do not",
        "cover Puerto Rico); it would not make the top 30 by population.",
        "Generated by `scripts/metro_gos_pi_ratio.py`.",
    ]
    md_path.write_text("\n".join(lines) + "\n")
    print(f"wrote {csv_path} and {md_path}")
    print(top30[["title", "pop", "gos", "pi", "gos_pi"]].to_string())


if __name__ == "__main__":
    main()
