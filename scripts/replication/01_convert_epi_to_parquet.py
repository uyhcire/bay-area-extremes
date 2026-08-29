#!/usr/bin/env python3
"""Convert EPI CPS-ORG .dta files (inside the downloaded zip) to lean parquet.

Extracts one year at a time from data/raw/replication/epi_cpsorg_1979_2026.zip,
keeps only the columns needed for the college-wage-premium replication, and
deletes the intermediate .dta to conserve disk.
"""
import os
import subprocess
import sys
import zipfile

import pyreadstat

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
RAW = os.path.join(ROOT, "data", "raw", "replication")
ZIP = os.path.join(RAW, "epi_cpsorg_1979_2026.zip")
OUT = os.path.join(RAW, "parquet")
TMP = os.path.join(RAW, "extracted")

# Columns needed (not every column exists in every year; filtered per file)
WANT = [
    "year", "month", "age", "female", "wbhao", "raceorig", "hispanic",
    "educ", "gradeatn", "gradecom", "gradehi",
    "wage", "wage_noadj", "weekpay", "earnhour", "a_earnhour", "a_weekpay",
    "tc_weekpay", "tc_earnhour", "paidhre",
    "orgwgt", "hoursu1", "hoursuorg", "hourslw1",
    "occ18", "occ10", "occ00", "occ90", "occ80", "occ70", "docc03",
    "ind17", "ind22", "ind12", "ind02", "ind90", "ind80", "dind03",
    "cow1", "selfemp", "selfinc", "emp", "lfstat", "minsamp",
]

os.makedirs(OUT, exist_ok=True)
os.makedirs(TMP, exist_ok=True)

zf = zipfile.ZipFile(ZIP)
names = sorted(zf.namelist())
for name in names:
    stem = os.path.splitext(os.path.basename(name))[0]
    dest = os.path.join(OUT, stem + ".parquet")
    if os.path.exists(dest):
        print("skip", stem, flush=True)
        continue
    dta = os.path.join(TMP, os.path.basename(name))
    if not os.path.exists(dta):
        zf.extract(name, TMP)
    _, meta = pyreadstat.read_dta(dta, row_limit=1)
    cols = [c for c in WANT if c in meta.column_names]
    df, _ = pyreadstat.read_dta(dta, usecols=cols)
    df.to_parquet(dest, index=False)
    os.remove(dta)
    print("done", stem, len(df), "rows", flush=True)

print("ALL DONE")
