#!/usr/bin/env python3
"""Build a CPS ASEC person extract with IPUMS CPS variable names and codes.

Output: data/raw/census_cps_asec/cps_asec_harmonized.parquet with columns
YEAR, ASECWT, AGE, SEX, EDUC, INCWAGE, MARST, WKSWORK1, UHRSWORKLY.

Two sources:

  --source census (default)  Census Bureau public-use files fetched by
                             scripts/download_cps_asec.sh. Census variables
                             are recoded to their IPUMS equivalents:
                               MARSUPWT/100 -> ASECWT   A_AGE   -> AGE
                               A_SEX        -> SEX      A_HGA   -> EDUC
                               WSAL_VAL     -> INCWAGE  A_MARITL-> MARST
                               WKSWORK      -> WKSWORK1 HRSWK   -> UHRSWORKLY
  --source ipums             An IPUMS CPS extract (.xml DDI + .dat.gz) under
                             data/raw/ipums_cps/, from
                             scripts/download_ipums.sh <samples> cps.

Census codes NIU as 0 for WSAL_VAL / HRSWK, where IPUMS uses 99999999 / 999;
the analysis recodes the IPUMS NIU values to 0, so both sources agree.
"""
import argparse
import glob
import gzip
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

RAW = "data/raw/census_cps_asec"
OUT = os.path.join(RAW, "cps_asec_harmonized.parquet")

# Fixed-width person-record layout (1-based start column, width) shared by the
# 2001 and 2010 files: techdocs cpsmar01.pdf / cpsmar10.pdf.
FWF_PERSON = {
    "A_AGE": (15, 2),
    "A_MARITL": (17, 1),
    "A_SEX": (20, 1),
    "A_HGA": (22, 2),
    "MARSUPWT": (66, 8),   # 2 implied decimals
    "WKSWORK": (171, 2),
    "HRSWK": (181, 2),
    "WSAL_VAL": (243, 6),
}
FWF_FILES = {2001: "chip2001pub.cps.gz", 2010: "asec2010_pubuse.dat.gz"}
CSV_FILES = {
    2019: ("asecpub19csv.zip", "cpspb/asec/prod/data/2019/pppub19.csv"),
    2025: ("asecpub25csv.zip", "pppub25.csv"),
}

# Census A_HGA -> IPUMS EDUC.
HGA_TO_EDUC = {0: 1, 31: 2, 32: 10, 33: 20, 34: 30, 35: 40, 36: 50, 37: 60,
               38: 71, 39: 73, 40: 81, 41: 91, 42: 92, 43: 111, 44: 123,
               45: 124, 46: 125}
# Census A_MARITL -> IPUMS MARST (1 spouse present, 2 spouse absent,
# 3 separated, 4 divorced, 5 widowed, 6 never married).
MARITL_TO_MARST = {1: 1, 2: 1, 3: 2, 4: 5, 5: 4, 6: 3, 7: 6}


def read_fwf_persons(path: str) -> pd.DataFrame:
    with gzip.open(path, "rt", encoding="latin-1") as fh:
        lines = [ln for ln in fh if ln[0] == "3"]  # person records
    cols = {name: [int(ln[s - 1:s - 1 + w]) for ln in lines]
            for name, (s, w) in FWF_PERSON.items()}
    return pd.DataFrame(cols)


def read_csv_persons(zpath: str, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(zpath) as z, z.open(member) as fh:
        return pd.read_csv(io.TextIOWrapper(fh), usecols=list(FWF_PERSON))


def harmonize(df: pd.DataFrame, survey_year: int) -> pd.DataFrame:
    return pd.DataFrame({
        "YEAR": survey_year,
        "ASECWT": df["MARSUPWT"].astype(float) / 100.0,
        "AGE": df["A_AGE"].astype(int),
        "SEX": df["A_SEX"].astype(int),
        "EDUC": df["A_HGA"].map(HGA_TO_EDUC).astype(int),
        "INCWAGE": df["WSAL_VAL"].astype(float),
        "MARST": df["A_MARITL"].map(MARITL_TO_MARST).fillna(9).astype(int),
        "WKSWORK1": df["WKSWORK"].astype(int),
        "UHRSWORKLY": df["HRSWK"].astype(int),
    })


def build_census() -> pd.DataFrame:
    parts = []
    for year, fname in FWF_FILES.items():
        parts.append(harmonize(read_fwf_persons(os.path.join(RAW, fname)), year))
    for year, (zname, member) in CSV_FILES.items():
        parts.append(harmonize(read_csv_persons(os.path.join(RAW, zname), member), year))
    return pd.concat(parts, ignore_index=True)


def build_ipums() -> pd.DataFrame:
    from ipumspy import readers
    xmls = sorted(glob.glob("data/raw/ipums_cps/*.xml"))
    if not xmls:
        sys.exit("No IPUMS CPS extract in data/raw/ipums_cps/.")
    ddi = readers.read_ipums_ddi(xmls[-1])
    df = readers.read_microdata(ddi, xmls[-1].replace(".xml", ".dat.gz"))
    keep = ["YEAR", "ASECWT", "AGE", "SEX", "EDUC", "INCWAGE", "MARST",
            "WKSWORK1", "UHRSWORKLY"]
    return df[keep].dropna(subset=["ASECWT"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--source", choices=["census", "ipums"], default="census")
    args = ap.parse_args()
    df = build_census() if args.source == "census" else build_ipums()
    df.attrs["source"] = args.source
    df.to_parquet(OUT, index=False)
    print(f"Wrote {OUT}: {len(df):,} persons ({args.source})")
    print(df.groupby("YEAR").agg(n=("AGE", "size"), pop_m=("ASECWT", lambda w: w.sum() / 1e6)))


if __name__ == "__main__":
    main()
