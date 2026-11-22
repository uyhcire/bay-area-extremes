"""Build a CPS outgoing-rotation-group (ORG) earnings extract from the Census
Bureau's basic monthly public-use files (key-free).

  python3 analysis/cps_org_build.py [START_YEAR] [END_YEAR]     # default 2015 .. latest

Source: https://www2.census.gov/programs-surveys/cps/datasets/<YEAR>/basic/<mon><yy>pub.{csv,dat.gz}
  - 2020+  : CSV (header names; lower/upper case varies)
  - <=2019 : fixed-width .dat.gz (column positions from January_2017_Record_Layout.txt)
Keeps only earnings-eligible records (PRERELG == 1) and the columns needed for
wage regressions. Writes one parquet per month to data/raw/cps_org/ and skips
months already present. Months that do not exist (e.g. Oct 2025, not collected
during the federal shutdown) are reported and skipped. Also saves the CPI-U
(FRED CPIAUCSL, key-free CSV) used as the deflator.
"""
import gzip, io, os, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

OUT = "data/raw/cps_org"
BASE = "https://www2.census.gov/programs-surveys/cps/datasets"
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]

# 1-indexed inclusive positions (Jan 2015 / Jan 2017 record layouts).
FWF = {
    "hrmonth": (16, 17), "hryear4": (18, 21), "hrmis": (63, 64), "gestfips": (93, 94),
    "prtage": (122, 123), "pesex": (129, 130), "peeduca": (137, 138), "ptdtrace": (139, 140),
    "pehspnon": (157, 158), "pemlr": (180, 181), "pehrusl1": (218, 219), "pehract1": (243, 244),
    "peio1cow": (432, 433), "prerelg": (498, 499), "peernhry": (506, 507), "ernhly": (520, 523),
    "pthr": (524, 524), "peernhro": (525, 526), "ernwa": (527, 534), "ptwk": (535, 535),
    "pworwgt": (603, 612), "prwernal": (639, 640), "prhernal": (641, 642), "peio1ocd": (860, 863),
}
# CSV name -> canonical name (earnings recodes were renamed PR* -> PT* in 2021).
CSV = {c: c for c in FWF if c not in ("ernhly", "ernwa", "peio1ocd")}
CSV.update({"prernhly": "ernhly", "pternhly": "ernhly", "prernwa": "ernwa", "pternwa": "ernwa",
            "peio1ocd": "peio1ocd", "ptio1ocd": "peio1ocd"})


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bay-area-extremes/1.0 (research)"})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=600).read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:  # network hiccup: retry
            err = e
    raise err


def build(year, month):
    dst = f"{OUT}/cps_org_{year}_{month:02d}.parquet"
    if os.path.exists(dst):
        return f"have {year}-{month:02d}"
    stem = f"{BASE}/{year}/basic/{MON[month - 1]}{year % 100:02d}pub"
    if year >= 2020:
        raw = fetch(stem + ".csv")
        if raw is None:
            return f"MISSING {year}-{month:02d}"
        df = pd.read_csv(io.BytesIO(raw), usecols=lambda c: c.lower() in CSV, low_memory=False)
        df.columns = [CSV[c.lower()] for c in df.columns]
    else:
        raw = fetch(stem + ".dat.gz")
        if raw is None:
            return f"MISSING {year}-{month:02d}"
        names = list(FWF)
        df = pd.read_fwf(io.BytesIO(gzip.decompress(raw)), colspecs=[(a - 1, b) for a, b in FWF.values()],
                         names=names, header=None)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df[df.prerelg == 1].reset_index(drop=True)
    assert df.hryear4.eq(year).all() and df.hrmonth.eq(month).all(), (year, month)
    df.to_parquet(dst + ".tmp")
    os.replace(dst + ".tmp", dst)
    return f"ok   {year}-{month:02d} n={len(df)}"


def main():
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 2015
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else pd.Timestamp.today().year
    os.makedirs(OUT, exist_ok=True)
    today = pd.Timestamp.today()
    jobs = [(y, m) for y in range(y0, y1 + 1) for m in range(1, 13) if (y, m) < (today.year, today.month)]
    cpi = fetch("https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL&cosd=2014-01-01")
    open(f"{OUT}/CPIAUCSL.csv", "wb").write(cpi)
    with ThreadPoolExecutor(6) as ex:
        for msg in ex.map(lambda a: build(*a), jobs):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
