"""Shared loaders for the income-side health account. All raw inputs live in data/raw/health_income/ (git-ignored;
re-created by 00_download.sh). Money is in $ millions unless noted."""
import os, re, csv
import pandas as pd, numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(os.path.dirname(ROOT), "data", "raw", "health_income")
INP = os.path.join(ROOT, "data", "inputs")
OUT = os.path.join(ROOT, "data", "output")
Y0, Y1 = 1998, 2025   # NAICS-based NIPA income tables (6.xD) begin in 1998
YEARS = list(range(Y0, Y1 + 1))


# ---------------------------------------------------------------- CMS NHEA
def load_nhe():
    """NHE2024.csv -> dict {block_title: DataFrame(rows = source of funds, cols = years)} in $ millions.
    Row labels are made unique by prefixing parents for Federal / State and Local sub-rows."""
    f = os.path.join(RAW, "cms", "national-health-expenditures-type-service-source-funds-cy-1960-2024", "NHE2024.csv")
    rows = list(csv.reader(open(f, encoding="latin1")))
    years = [int(x) for x in rows[1][1:] if x.strip()]
    blocks, cur, parent = {}, None, None
    for r in rows[2:]:
        lab = r[0]
        if not lab.strip() or lab.startswith("*") or lab.startswith("NOTE") or lab.startswith("SOURCE"):
            continue
        vals = [np.nan if v.strip() in ("", "-", "\x97") else float(v.replace(",", "")) for v in r[1:1 + len(years)]]
        name = lab.strip()
        if not lab.startswith(" "):  # block header (total row)
            if name in ("POPULATION",) or name.startswith("Total CMS Programs"):
                blocks[cur][name] = vals
                continue
            cur = name
            blocks[cur] = {"TOTAL": vals}
            continue
        if name in ("Federal", "State and Local"):
            name = parent + " | " + name
        else:
            parent = name
        blocks[cur][name] = vals
    return {k: pd.DataFrame(v, index=years).T for k, v in blocks.items()}


# ---------------------------------------------------------------- BEA NIPA / Fixed Assets flat files
def _flat(path):
    d = pd.read_csv(path, dtype=str)
    d.columns = ["code", "period", "value"]
    d["value"] = pd.to_numeric(d["value"].str.replace(",", ""), errors="coerce")
    d["period"] = d["period"].astype(int)
    return d.pivot_table(index="code", columns="period", values="value", aggfunc="first")

_cache = {}
def nipa():
    if "nipa" not in _cache:
        _cache["nipa"] = _flat(os.path.join(RAW, "bea", "NipaDataA.txt"))
    return _cache["nipa"]

def fa():
    if "fa" not in _cache:
        _cache["fa"] = _flat(os.path.join(RAW, "bea", "FixedAssets.txt"))
    return _cache["fa"]

def register(which="nipa"):
    f = "SeriesRegister.txt" if which == "nipa" else "FA_SeriesRegister.txt"
    d = pd.read_csv(os.path.join(RAW, "bea", f), dtype=str)
    d.columns = ["code", "label", "metric", "calc", "scale", "tables", "parents"]
    return d

def table_lines(table_id, which="nipa"):
    """Return DataFrame(code,label,line) for one table id like 'T60200D' or 'FAAt304ESI'."""
    reg = register(which)
    out = []
    for _, r in reg.iterrows():
        for t in str(r["tables"]).split("|"):
            if t.startswith(table_id + ":"):
                out.append((int(t.split(":")[1]), r["code"], r["label"]))
    return pd.DataFrame(sorted(out), columns=["line", "code", "label"])

def nipa_series(code, which="nipa"):
    d = nipa() if which == "nipa" else fa()
    return d.loc[code].reindex(YEARS)


# ---------------------------------------------------------------- BEA GDP-by-industry workbooks
def bea_ind_table(workbook, sheet):
    """workbook e.g. 'GdpByInd/ValueAdded.xlsx', sheet e.g. 'TVA113-A'. Returns DataFrame indexed by (line,label)
    with int year columns; labels stripped; keeps order."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(RAW, "bea", workbook), read_only=True)
    rows = list(wb[sheet].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r[0] == "Line")
    yrs = [int(x) for x in rows[hi][3:] if x]
    recs = []
    for r in rows[hi + 1:]:
        if r[1] is None: continue
        vals = [np.nan if (v is None or isinstance(v, str)) else float(v) for v in r[3:3 + len(yrs)]]
        recs.append([r[0], str(r[1]).strip()] + vals)
    d = pd.DataFrame(recs, columns=["line", "label"] + yrs)
    meta = " | ".join(str(r[0]) for r in rows[:6] if r[0])
    d.attrs["meta"] = meta
    return d
