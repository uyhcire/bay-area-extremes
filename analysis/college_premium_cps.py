"""College wage premium in the CPS ORG, 2015 -> latest month, with a consistent
treatment of top-coded (censored) earnings.

  python3 analysis/cps_org_build.py          # data/raw/cps_org/*.parquet + CPIAUCSL.csv (key-free)
  python3 analysis/college_premium_cps.py    # -> analysis/output/college_premium_*.csv

Why censoring matters here
--------------------------
Through March 2023 usual weekly earnings were top-coded at a fixed nominal
$2,884.61 (binding for 2.8% of earners in 2015, ~7% by early 2023). From April
2023 (rotation-phased; complete April 2024) Census instead replaces the top 3%
of weekly earnings -- and, separately, the top 3% of hourly rates -- with the
mean of the replaced values. So the censoring point moves every month and the
whole regime breaks in the middle of the 2022 -> 2026 window.

Fix: impose ONE censoring rule on every month -- a constant *real* threshold
that lies at or below the published censoring point in every month:
    weekly earnings >= $2,884.61 in March-2024 dollars, or
    hourly rate     >= $50.00    in March-2024 dollars
-- and estimate the log-wage equation by censored-normal ML (Tobit) with
observation-specific censoring points and education-specific variances.

Premium = coefficient on BA-or-more (vs. exactly high school) in a regression
of log hourly wage on education dummies, a quartic in potential experience
interacted with sex, race/ethnicity and month dummies; ORG weights.
"""
import glob, os, sys
import numpy as np, pandas as pd
from scipy import optimize, special
import statsmodels.api as sm

RAW = "data/raw/cps_org"
OUT = "analysis/output"
REF = pd.Timestamp(2024, 3, 1)      # dollars in which the common thresholds are fixed
WK_CAP, HR_CAP = 2884.61, 50.0      # common real censoring points (REF dollars)
OLD_TOP = 2884.61


def load():
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(f"{RAW}/cps_org_*.parquet"))], ignore_index=True)
    cpi = pd.read_csv(f"{RAW}/CPIAUCSL.csv", parse_dates=["observation_date"]).set_index("observation_date").CPIAUCSL
    cpi = cpi.reindex(pd.date_range(cpi.index.min(), cpi.index.max(), freq="MS")).interpolate()  # Oct 2025 gap
    d["date"] = pd.to_datetime(dict(year=d.hryear4, month=d.hrmonth, day=1))
    d["defl"] = d.date.map(cpi) / cpi[REF]          # nominal dollars per REF dollar
    assert d.defl.notna().all(), "CPI missing for some months"
    d["wt"] = d.pworwgt / 1e4
    d["wk"] = d.ernwa / 100.0
    d["hr"] = d.ernhly / 100.0
    # --- sample: employed wage & salary workers aged 18-64 with positive earnings
    d = d[d.prtage.between(18, 64) & d.pemlr.isin([1, 2]) & d.peio1cow.between(1, 5) & (d.wk > 0) & (d.wt > 0)].copy()
    hours = d.pehrusl1.where(d.pehrusl1 > 0, d.pehract1)
    d["hours"] = hours.where(hours > 0)
    d["hourly"] = (d.peernhry == 1) & (d.hr > 0)
    d = d[d.hourly | d.hours.notna()].copy()
    # --- regime: dynamic top-code for MIS 4 from Apr 2023, everyone from Apr 2024
    d["new"] = (d.date >= "2024-04-01") | ((d.date >= "2023-04-01") & (d.hrmis == 4))
    grp = [d.date, d.new]
    d["wk_top"] = np.where(d.new, d.wk == d.groupby(grp).wk.transform("max"), d.wk >= OLD_TOP)
    d["hr_top"] = d.hourly & np.where(d.new, d.hr == d[d.hourly].groupby(grp).hr.transform("max").reindex(d.index),
                                      d.pthr == 1)
    # --- wage as published; with the classic 1.5x fix for the old fixed top-code
    d["w_pub"] = np.where(d.hourly, d.hr, d.wk / d.hours)
    wk15 = np.where(d.wk_top & ~d.new, 1.5 * d.wk, d.wk)
    d["w_15"] = np.where(d.hourly, np.where(d.hr_top & ~d.new, 1.5 * d.hr, d.hr), wk15 / d.hours)
    # --- common real censoring rule
    c_wk, c_hr = WK_CAP * d.defl, HR_CAP * d.defl
    d["cens"] = np.where(d.hourly, (d.hr >= c_hr) | d.hr_top, d.wk >= c_wk)
    d["L"] = np.where(d.hourly, np.minimum(d.hr, c_hr), c_wk / d.hours)        # lower bound when censored
    d["w_cap"] = np.where(d.cens, d.L, d.w_pub)
    # sanity: every published top-coded value is censored under the common rule
    assert d.loc[d.wk_top & ~d.hourly, "cens"].all() and d.loc[d.hr_top, "cens"].all()
    d = d[d.w_cap / d.defl >= 3.0].copy()                                       # drop < $3/hr (REF $)
    for c in ("w_pub", "w_15", "w_cap", "L"):
        d["ln_" + c] = np.log(d[c] / d.defl)                                    # real log wages
    # --- covariates
    e = d.peeduca
    d["edu"] = np.select([e <= 38, e == 39, e <= 42, e == 43], [0, 1, 2, 3], 4)  # <HS, HS, some col, BA, adv
    yrs = e.map({39: 12, 40: 13, 41: 14, 42: 14, 43: 16, 44: 18, 45: 19, 46: 21}).fillna(10)
    d["exp"] = (d.prtage - yrs - 6).clip(lower=0)
    d["female"] = (d.pesex == 2).astype(float)
    hisp = d.pehspnon == 1
    d["race"] = np.select([hisp, d.ptdtrace == 1, d.ptdtrace == 2], [1, 0, 2], 3)  # 0 white NH,1 hisp,2 black,3 other
    d["imputed"] = (d.prwernal == 1) | (d.hourly & (d.prhernal == 1))
    d["ft"] = d.hours >= 35
    return d


def design(d):
    x = d.exp / 10.0
    cols = {"const": 1.0, "college": (d.edu >= 3) * 1.0, "lths": (d.edu == 0) * 1.0, "somecol": (d.edu == 2) * 1.0,
            "female": d.female}
    for p in range(1, 5):
        cols[f"exp{p}"] = x ** p
        cols[f"fexp{p}"] = d.female * x ** p
    for r, nm in ((1, "hisp"), (2, "black"), (3, "other")):
        cols[nm] = (d.race == r) * 1.0
    X = pd.DataFrame(cols, index=d.index)
    for m in sorted(d.date.unique())[1:]:
        X[f"m{pd.Timestamp(m):%Y%m}"] = (d.date == m) * 1.0
    return X


def wls(y, X, w):
    r = sm.WLS(y, X, weights=w).fit(cov_type="HC1")
    return r.params["college"], r.bse["college"]


def tobit(y, L, cens, X, w, sgrp):
    """Censored-normal ML. y observed log wage; L log censoring point (used where cens).
    sigma differs by group sgrp (education). Returns college coef and robust SE."""
    Xv = X.values; n, k = Xv.shape; G = pd.get_dummies(sgrp).values.astype(float); g = G.shape[1]
    w = (w / w.mean()).values; c = cens.values; yy = np.where(c, L.values, y.values)
    b0 = np.linalg.lstsq(Xv * np.sqrt(w)[:, None], yy * np.sqrt(w), rcond=None)[0]
    th0 = np.r_[b0, np.full(g, np.log((yy - Xv @ b0).std()))]

    def parts(th):
        s = np.exp(G @ th[k:]); z = (yy - Xv @ th[:k]) / s
        lam = np.exp(special.log_ndtr(-z) * -1 - 0.5 * z * z) / np.sqrt(2 * np.pi)   # phi(z)/Phi(-z)
        ll = np.where(c, special.log_ndtr(-z), -np.log(s) - 0.5 * z * z)
        dz = np.where(c, lam, z)                        # d ll / d(xb) * s
        ds = np.where(c, lam * z, z * z - 1.0)          # d ll / d log s
        return ll, dz / s, ds

    def nll(th):
        ll, db, ds = parts(th)
        return -(w * ll).sum() / n, -np.r_[Xv.T @ (w * db), G.T @ (w * ds)] / n

    res = optimize.minimize(nll, th0, jac=True, method="BFGS", options={"gtol": 1e-7, "maxiter": 500})
    th = res.x
    _, db, ds = parts(th)
    S = np.c_[Xv * (w * db)[:, None], G * (w * ds)[:, None]]
    H = np.empty((k + g, k + g)); eps = 1e-5
    for j in range(k + g):
        e = np.zeros(k + g); e[j] = eps
        H[:, j] = (nll(th + e)[1] - nll(th - e)[1]) / (2 * eps) * n
    Hi = np.linalg.pinv((H + H.T) / 2)
    V = Hi @ (S.T @ S) @ Hi
    j = list(X.columns).index("college")
    return th[j], np.sqrt(V[j, j]), res.success


def median_reg(y, X, w):
    wv = w.values / w.mean()
    r = sm.QuantReg(y.values * wv, X.values * wv[:, None]).fit(q=0.5, max_iter=3000)
    return r.params[list(X.columns).index("college")]


def estimate(d, label, median=True):
    X = design(d); w = d.wt
    X = X.loc[:, (X != 0).any()]
    out = {"period": label, "n": len(d), "months": d.date.nunique(),
           "pct_top_published": 100 * np.average(np.where(d.hourly, d.hr_top, d.wk_top), weights=w),
           "pct_cens_common": 100 * np.average(d.cens, weights=w),
           "pct_cens_common_college": 100 * np.average(d.cens[d.edu >= 3], weights=w[d.edu >= 3])}
    out["ols_published"], out["se_ols_published"] = wls(d.ln_w_pub, X, w)
    out["ols_1.5x_old_topcode"], _ = wls(d.ln_w_15, X, w)
    out["ols_common_cap"], out["se_ols_common_cap"] = wls(d.ln_w_cap, X, w)
    out["tobit"], out["se_tobit"], ok = tobit(d.ln_w_cap, d.ln_L, d.cens, X, w, d.edu)
    out["tobit_converged"] = ok
    if median:
        out["median_reg"] = median_reg(d.ln_w_cap, X, w)
    return out


def run(d, tag, median=True):
    rows = []
    yrs = sorted(d.hryear4.unique())
    for y in yrs:                                           # calendar years (latest year = months to date)
        rows.append(estimate(d[d.hryear4 == y], f"{y}", median))
    for y in yrs:                                           # the paper's window and the months since
        a = d[(d.hryear4 == y) & (d.hrmonth <= 7)]; b = d[(d.hryear4 == y) & d.hrmonth.between(8, 10)]
        rows.append(estimate(a, f"{y} Jan-Jul", median)); rows.append(estimate(b, f"{y} Aug-Oct", median))
    res = pd.DataFrame(rows)
    res.to_csv(f"{OUT}/college_premium_{tag}.csv", index=False)
    return res


def quarterly(d, tag):
    rows = []
    for q, g in d.groupby(d.date.dt.to_period("Q")):
        r = estimate(g, str(q), median=False); rows.append(r)
    res = pd.DataFrame(rows); res.to_csv(f"{OUT}/college_premium_quarterly_{tag}.csv", index=False)
    return res


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    d = load()
    print("sample", len(d), "imputed share", round(d.imputed.mean(), 3))
    which = sys.argv[1:] or ["main", "quarterly", "with_imputed", "ft_weekly_sample", "age25_54"]
    show = ["period", "n", "pct_top_published", "pct_cens_common", "pct_cens_common_college", "ols_published",
            "ols_1.5x_old_topcode", "ols_common_cap", "tobit", "se_tobit", "median_reg"]
    base = d[~d.imputed]
    if "main" in which:
        print("\n== MAIN: non-imputed earnings, ages 18-64 =="); print(run(base, "main")[show].round(4).to_string(index=False))
    if "quarterly" in which:
        print("\n== quarterly =="); print(quarterly(base, "main")[show[:-1]].round(4).to_string(index=False))
    if "with_imputed" in which:
        print("\n== incl. imputed earnings =="); print(run(d, "with_imputed", False)[show[:-1]].round(4).to_string(index=False))
    if "ft_weekly_sample" in which:
        print("\n== full-time (35+ usual hours) only =="); print(run(base[base.ft], "fulltime", False)[show[:-1]].round(4).to_string(index=False))
    if "age25_54" in which:
        print("\n== ages 25-54 =="); print(run(base[base.prtage.between(25, 54)], "age25_54", False)[show[:-1]].round(4).to_string(index=False))
