#!/usr/bin/env python3
"""12_comparison_series.py -- comparison price / premium / population series.

Writes health-income-side/data/inputs/comparison_series.csv (long format:
series_id, year, value, units, source_url) with ANNUAL values 1997-latest.

Sources (all public, no key):
  * BLS public API v2, unregistered (annualaverage=true -> period M13):
      CUUR0000SA0, CUUR0000SAM, CUUR0000SAM2, CUUR0000SEMF01, CUUR0000SEMD,
      PCU622110622110, PCU621111621111
    (fred.stlouisfed.org timed out and download.bls.gov flat files returned
     HTTP 403 "Access Denied" for the generic User-Agent on 2026-11-27, so the
     API is used. Unregistered limit: 25 queries/day, 10 years/query -> the
     three raw JSON responses are cached and only re-fetched with --refresh.)
  * KFF Employer Health Benefits Survey 2026, Section 1 tables workbook,
    Figure 1.12 "Average Annual Premiums for Single and Family Coverage,
    1999-2026".
  * BEA NIPA flat file (already on disk): B230RC midperiod population.

Every value is read from a downloaded file; nothing is interpolated or filled.
Run:  python3 -I health-income-side/code/12_comparison_series.py [--refresh]
"""
import csv
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _xlsx_min import read_xlsx  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "data", "raw", "health_income", "misc")
BEA_NIPA = os.path.join(ROOT, "data", "raw", "health_income", "bea", "NipaDataA.txt")
OUT = os.path.join(ROOT, "health-income-side", "data", "inputs", "comparison_series.csv")
UA = "Mozilla/5.0 research-script"
Y0 = 1997

BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_SERIES = {
    # index base periods are NOT in the API payload (unregistered API returns no
    # catalog metadata), so units deliberately do not assert a base period.
    "CUUR0000SA0": "index, NSA, annual avg (CPI-U all items, U.S. city average)",
    "CUUR0000SAM": "index, NSA, annual avg (CPI-U medical care)",
    "CUUR0000SAM2": "index, NSA, annual avg (CPI-U medical care services)",
    "CUUR0000SEMF01": "index, NSA, annual avg (CPI-U prescription drugs)",
    "CUUR0000SEMD": "index, NSA, annual avg (CPI-U hospital and related services)",
    "PCU622110622110": "index, NSA, annual avg (PPI industry: general medical and surgical hospitals)",
    "PCU621111621111": "index, NSA, annual avg (PPI industry: offices of physicians, except mental health)",
}
BLS_WINDOWS = [(1997, 2006), (2007, 2016), (2017, 2026)]

KFF_URL = "https://files.kff.org/attachment/Tables-EHBS-2026-Section-01.xlsx"
KFF_FILE = os.path.join(RAW, "kff", "Tables-EHBS-2026-Section-01.xlsx")
KFF_SHEET = "Figure 1.12"


def curl(args, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    code = subprocess.run(
        ["curl", "-sL", "-m", "90", "-A", UA, "-o", tmp, "-w", "%{http_code}"] + args,
        capture_output=True, text=True).stdout.strip()
    if code != "200":
        if os.path.exists(tmp):
            os.remove(tmp)
        raise RuntimeError("HTTP %s for %s" % (code, args[-1]))
    os.replace(tmp, dest)


def bls_rows(refresh):
    rows = []
    for a, b in BLS_WINDOWS:
        dest = os.path.join(RAW, "bls", "bls_api_%d_%d.json" % (a, b))
        if refresh or not os.path.exists(dest):
            body = json.dumps({"seriesid": list(BLS_SERIES), "startyear": str(a),
                               "endyear": str(b), "annualaverage": True})
            curl(["-X", "POST", "-H", "Content-Type: application/json", "-d", body, BLS_API], dest)
        d = json.load(open(dest))
        if d.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError("BLS API: %s %s" % (d.get("status"), d.get("message")))
        for s in d["Results"]["series"]:
            sid = s["seriesID"]
            for x in s["data"]:
                # M13 = BLS-published annual average; monthly values are ignored
                if x["period"] == "M13" and int(x["year"]) >= Y0:
                    rows.append((sid, int(x["year"]), float(x["value"]), BLS_SERIES[sid],
                                 BLS_API + " (POST seriesid=%s, annualaverage=true, period M13)" % sid))
    return rows


def kff_rows(refresh):
    if refresh or not os.path.exists(KFF_FILE):
        curl([KFF_URL], KFF_FILE)
    sheet = read_xlsx(KFF_FILE)[KFF_SHEET]
    title = sheet[1][0]
    if "Average Annual Premiums for Single and Family Coverage" not in title:
        raise RuntimeError("unexpected KFF sheet title: %r" % title)
    hdr = [str(c).strip() if c else "" for c in sheet[3]]
    if hdr[1:3] != ["Single Coverage", "Family Coverage"]:
        raise RuntimeError("unexpected KFF header: %r" % hdr)
    rows = []
    for r in sheet[4:]:
        if not r or not r[0] or not re.fullmatch(r"\d{4}", str(r[0]).strip()):
            continue
        yr = int(str(r[0]).strip())
        for sid, cell in (("KFF_EHBS_PREMIUM_SINGLE", r[1]), ("KFF_EHBS_PREMIUM_FAMILY", r[2])):
            # cells look like "$2,439*" (* = significantly different from prior year)
            val = float(re.sub(r"[^0-9.]", "", str(cell)))
            rows.append((sid, yr, val,
                         "USD per year, average annual premium (employer+worker), covered workers",
                         KFF_URL + " (sheet '%s')" % KFF_SHEET))
    return rows


def pop_rows():
    rows = []
    if not os.path.exists(BEA_NIPA):
        print("WARN: %s missing - population skipped" % BEA_NIPA)
        return rows
    with open(BEA_NIPA, newline="") as f:
        for r in csv.reader(f):
            if r and r[0] == "B230RC" and re.fullmatch(r"\d{4}", r[1]) and int(r[1]) >= Y0:
                rows.append(("BEA_B230RC_POP", int(r[1]), float(r[2].replace(",", "")),
                             "thousands of persons (midperiod population, NIPA T7.1 line 18)",
                             "https://apps.bea.gov/national/Release/TXT/NipaDataA.txt (series B230RC)"))
    return rows


def main():
    refresh = "--refresh" in sys.argv
    rows = bls_rows(refresh) + kff_rows(refresh) + pop_rows()
    rows.sort(key=lambda r: (r[0], r[1]))
    seen = set()
    for r in rows:
        if (r[0], r[1]) in seen:
            raise RuntimeError("duplicate %s %s" % r[:2])
        seen.add((r[0], r[1]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series_id", "year", "value", "units", "source_url"])
        w.writerows(rows)
    by = {}
    for r in rows:
        by.setdefault(r[0], []).append(r[1])
    for sid in sorted(by):
        ys = by[sid]
        gaps = sorted(set(range(min(ys), max(ys) + 1)) - set(ys))
        print("%-26s %d-%d n=%d%s" % (sid, min(ys), max(ys), len(ys), "  MISSING %s" % gaps if gaps else ""))
    print("wrote", OUT, len(rows), "rows")


if __name__ == "__main__":
    main()
