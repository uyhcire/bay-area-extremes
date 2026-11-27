#!/usr/bin/env python3
"""
10_hcris_hospital_financials.py

Annual national hospital financials from CMS Medicare hospital cost reports
(HCRIS), forms CMS-2552-96 (HOSPFY<YYYY>.zip) and CMS-2552-10
(HOSP10FY<YYYY>.zip), from https://downloads.cms.gov/files/hcris/ .

Run (downloads are untrusted data -> isolated mode, run from the repo root or
anywhere; never from inside the download dir):

    python3 -I health-income-side/code/10_hcris_hospital_financials.py

Outputs
  data/raw/health_income/hcris/                 raw zips (git-ignored), manifest,
                                                per-zip cell extracts (cache)
  health-income-side/data/inputs/hcris_hospital_financials.csv
  data/raw/health_income/hcris/hcris_qa_stats.json     (QA numbers quoted in hcris_NOTES.md)
  data/raw/health_income/hcris/extract/hcris_report_level_used.csv  (report-level audit file)

Main columns are CALENDAR-YEAR-PRORATED: each report's dollar amounts are
allocated to calendar years in proportion to the days of its reporting period
that fall in each year. *_fyend columns assign the whole report to the calendar
year in which its fiscal period ends. See hcris_NOTES.md for all rules.

stdlib + pandas/numpy only.
"""
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(REPO, "data", "raw", "health_income", "hcris")
EXTRACT = os.path.join(RAW, "extract")
OUT_DIR = os.path.join(REPO, "health-income-side", "data", "inputs")
OUT_CSV = os.path.join(OUT_DIR, "hcris_hospital_financials.csv")
OUT_QA = os.path.join(RAW, "hcris_qa_stats.json")      # QA numbers quoted in hcris_NOTES.md
MANIFEST = os.path.join(RAW, "download_manifest.csv")

BASE_URL = "https://downloads.cms.gov/files/hcris/"
UA = "Mozilla/5.0 research-script"

# (form, file-year) -> zip name.  File year = federal fiscal year (Oct-Sep) in
# which the cost-report period BEGINS.
FILES = [("96", y, "HOSPFY%d.zip" % y) for y in range(1995, 2012)] + \
        [("10", y, "HOSP10FY%d.zip" % y) for y in range(2010, 2027)]

RPT_COLS = ["rpt_rec_num", "prvdr_ctrl_type_cd", "prvdr_num", "npi",
            "rpt_stus_cd", "fy_bgn_dt", "fy_end_dt", "proc_dt", "initl_rpt_sw",
            "last_rpt_sw", "trnsmtl_num", "fi_num", "adr_vndr_cd",
            "fi_creat_dt", "util_cd", "npr_dt", "spec_ind", "fi_rcpt_dt"]

# Cells kept from the NMRC file: worksheet -> (line filter or None, column filter or None)
# Line/column codes are zero-padded: line = 5 digits (LLLSS), column = 4 digits
# in 2552-96 files and 5 digits in 2552-10 files.
KEEP = {
    "96": {
        "G300000": (None, {"0100"}),            # statement of revenues & expenses
        "S200000": ({"01800"}, {"0100"}),       # type of control
        "A000000": ({"10100"}, {"0100"}),       # Wkst A total, col 1 salaries
        "A700003": ({"00500"}, {"0900", "1100"}),  # A-7 Pt III total: depreciation, interest
    },
    "10": {
        "G300000": (None, {"00100"}),
        "S200001": ({"02100"}, {"00100"}),
        "A000000": ({"20000"}, {"00100"}),
        "A700003": ({"00300"}, {"00900", "01100"}),
    },
}

# G-3 line map (5-digit line codes) per form
G3 = {
    "96": dict(npr="00300", opex="00400", oth_inc="02500", oth_exp="03000",
               ni="03100", oi_first=600, oi_last=2499, oe_first=2700, oe_last=2999),
    "10": dict(npr="00300", opex="00400", oth_inc="02500", oth_exp="02800",
               ni="02900", oi_first=600, oi_last=2499, oe_first=2700, oe_last=2799),
}
A_SAL = {"96": "10100", "10": "20000"}
A7_TOT = {"96": "00500", "10": "00300"}

# Type-of-control codes (same list on 2552-96 S-2 line 18 and 2552-10 S-2 Pt I
# line 21; also RPT.PRVDR_CTRL_TYPE_CD)
OWN = {1: "nonprofit", 2: "nonprofit",
       3: "forprofit", 4: "forprofit", 5: "forprofit", 6: "forprofit",
       7: "government_federal",
       8: "government_nonfederal", 9: "government_nonfederal",
       10: "government_nonfederal", 11: "government_nonfederal",
       12: "government_nonfederal", 13: "government_nonfederal"}
CLASSES = ["nonprofit", "forprofit", "government_nonfederal",
           "government_federal", "unknown"]

# report status precedence for dedup (higher = preferred):
# 1 as submitted < 5 amended < 2 settled w/o audit < 3 settled with audit < 4 reopened
STATUS_RANK = {1: 1, 5: 2, 2: 3, 3: 4, 4: 5}

A7_MIN_COVERAGE = 0.90

MEASURES = ["net_patient_revenue", "total_operating_expenses", "other_income",
            "total_revenue", "net_income", "net_income_from_patients",
            "contributions_donations", "investment_income", "govt_appropriations",
            "depreciation", "interest_expense_capital_a7", "salaries"]


# ----------------------------------------------------------------------------
# download
# ----------------------------------------------------------------------------
def _request(url, method="GET"):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    return urllib.request.urlopen(req, timeout=300)   # default TLS verification


def download_all():
    os.makedirs(RAW, exist_ok=True)
    man = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, newline="") as f:
            for r in csv.DictReader(f):
                man[r["file"]] = r
    failed = []
    for form, year, name in FILES:
        path = os.path.join(RAW, name)
        url = BASE_URL + name
        if os.path.exists(path) and os.path.getsize(path) > 0:
            if name not in man or man[name].get("bytes") != str(os.path.getsize(path)):
                # file was already present: record remote vintage via HEAD
                lm, note = "", "pre-existing file; Last-Modified from HEAD"
                try:
                    with _request(url, "HEAD") as r:
                        lm = r.headers.get("Last-Modified", "")
                        if r.headers.get("Content-Length") != str(os.path.getsize(path)):
                            note += " (remote size differs from local!)"
                except Exception as e:      # noqa
                    note = "pre-existing file; HEAD failed: %r" % (e,)
                man[name] = dict(file=name, url=url, bytes=str(os.path.getsize(path)),
                                 last_modified=lm, note=note)
            continue
        ok = False
        for attempt in range(4):
            try:
                with _request(url) as r, open(path + ".part", "wb") as out:
                    lm = r.headers.get("Last-Modified", "")
                    while True:
                        b = r.read(1 << 20)
                        if not b:
                            break
                        out.write(b)
                os.replace(path + ".part", path)
                man[name] = dict(file=name, url=url, bytes=str(os.path.getsize(path)),
                                 last_modified=lm, note="downloaded by script")
                print("downloaded", name, os.path.getsize(path), flush=True)
                ok = True
                break
            except urllib.error.HTTPError as e:
                print("HTTP %s for %s" % (e.code, url), flush=True)
                if e.code == 404:
                    break
                time.sleep(3 * (attempt + 1))
            except Exception as e:  # noqa
                print("error %r for %s" % (e, url), flush=True)
                time.sleep(3 * (attempt + 1))
        if not ok:
            failed.append(name)
            if os.path.exists(path + ".part"):
                os.remove(path + ".part")
    with open(MANIFEST, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "bytes", "last_modified", "note"])
        w.writeheader()
        for _, _, name in FILES:
            if name in man:
                w.writerow(man[name])
    return failed


# ----------------------------------------------------------------------------
# extract needed cells from each zip (streamed; cached)
# ----------------------------------------------------------------------------
def extract_one(args):
    form, year, name = args
    zpath = os.path.join(RAW, name)
    stem = name[:-4]
    out_rpt = os.path.join(EXTRACT, stem + "_rpt.csv")
    out_num = os.path.join(EXTRACT, stem + "_cells.csv")
    if not os.path.exists(zpath):
        return name, "missing"
    if (os.path.exists(out_rpt) and os.path.exists(out_num)
            and os.path.getmtime(out_num) >= os.path.getmtime(zpath)):
        return name, "cached"
    keep = KEEP[form]
    with zipfile.ZipFile(zpath) as z:
        members = {m.lower(): m for m in z.namelist()}
        rpt = [m for k, m in members.items() if k.endswith("_rpt.csv")]
        nmrc = [m for k, m in members.items() if k.endswith("_nmrc.csv")]
        if len(rpt) != 1 or len(nmrc) != 1:
            return name, "unexpected members %r" % (z.namelist(),)
        with z.open(rpt[0]) as f, open(out_rpt + ".tmp", "wb") as o:
            o.write(f.read())
        n = 0
        with z.open(nmrc[0]) as f, open(out_num + ".tmp", "w") as o:
            for line in io.TextIOWrapper(f, encoding="latin-1", newline=""):
                p = line.rstrip("\r\n").split(",")
                if len(p) != 5:
                    continue
                k = keep.get(p[1])
                if k is None:
                    continue
                if k[0] is not None and p[2] not in k[0]:
                    continue
                if k[1] is not None and p[3] not in k[1]:
                    continue
                o.write(",".join(p) + "\n")
                n += 1
    os.replace(out_rpt + ".tmp", out_rpt)
    os.replace(out_num + ".tmp", out_num)
    return name, "extracted %d cells" % n


# ----------------------------------------------------------------------------
# build report-level table
# ----------------------------------------------------------------------------
def load_reports():
    frames = []
    for form, year, name in FILES:
        stem = name[:-4]
        p_rpt = os.path.join(EXTRACT, stem + "_rpt.csv")
        p_num = os.path.join(EXTRACT, stem + "_cells.csv")
        if not os.path.exists(p_rpt):
            continue
        rpt = pd.read_csv(p_rpt, header=None, names=RPT_COLS, dtype=str,
                          encoding="latin-1", keep_default_na=False)
        rpt["form"] = form
        rpt["file_year"] = year
        if os.path.getsize(p_num) > 0:
            num = pd.read_csv(p_num, header=None,
                              names=["rpt_rec_num", "wksht", "line", "col", "val"],
                              dtype={"rpt_rec_num": str, "wksht": str, "line": str,
                                     "col": str, "val": float})
        else:
            num = pd.DataFrame(columns=["rpt_rec_num", "wksht", "line", "col", "val"])
        num = num.drop_duplicates(["rpt_rec_num", "wksht", "line", "col"], keep="last")
        g = G3[form]
        g3 = num[num.wksht == "G300000"]
        ln = g3.line.astype(int)

        def cell(df, line):
            return df[df.line == line].set_index("rpt_rec_num").val

        cols = {
            "g3_npr": cell(g3, g["npr"]),
            "g3_opex": cell(g3, g["opex"]),
            "g3_oth_inc_tot": cell(g3, g["oth_inc"]),
            "g3_oth_exp_tot": cell(g3, g["oth_exp"]),
            "g3_ni": cell(g3, g["ni"]),
            "g3_oth_inc_sum": g3[(ln >= g["oi_first"]) & (ln <= g["oi_last"])]
            .groupby("rpt_rec_num").val.sum(),
            "g3_oth_exp_sum": g3[(ln >= g["oe_first"]) & (ln <= g["oe_last"])]
            .groupby("rpt_rec_num").val.sum(),
            "g3_ncells": g3.groupby("rpt_rec_num").val.size(),
            # G-3 components (same line numbers on both forms); a line and any
            # sublines (e.g. 6.01) are summed
            "g3_line5": cell(g3, "00500"),
            "contributions_donations": g3[ln // 100 == 6].groupby("rpt_rec_num").val.sum(),
            "investment_income": g3[ln // 100 == 7].groupby("rpt_rec_num").val.sum(),
            "govt_appropriations": g3[ln // 100 == 23].groupby("rpt_rec_num").val.sum(),
            "g3_subline_6_7_23_n": g3[((ln // 100).isin([6, 7, 23])) & (ln % 100 != 0)]
            .groupby("rpt_rec_num").val.size(),
            "salaries": cell(num[num.wksht == "A000000"], A_SAL[form]),
        }
        a7 = num[(num.wksht == "A700003") & (num.line == A7_TOT[form])]
        cols["depreciation"] = a7[a7.col.astype(int) == 900].set_index("rpt_rec_num").val
        cols["interest_expense_capital_a7"] = a7[a7.col.astype(int) == 1100].set_index("rpt_rec_num").val
        s2 = num[num.wksht.isin(["S200000", "S200001"])]
        cols["s2_ctrl"] = s2.set_index("rpt_rec_num").val
        vals = pd.DataFrame(cols)
        rpt = rpt.merge(vals, how="left", left_on="rpt_rec_num", right_index=True)
        frames.append(rpt)
    return pd.concat(frames, ignore_index=True)


def dedup(df):
    """Within a provider, drop any report whose period overlaps a preferred
    (kept) report by more than 30 days. Preference: status rank, then 2552-10
    over 2552-96, then later PROC_DT, then higher RPT_REC_NUM."""
    df = df.sort_values(["prvdr_num", "pref_key"], ascending=[True, False])
    keep = np.ones(len(df), dtype=bool)
    b = df.bgn.values.astype("datetime64[D]").astype(np.int64)
    e = df.end.values.astype("datetime64[D]").astype(np.int64)
    prv = df.prvdr_num.values
    start = 0
    n = len(df)
    while start < n:
        stop = start
        while stop < n and prv[stop] == prv[start]:
            stop += 1
        kept = []
        for i in range(start, stop):
            ok = True
            for j in kept:
                ov = min(e[i], e[j]) - max(b[i], b[j]) + 1
                if ov > 30:
                    ok = False
                    break
            if ok:
                kept.append(i)
            else:
                keep[i] = False
        start = stop
    df = df.copy()
    df["dedup_keep"] = keep
    return df


def main():
    os.makedirs(EXTRACT, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    qa = {}

    failed = download_all()
    qa["download_failed"] = failed
    if failed:
        print("WARNING: could not download:", failed)

    with ProcessPoolExecutor(max_workers=min(6, os.cpu_count() or 2)) as ex:
        for name, status in ex.map(extract_one, FILES):
            print("extract", name, status, flush=True)

    df = load_reports()
    qa["n_rpt_rows_raw"] = int(len(df))
    qa["n_rpt_rows_by_file"] = {"%s_%d" % (f, y): int(n) for (f, y), n in
                                df.groupby(["form", "file_year"]).size().items()}

    # ---- dates
    df["bgn"] = pd.to_datetime(df.fy_bgn_dt, format="%m/%d/%Y", errors="coerce")
    df["end"] = pd.to_datetime(df.fy_end_dt, format="%m/%d/%Y", errors="coerce")
    df["proc"] = pd.to_datetime(df.proc_dt, format="%m/%d/%Y", errors="coerce")
    df["days"] = (df.end - df.bgn).dt.days + 1
    bad_dates = df.bgn.isna() | df.end.isna() | (df.days < 1) | (df.days > 550)
    qa["dropped_bad_dates_n"] = int(bad_dates.sum())
    qa["dropped_bad_dates_npr"] = float(df.loc[bad_dates, "g3_npr"].sum())
    df = df[~bad_dates].copy()

    # ---- ownership (RPT field; fall back to S-2 cell)
    ctrl_rpt = pd.to_numeric(df.prvdr_ctrl_type_cd, errors="coerce")
    ctrl = ctrl_rpt.where(ctrl_rpt.isin(list(OWN)), df.s2_ctrl)
    both = ctrl_rpt.notna() & df.s2_ctrl.notna()
    qa["ctrl_rpt_vs_s2_both_present"] = int(both.sum())
    qa["ctrl_rpt_vs_s2_disagree"] = int((both & (ctrl_rpt != df.s2_ctrl)).sum())
    qa["ctrl_from_s2_fallback"] = int((~ctrl_rpt.isin(list(OWN)) & df.s2_ctrl.isin(list(OWN))).sum())
    df["ctrl"] = ctrl
    df["ownership_class"] = ctrl.map(OWN).fillna("unknown")

    # ---- dedup (before garbage filters, so that an amended/blank duplicate
    # never displaces nothing; only reports with a G-3 compete)
    df["has_g3"] = df.g3_npr.notna() & df.g3_opex.notna()
    stat = pd.to_numeric(df.rpt_stus_cd, errors="coerce").map(STATUS_RANK).fillna(0)
    recnum = pd.to_numeric(df.rpt_rec_num, errors="coerce").fillna(0)
    procn = df.proc.fillna(pd.Timestamp("1900-01-01")).dt.strftime("%Y%m%d").astype(np.int64)
    df["pref_key"] = list(zip(df.has_g3.astype(int), stat.astype(int),
                              (df.form == "10").astype(int), procn, recnum.astype(np.int64)))
    df = dedup(df)
    dd = df[~df.dedup_keep]
    qa["dedup_dropped_n"] = int(len(dd))
    qa["dedup_dropped_with_g3_n"] = int(dd.has_g3.sum())
    qa["dedup_dropped_npr"] = float(dd.g3_npr.sum())
    qa["dedup_dropped_by_form"] = {k: int(v) for k, v in dd.groupby("form").size().items()}
    # cross-form overlap diagnostics: providers/periods present in both forms
    k96 = set(zip(df[df.form == "96"].prvdr_num, df[df.form == "96"].fy_end_dt))
    k10 = set(zip(df[df.form == "10"].prvdr_num, df[df.form == "10"].fy_end_dt))
    qa["cross_form_same_provider_same_fyend"] = len(k96 & k10)
    df = df[df.dedup_keep].copy()
    qa["n_reports_after_dedup"] = int(len(df))

    # ---- derive measures
    # other income: G-3 total line; if absent, sum of component lines
    df["other_income"] = df.g3_oth_inc_tot.where(df.g3_oth_inc_tot.notna(), df.g3_oth_inc_sum)
    oth_exp = df.g3_oth_exp_tot.where(df.g3_oth_exp_tot.notna(), df.g3_oth_exp_sum)
    qa["other_income_from_component_sum_n"] = int(
        (df.has_g3 & df.g3_oth_inc_tot.isna() & df.g3_oth_inc_sum.notna()).sum())
    ni_identity = df.g3_npr - df.g3_opex + df.other_income.fillna(0) - oth_exp.fillna(0)
    ni_missing = df.has_g3 & df.g3_ni.isna()
    qa["net_income_line_blank_n"] = int(ni_missing.sum())
    qa["net_income_line_blank_identity_value_sum"] = float(ni_identity[ni_missing].sum())
    # A blank net-income line on a filed G-3 is filled from the form identity
    # (line 3 - line 4 + other income - other expenses); this is arithmetic on
    # reported cells, not an estimate.
    df["net_income"] = df.g3_ni.where(df.g3_ni.notna(), ni_identity)
    df["net_patient_revenue"] = df.g3_npr
    df["total_operating_expenses"] = df.g3_opex
    df["other_income"] = df.other_income.fillna(0.0).where(df.has_g3)
    df["total_revenue"] = df.net_patient_revenue + df.other_income
    # G-3 line 5 as reported; if blank, line 3 - line 4
    l5 = df.g3_npr - df.g3_opex
    chk = df.has_g3 & df.g3_line5.notna()
    qa["line5_blank_n"] = int((df.has_g3 & df.g3_line5.isna()).sum())
    qa["line5_differs_from_l3_minus_l4_gt2_n"] = int((chk & ((df.g3_line5 - l5).abs() > 2)).sum())
    qa["line5_minus_l3l4_sum"] = float((df.g3_line5 - l5)[chk].sum())
    df["net_income_from_patients"] = df.g3_line5.where(df.g3_line5.notna(), l5)
    for c in ["contributions_donations", "investment_income", "govt_appropriations"]:
        df[c] = df[c].fillna(0.0).where(df.has_g3)
    qa["reports_with_sublines_on_6_7_23"] = int(df.g3_subline_6_7_23_n.notna().sum())
    resid = (df.g3_ni - ni_identity)[df.has_g3 & df.g3_ni.notna()]
    qa["identity_check_n"] = int(len(resid))
    qa["identity_within_2_dollars_share"] = float((resid.abs() <= 2).mean())
    qa["identity_abs_resid_sum"] = float(resid.abs().sum())
    qa["identity_resid_sum"] = float(resid.sum())
    for f in ("96", "10"):
        r = resid[df.loc[resid.index, "form"] == f]
        qa["identity_within_2_dollars_share_form%s" % f] = float((r.abs() <= 2).mean())

    # ---- garbage filters
    no_g3 = ~df.has_g3
    qa["dropped_no_g3_n"] = int(no_g3.sum())
    qa["dropped_no_g3_by_util_cd"] = {str(k): int(v) for k, v in
                                      df[no_g3].groupby("util_cd").size().items()}
    npr, opx, ni = df.net_patient_revenue, df.total_operating_expenses, df.net_income
    g_nonpos = df.has_g3 & ((npr <= 0) | (opx <= 0))
    g_ni = df.has_g3 & ~g_nonpos & (ni.abs() > 5 * npr.abs())
    g_hi = df.has_g3 & ~g_nonpos & ~g_ni & (npr > 2 * opx)     # "operating margin" > 50%
    g_ratio = df.has_g3 & ~g_nonpos & ~g_ni & ~g_hi & (opx > 20 * npr)
    # retained-but-suspect band, reported in QA only
    band = df.has_g3 & ~g_nonpos & ~g_ni & ~g_hi & (npr > 1.5 * opx)
    qa["retained_npr_1p5_to_2x_opex"] = dict(
        n=int(band.sum()), npr=float(npr[band].sum()), opex=float(opx[band].sum()),
        net_income=float(ni[band].sum()))
    qa["retained_npr_1p5_to_2x_opex_net_income_by_fyend_year"] = {
        str(int(k)): float(v) for k, v in ni[band].groupby(df.end.dt.year[band]).sum().items()}
    df["drop_reason"] = np.select(
        [no_g3, g_nonpos, g_ni, g_hi, g_ratio],
        ["no_g3", "nonpositive_npr_or_opex", "abs_ni_gt_5x_npr", "npr_gt_2x_opex",
         "opex_gt_20x_npr"],
        default="")
    dropped = df[~df.drop_reason.isin(["", "no_g3"])]
    qa["dropped_garbage_by_fyend_year"] = {
        str(int(y)): dict(n=int(len(g)), npr=float(g.net_patient_revenue.sum()),
                          opex=float(g.total_operating_expenses.sum()),
                          other_income=float(g.other_income.sum()),
                          net_income=float(g.net_income.sum()))
        for y, g in dropped.groupby(dropped.end.dt.year)}
    for reason in ["nonpositive_npr_or_opex", "abs_ni_gt_5x_npr", "npr_gt_2x_opex",
                   "opex_gt_20x_npr"]:
        d = df[df.drop_reason == reason]
        qa["dropped_%s" % reason] = dict(
            n=int(len(d)), npr=float(d.net_patient_revenue.sum()),
            opex=float(d.total_operating_expenses.sum()),
            other_income=float(d.other_income.sum()), net_income=float(d.net_income.sum()))
        qa["dropped_%s_top" % reason] = [
            dict(form=r.form, prvdr_num=r.prvdr_num, fy_end=r.fy_end_dt,
                 npr=float(r.net_patient_revenue), opex=float(r.total_operating_expenses),
                 other_income=float(r.other_income), net_income=float(r.net_income))
            for r in d.reindex(d.net_income.abs().sort_values(ascending=False).index)
            .head(8).itertuples()]
    used = df[df.drop_reason == ""].copy()
    qa["n_reports_used"] = int(len(used))
    qa["n_reports_used_by_form"] = {k: int(v) for k, v in used.groupby("form").size().items()}
    qa["n_used_unknown_ownership"] = int((used.ownership_class == "unknown").sum())
    qa["used_ctrl_code_counts"] = {str(int(k)): int(v) for k, v in
                                   used.groupby("ctrl").size().items()}
    qa["used_days_distribution"] = {
        "lt_330": int((used.days < 330).sum()),
        "330_to_400": int(((used.days >= 330) & (used.days <= 400)).sum()),
        "gt_400": int((used.days > 400).sum())}
    for m in ["depreciation", "interest_expense_capital_a7", "salaries"]:
        qa["missing_%s_n" % m] = int(used[m].isna().sum())

    # A-7 Part III presence: operating expenses of reports that have a
    # depreciation cell (used for the *_a7_opex_coverage columns)
    used["a7_opex"] = used.total_operating_expenses.where(used.depreciation.notna(), 0.0)
    used.drop(columns=["pref_key"]).to_csv(
        os.path.join(EXTRACT, "hcris_report_level_used.csv"), index=False)

    # ---- aggregate: FY-end convention
    used["fyend_year"] = used.end.dt.year
    fy = used.groupby(["fyend_year", "ownership_class"]).agg(
        n_reports=("rpt_rec_num", "size"),
        **{m + "_fyend": (m, "sum") for m in MEASURES + ["a7_opex"]}).reset_index() \
        .rename(columns={"fyend_year": "year"})

    # ---- aggregate: calendar-year proration by days
    parts = []
    y0, y1 = int(used.bgn.dt.year.min()), int(used.end.dt.year.max())
    for y in range(y0, y1 + 1):
        ys, ye = pd.Timestamp(y, 1, 1), pd.Timestamp(y, 12, 31)
        ov = (np.minimum(used.end.values, np.datetime64(ye)) -
              np.maximum(used.bgn.values, np.datetime64(ys))).astype("timedelta64[D]").astype(int) + 1
        ov = np.clip(ov, 0, None)
        m = ov > 0
        if not m.any():
            continue
        sub = used.loc[m, ["ownership_class"] + MEASURES + ["a7_opex"]].copy()
        share = ov[m] / used.days.values[m]
        for c in MEASURES + ["a7_opex"]:
            sub[c] = sub[c].fillna(0.0) * share
        sub["n_report_years"] = ov[m] / float((ye - ys).days + 1)
        sub["year"] = y
        parts.append(sub.groupby(["year", "ownership_class"]).sum(numeric_only=True).reset_index())
    cy = pd.concat(parts, ignore_index=True)

    out = cy.merge(fy, on=["year", "ownership_class"], how="outer")
    num_cols = [c for c in out.columns if c not in ("year", "ownership_class")]
    allc = out.groupby("year")[num_cols].sum(min_count=1).reset_index()
    allc["ownership_class"] = "all"
    out = pd.concat([out, allc], ignore_index=True)
    out["n_reports"] = out.n_reports.fillna(0).astype(int)
    order = {c: i for i, c in enumerate(["all"] + CLASSES)}
    out["_o"] = out.ownership_class.map(order)
    out = out.sort_values(["year", "_o"]).drop(columns="_o")
    # Worksheet A-7 Part III (source of depreciation / capital interest) is
    # missing for most reports in the FY2002-FY2004 files. Publish the share of
    # operating expenses covered, and blank (not estimate) the two A-7 items
    # wherever that share is < A7_MIN_COVERAGE.
    out["a7_opex_coverage"] = (out.a7_opex / out.total_operating_expenses).round(4)
    out["a7_opex_coverage_fyend"] = (out.a7_opex_fyend / out.total_operating_expenses_fyend).round(4)
    for sfx in ("", "_fyend"):
        low = ~(out["a7_opex_coverage" + sfx] >= A7_MIN_COVERAGE)
        for c in ("depreciation", "interest_expense_capital_a7"):
            out.loc[low, c + sfx] = np.nan
    money = MEASURES + [m + "_fyend" for m in MEASURES]
    cols = (["year", "ownership_class", "n_reports", "n_report_years"] + MEASURES +
            ["a7_opex_coverage"] + [m + "_fyend" for m in MEASURES] + ["a7_opex_coverage_fyend"])
    out = out[cols].copy()
    out["n_report_years"] = out.n_report_years.round(2)
    for c in money:
        out[c] = out[c].round(0).astype("Int64")
    out.to_csv(OUT_CSV, index=False)

    with open(OUT_QA, "w") as f:
        json.dump(qa, f, indent=1, sort_keys=True)

    a = out[out.ownership_class == "all"]
    print("\nyear  n_reports  n_rpt_yrs  total_revenue($B)  net_income($B)  margin   [prorated]")
    for r in a.itertuples():
        tr = r.total_revenue
        print("%d  %6d  %8.1f  %10.1f  %8.1f  %6.2f%%" % (
            r.year, r.n_reports, r.n_report_years, tr / 1e9, r.net_income / 1e9,
            100 * r.net_income / tr if tr else float("nan")))
    print("\nwrote", OUT_CSV)
    print("wrote", OUT_QA)


if __name__ == "__main__":
    sys.exit(main())
