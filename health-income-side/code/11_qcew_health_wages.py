#!/usr/bin/env python3
"""11_qcew_health_wages.py -- national QCEW employment & wages for health-care
industries by ownership, annual averages 1997..latest.

Run:  python3 -I health-income-side/code/11_qcew_health_wages.py [FIRST_YEAR] [LAST_YEAR]

Sources (BLS QCEW, no key; User-Agent required):
  * 2014+      : open-data slice API, one small CSV per industry
                 https://data.bls.gov/cew/data/api/<YEAR>/a/industry/<CODE>.csv
  * 1997-2013  : (API returns 404) bulk zip
                 https://data.bls.gov/cew/data/files/<YEAR>/csv/<YEAR>_annual_by_industry.zip
                 The zip is 60-150 MB/year, so it is NOT downloaded whole: the
                 central directory and only the needed members are fetched with
                 HTTP Range requests and the members saved as raw CSVs.
Raw files -> data/raw/health_income/qcew/<YEAR>/<CODE>.csv (skipped if present;
a zero-byte <CODE>.missing marker records a code that does not exist that year).
Output    -> health-income-side/data/inputs/qcew_health_national.csv
             data/raw/health_income/qcew/_download_log.csv (URL, Last-Modified)

Only national rows (area_fips == US000) are kept. Cells with disclosure_code 'N'
(suppressed) are written as missing, never as the 0 BLS puts in the file.
Nothing is interpolated.
"""
import csv, io, os, re, sys, time, zipfile
import urllib.request, urllib.error
import pandas as pd

UA = "Mozilla/5.0 research-script"
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(REPO, "data", "raw", "health_income", "qcew")
OUT = os.path.join(REPO, "health-income-side", "data", "inputs")
API = "https://data.bls.gov/cew/data/api/{y}/a/industry/{c}.csv"
ZIP = "https://data.bls.gov/cew/data/files/{y}/csv/{y}_annual_by_industry.zip"
TITLES = "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv"
API_FIRST_YEAR = 2014          # earlier years 404 on the slice API

HEALTH = ["62", "621", "6211", "6212", "6213", "6214", "6215", "6216", "6219", "62191",
          "622", "6221", "6222", "6223",
          "623", "6231", "6232", "6233", "62331", "623311", "623312", "6239",
          "624", "6241", "62412", "6242", "6243", "6244"]
ADJACENT = ["524114", "3254", "325412", "3391", "334510", "4242",
            "44611", "446110", "45611", "456110",   # pharmacies: NAICS<=2017 / NAICS 2022
            "5417", "54171", "923120"]
TOTALS = ["10", "92"]
CODES = HEALTH + ADJACENT + TOTALS
OWNS = {"0", "1", "2", "3", "5"}
KEEP = ["year", "own_code", "industry_code", "industry_title", "agglvl_code",
        "annual_avg_estabs", "annual_avg_emplvl", "total_annual_wages", "disclosure_code"]


def _open(url, headers=None, tries=4):
    h = {"User-Agent": UA}
    h.update(headers or {})
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=120)
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise
            err = e
        except Exception as e:  # network hiccup
            err = e
        time.sleep(2 * (i + 1))
    raise err


class HttpRangeFile(io.RawIOBase):
    """Seekable read-only view of a remote file via HTTP Range (for zipfile)."""
    BLOCK = 1 << 20

    def __init__(self, url):
        self.url = url
        r = _open(url, {"Range": "bytes=0-0"})
        if r.status != 206:
            raise IOError("server does not honour Range requests: %s" % url)
        self.size = int(r.headers["Content-Range"].split("/")[1])
        self.last_modified = r.headers.get("Last-Modified", "")
        r.close()
        self.pos = 0
        self.cs, self.cache = 0, b""

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        if not (self.cs <= self.pos and self.pos + n <= self.cs + len(self.cache)):
            end = min(self.size, self.pos + max(n, self.BLOCK)) - 1
            r = _open(self.url, {"Range": "bytes=%d-%d" % (self.pos, end)})
            self.cache, self.cs = r.read(), self.pos
            r.close()
            if len(self.cache) < n:
                raise IOError("short range read from %s" % self.url)
        o = self.pos - self.cs
        self.pos += n
        return self.cache[o:o + n]

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def member_code(name):
    # e.g. "1997.annual.by_industry/1997.annual 622 NAICS 622 Hospitals.csv"
    m = re.search(r"\.annual (\S+) ", os.path.basename(name))
    return m.group(1) if m else None


def fetch_year(y, log):
    d = os.path.join(RAW, str(y))
    os.makedirs(d, exist_ok=True)
    need = [c for c in CODES if not (os.path.exists(os.path.join(d, c + ".csv"))
                                     or os.path.exists(os.path.join(d, c + ".missing")))]
    if not need:
        return
    if y >= API_FIRST_YEAR:
        for c in need:
            url = API.format(y=y, c=c)
            try:
                r = _open(url)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    open(os.path.join(d, c + ".missing"), "w").close()
                    log.append((y, c, url, "", "404 (code not in this year's NAICS vintage / not published)"))
                    continue
                raise
            data = r.read()
            tmp = os.path.join(d, c + ".csv.part")
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, os.path.join(d, c + ".csv"))
            log.append((y, c, url, r.headers.get("Last-Modified", ""), "ok"))
            time.sleep(0.1)
    else:
        url = ZIP.format(y=y)
        rf = HttpRangeFile(url)
        zf = zipfile.ZipFile(rf)
        by_code = {}
        for zi in zf.infolist():
            c = member_code(zi.filename)
            if c:
                by_code[c] = zi
        for c in need:
            zi = by_code.get(c)
            if zi is None:
                open(os.path.join(d, c + ".missing"), "w").close()
                log.append((y, c, url, rf.last_modified, "no member for this code in zip"))
                continue
            tmp = os.path.join(d, c + ".csv.part")
            with zf.open(zi) as src, open(tmp, "wb") as f:   # never extract by member path
                while True:
                    b = src.read(1 << 20)
                    if not b:
                        break
                    f.write(b)
            os.replace(tmp, os.path.join(d, c + ".csv"))
            log.append((y, c, url + " :: " + zi.filename, rf.last_modified, "ok"))


def load_titles(log):
    p = os.path.join(RAW, "industry_titles.csv")
    if not os.path.exists(p):
        r = _open(TITLES)
        with open(p, "wb") as f:
            f.write(r.read())
        log.append(("", "titles", TITLES, r.headers.get("Last-Modified", ""), "ok"))
    t = pd.read_csv(p, dtype=str)
    return dict(zip(t["industry_code"], t["industry_title"]))


def parse_year(y, titles):
    frames = []
    for c in CODES:
        p = os.path.join(RAW, str(y), c + ".csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p, dtype=str, keep_default_na=False)
        df.columns = [x.strip().replace("annual_avg_estabs_count", "annual_avg_estabs")
                      for x in df.columns]   # bulk files name it *_estabs_count
        for col in df.columns:
            df[col] = df[col].str.strip()
        df = df[(df["area_fips"] == "US000") & (df["industry_code"] == c)
                & (df["own_code"].isin(OWNS))].copy()
        if df.empty:
            continue
        if "industry_title" not in df.columns:           # API files carry no titles
            df["industry_title"] = df["industry_code"].map(titles).fillna("")
        frames.append(df[KEEP])
    return frames


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 1997
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else 2025
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    log, frames, unreachable = [], [], []
    titles = load_titles(log)
    for y in range(y0, y1 + 1):
        try:
            fetch_year(y, log)
        except Exception as e:
            unreachable.append((y, repr(e)))
            print("!! %d: %r" % (y, e), file=sys.stderr)
        fr = parse_year(y, titles)
        print(y, "industries with national rows:", len(fr), file=sys.stderr)
        frames += fr
    df = pd.concat(frames, ignore_index=True)
    num = ["annual_avg_estabs", "annual_avg_emplvl", "total_annual_wages"]
    for c in num:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    df.loc[df["disclosure_code"] == "N", num] = pd.NA     # suppressed -> missing, not 0
    df["industry_title"] = df["industry_title"].str.replace(r"^(NAICS\d*\s+)?\d+\s+", "", regex=True)
    for c in ["year", "own_code", "agglvl_code"]:
        df[c] = df[c].astype(int)
    df["_o"] = df["industry_code"].map({c: i for i, c in enumerate(CODES)})
    df = df.sort_values(["_o", "own_code", "year"]).drop(columns="_o")
    df.to_csv(os.path.join(OUT, "qcew_health_national.csv"), index=False)
    lp = os.path.join(RAW, "_download_log.csv")
    new = not os.path.exists(lp)
    if log:
        with open(lp, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["year", "industry_code", "url", "last_modified", "status"])
            w.writerows(log)
    print("rows:", len(df), "years:", df.year.min(), "-", df.year.max(), file=sys.stderr)
    if unreachable:
        print("UNREACHABLE:", unreachable, file=sys.stderr)


if __name__ == "__main__":
    main()
