#!/usr/bin/env python3
"""Rank the largest U.S. Combined Statistical Areas (CSAs) by partisan lean.

Joins county-level presidential returns to the Census county->CSA crosswalk,
aggregates votes up to each CSA, and ranks the N most populous CSAs by their
two-party Democratic vote share.

Inputs (download first):
    scripts/download_csa_geography.sh        # crosswalk + CSA populations
    scripts/download_election_returns.sh     # county presidential returns

Usage:
    scripts/rank_csa_partisanship.py [--year 2024] [--top 20] [--out [PATH]]

Prints the ranked table; pass --out to also save it as CSV (a bare --out writes
findings/csa_partisanship_<year>.csv). A committed write-up lives in findings/.

Two-party Dem share = votes_dem / (votes_dem + votes_gop). Margin = (dem - gop)
/ total_votes. These are whole CSAs (urban core + exurbs), so they run more
Republican than the central city alone.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

RAW = Path("data/raw")
GEO = RAW / "csa_geography"
RETURNS = RAW / "election_returns"


def load_crosswalk() -> pd.DataFrame:
    d = pd.read_excel(GEO / "delineation_list1_2023.xlsx", skiprows=2, dtype=str)
    d = d.dropna(subset=["CSA Code"]).copy()
    d["fips"] = d["FIPS State Code"].str.zfill(2) + d["FIPS County Code"].str.zfill(3)
    return d[["fips", "CSA Code", "CSA Title"]].drop_duplicates()


def load_top_csas(top: int) -> pd.DataFrame:
    df = pd.read_csv(GEO / "csa_population_2023.csv", encoding="latin-1", dtype={"CSA": str})
    csa = df[df["LSAD"] == "Combined Statistical Area"].copy()
    return csa.sort_values("POPESTIMATE2023", ascending=False).head(top)[
        ["CSA", "NAME", "POPESTIMATE2023"]
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", default="2024", help="presidential election year (default: 2024)")
    ap.add_argument("--top", type=int, default=20, help="number of largest CSAs to rank (default: 20)")
    ap.add_argument(
        "--out",
        nargs="?",
        const="",
        help="write the ranked table as CSV; bare --out defaults to findings/csa_partisanship_<year>.csv",
    )
    args = ap.parse_args()
    if args.out == "":
        args.out = f"findings/csa_partisanship_{args.year}.csv"

    returns_file = RETURNS / f"county_presidential_{args.year}.csv"
    if not returns_file.exists():
        sys.exit(f"Missing {returns_file}. Run scripts/download_election_returns.sh {args.year}")

    xwalk = load_crosswalk()
    top = load_top_csas(args.top)

    e = pd.read_csv(returns_file, dtype={"county_fips": str})
    e["county_fips"] = e["county_fips"].str.zfill(5)

    m = e.merge(xwalk, left_on="county_fips", right_on="fips", how="left")

    # Coverage check: every county a top CSA expects should match the returns.
    expected = xwalk[xwalk["CSA Code"].isin(top["CSA"])].groupby("CSA Code")["fips"].nunique()
    matched = m[m["CSA Code"].isin(top["CSA"])].groupby("CSA Code")["county_fips"].nunique()
    gaps = (expected - matched).fillna(expected)
    gaps = gaps[gaps != 0]
    if len(gaps):
        print("WARNING: counties in the crosswalk with no match in the returns file:", file=sys.stderr)
        for code, n in gaps.items():
            name = top.loc[top["CSA"] == code, "NAME"].iloc[0] if (top["CSA"] == code).any() else code
            print(f"  {name}: {int(n)} county/ies unmatched (often Connecticut FIPS vintage)", file=sys.stderr)

    agg = m.groupby("CSA Code").agg(
        dem=("votes_dem", "sum"), gop=("votes_gop", "sum"), tot=("total_votes", "sum")
    ).reset_index()

    res = top.merge(agg, left_on="CSA", right_on="CSA Code", how="left")
    res["dem_share_2party"] = res["dem"] / (res["dem"] + res["gop"]) * 100
    res["dem_margin"] = (res["dem"] - res["gop"]) / res["tot"] * 100
    res = res.sort_values("dem_share_2party", ascending=False).reset_index(drop=True)
    res.insert(0, "rank", res.index + 1)

    cols = ["rank", "NAME", "POPESTIMATE2023", "dem_share_2party", "dem_margin", "tot"]
    print(f"\n{args.top} largest U.S. CSAs by two-party Democratic vote share ({args.year} presidential)\n")
    print(
        res[cols].to_string(
            index=False,
            formatters={
                "dem_share_2party": "{:.1f}".format,
                "dem_margin": "{:+.1f}".format,
                "POPESTIMATE2023": "{:,.0f}".format,
                "tot": "{:,.0f}".format,
            },
        )
    )

    if args.out:
        res[cols].to_csv(args.out, index=False)
        print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
