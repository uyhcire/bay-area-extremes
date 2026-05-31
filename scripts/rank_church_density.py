#!/usr/bin/env python3
"""
Rank MSAs by a *proxy* for church attendance: the density of religious
organizations (NAICS 8131) from Census County Business Patterns (CBP), per
capita.

IMPORTANT CAVEAT: The U.S. Census Bureau is legally barred (13 U.S.C. 221) from
requiring religious-affiliation responses, so there is no Census measure of
actual church *attendance*. This script instead counts the *supply* of
religious-organization establishments and their employment per capita -- a
density proxy, not a behavioral attendance rate.

Inputs (both keyless Census bulk files, see CLAUDE.md):
  - data/raw/cbp_2022/cbp22msa.txt                  (CBP, establishments by CBSA x NAICS)
  - data/raw/popest_metro/cbsa-est2024-alldata.csv  (CBSA population estimates)

Scope: the 20 most populous Metropolitan Statistical Areas + the San Jose MSA.

Output: prints a ranked table and writes data/processed/church_density_msa.csv
"""
import csv
import os

CBP = "data/raw/cbp_2022/cbp22msa.txt"
POP = "data/raw/popest_metro/cbsa-est2024-alldata.csv"
OUT = "data/processed/church_density_msa.csv"

POP_YEAR = "POPESTIMATE2022"  # match the CBP 2022 data year
SAN_JOSE = "41940"            # San Jose-Sunnyvale-Santa Clara, CA
RELIGIOUS_NAICS = "8131//"    # Religious Organizations (4-digit aggregate)


def load_population():
    """Return {cbsa: (name, pop)} for whole-MSA rows only."""
    msas = {}
    with open(POP, newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            # Whole-CBSA total row: no metro division, no county component.
            if r["MDIV"].strip() or r["STCOU"].strip():
                continue
            if r["LSAD"].strip() != "Metropolitan Statistical Area":
                continue
            try:
                pop = int(r[POP_YEAR])
            except ValueError:
                continue
            msas[r["CBSA"].strip()] = (r["NAME"].strip(), pop)
    return msas


def load_religious_establishments():
    """Return {cbsa: (est, emp)} for NAICS 8131 religious organizations."""
    out = {}
    with open(CBP, newline="", encoding="latin-1") as f:
        for r in csv.DictReader(f):
            if r["naics"] != RELIGIOUS_NAICS:
                continue
            try:
                est = int(r["est"])
            except ValueError:
                est = 0
            try:
                emp = int(r["emp"])
            except ValueError:
                emp = 0  # suppressed ('N') -> reported as 0; emp is unreliable, est is the count
            out[r["msa"].strip()] = (est, emp)
    return out


def main():
    pops = load_population()
    rel = load_religious_establishments()

    # Top 20 MSAs by population + San Jose.
    ranked_by_pop = sorted(pops.items(), key=lambda kv: kv[1][1], reverse=True)
    selected = [c for c, _ in ranked_by_pop[:20]]
    if SAN_JOSE not in selected and SAN_JOSE in pops:
        selected.append(SAN_JOSE)

    rows = []
    for cbsa in selected:
        name, pop = pops[cbsa]
        est, emp = rel.get(cbsa, (0, 0))
        per100k = est / pop * 100_000
        emp_per100k = emp / pop * 100_000
        rows.append({
            "cbsa": cbsa,
            "msa": name,
            "population_2022": pop,
            "religious_orgs": est,
            "orgs_per_100k": round(per100k, 2),
            "religious_emp": emp,
            "emp_per_100k": round(emp_per100k, 1),
        })

    rows.sort(key=lambda x: x["orgs_per_100k"], reverse=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Pretty print.
    print(f"\nReligious-organization density (NAICS 8131) by MSA -- proxy for"
          f" church attendance\nCBP 2022 establishments / {POP_YEAR} population."
          f" NOT a measured attendance rate.\n")
    hdr = f"{'#':>2}  {'MSA':<46}{'pop':>11}{'orgs':>7}{'per 100k':>10}{'emp/100k':>10}"
    print(hdr)
    print("-" * len(hdr))
    for i, x in enumerate(rows, 1):
        short = x["msa"].rsplit(",", 1)[0][:44]
        sj = "  <- San Jose" if x["cbsa"] == SAN_JOSE else ""
        print(f"{i:>2}  {short:<46}{x['population_2022']:>11,}{x['religious_orgs']:>7}"
              f"{x['orgs_per_100k']:>10.2f}{x['emp_per_100k']:>10.1f}{sj}")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()
