"""Leontief roll-up on BEA summary-level (71-industry) input-output accounts, 1997-2023.

Tables (all 'before redefinitions', producers' prices, vintage = BEA release of 2024-09-26):
  Use   : IOUse_Before_Redefinitions_PRO_1997-2023_Summary.xlsx   (commodity x industry, + final uses, + VA rows)
  Make  : IOMake_Before_Redefinitions_PRO_1997-2023_Summary.xlsx  (industry x commodity)
  Import: ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx  (commodity x industry/final use, imports only)

Model (industry-technology assumption, domestic/import split from the import matrix):
  D   = V / q            market shares (industry i's share of commodity c output)
  Bd  = (U - M) / g      domestic direct requirements (commodity per $ industry output)
  Bm  = M / g            imported direct requirements
  x   = (I - Bd D)^-1 fd commodity output required by domestic final demand fd
  g*  = D x              industry output
  VA_k = v_k' g*         (k = compensation, TOPI, GOS);   imports = fm + 1'Bm g*
By construction  sum(fd)+sum(fm) = sum_k VA_k + imports (+ a small leak through the 'Used'/'Other' rows,
which is reported, not hidden).
"""
import os, pickle
import numpy as np, pandas as pd
import hi_lib as L

IO_YEARS = list(range(1997, 2024))
_CACHE = os.path.join(L.RAW, "bea", "_io_cache.pkl")


def _read_sheet(path, sheet):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    rows = list(wb[sheet].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r[1] and str(r[1]).startswith(("Commodities/Industries", "Industries/Commodities", "Commodity / Industry")))
    cols = [str(c) if c is not None else None for c in rows[hi]]
    data = {}
    for r in rows[hi + 2:]:
        if r[0] is None and r[1] is None: continue
        key = str(r[0]) if r[0] is not None else str(r[1])
        if key.startswith(("Note", "1.", "2.")): continue
        data[key] = [0.0 if (v is None or isinstance(v, str)) else float(v) for v in r[2:]]
    colnames = []
    lab2 = rows[hi + 1]
    for j, c in enumerate(cols[2:], start=2):
        colnames.append(c if c else str(lab2[j]))
    return pd.DataFrame(data, index=colnames[:len(next(iter(data.values())))]).T


def load_io():
    if os.path.exists(_CACHE):
        return pickle.load(open(_CACHE, "rb"))
    b = os.path.join(L.RAW, "bea")
    out = {}
    for y in IO_YEARS:
        out[y] = dict(
            use=_read_sheet(os.path.join(b, "AllTablesIO", "IOUse_Before_Redefinitions_PRO_1997-2023_Summary.xlsx"), str(y)),
            make=_read_sheet(os.path.join(b, "AllTablesIO", "IOMake_Before_Redefinitions_PRO_1997-2023_Summary.xlsx"), str(y)),
            imp=_read_sheet(os.path.join(b, "ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx"), str(y)),
        )
    pickle.dump(out, open(_CACHE, "wb"))
    return out


class Year:
    """Pre-computed coefficient matrices for one year."""
    def __init__(self, t):
        use, make, imp = t["use"], t["make"], t["imp"]
        self.ind = [c for c in make.index if c in make.columns and c in use.columns and c not in ("Used", "Other") and not c.startswith("Total")]
        self.com = self.ind + ["Used", "Other"]
        ind, com = self.ind, self.com
        U = use.loc[com, ind].values
        M = imp.reindex(index=com, columns=ind).fillna(0).values.copy()
        # noncomparable imports ('Other' row, intermediate) are imports by definition
        io = com.index("Other")
        M[io, :] = U[io, :]
        M = np.where(np.sign(M) == np.sign(U), np.sign(U) * np.minimum(np.abs(M), np.abs(U)), 0.0)
        V = make.loc[ind, com].values
        g = V.sum(axis=1)                      # industry output
        q = V.sum(axis=0)                      # commodity output (domestic)
        self.g, self.q = g, q
        with np.errstate(divide="ignore", invalid="ignore"):
            self.D = np.where(q > 0, V / q, 0.0)           # ind x com
            self.Bd = (U - M) / g                           # com x ind
            self.Bm = M / g
        self.v = {k: use.loc[r, ind].values / g for k, r in (("comp", "V001"), ("topi", "V002"), ("gos", "V003"))}
        self.use, self.imp = use, imp
        n = len(com)
        self.Linv = np.linalg.inv(np.eye(n) - self.Bd @ self.D)
        # leak: commodities with no domestic producer (q == 0) cannot be produced -> their demand is lost
        self.noprod = q <= 0

    def col_shares(self, ind_code, drop=()):
        """Intermediate-input composition of one industry column: returns (dom, imp) share vectors over commodities,
        normalised so that dom+imp sums to 1 over all commodities kept; `drop` commodities are zeroed first."""
        j = self.ind.index(ind_code)
        d, m = self.Bd[:, j].copy(), self.Bm[:, j].copy()
        tot = d.sum() + m.sum()
        for c in drop:
            k = self.com.index(c); d[k] = 0; m[k] = 0
        return d / tot, m / tot

    def final_import_share(self, com_code, fcols):
        """Import share of final purchases of a commodity in given final-use columns (e.g. ['F010'])."""
        u = self.use.loc[com_code, fcols].sum()
        m = self.imp.reindex(index=[com_code], columns=fcols).fillna(0).values.sum()
        return float(np.clip(m / u, 0, 1)) if u > 0 else 0.0

    def rollup(self, fd, fm=None):
        """fd, fm: dicts or arrays over commodities (domestic-produced and directly imported final demand, $).
        Returns dict with comp/topi/gos (by industry arrays), imports (scalar), leak (scalar)."""
        fdv = self._vec(fd); fmv = self._vec(fm) if fm is not None else np.zeros(len(self.com))
        x = self.Linv @ fdv
        gs = self.D @ x
        res = {k: self.v[k] * gs for k in self.v}
        res["imports"] = fmv.sum() + (self.Bm @ gs).sum()
        res["leak"] = fdv.sum() + fmv.sum() - sum(res[k].sum() for k in ("comp", "topi", "gos")) - res["imports"]
        res["gs"] = gs
        return res

    def _vec(self, f):
        if isinstance(f, dict):
            v = np.zeros(len(self.com))
            for c, val in f.items(): v[self.com.index(c)] += val
            return v
        return np.asarray(f, dtype=float)


def years():
    t = load_io()
    return {y: Year(t[y]) for y in IO_YEARS}


if __name__ == "__main__":
    Y = years()
    y = Y[2017]
    # self-test: rolling up total final demand must reproduce GDP components
    fin = [c for c in y.use.columns if c.startswith("F")]
    f_tot = y.use.loc[y.com, fin].sum(axis=1).values
    m_fin = y.imp.reindex(index=y.com, columns=[c for c in fin if c != "F050"]).fillna(0).sum(axis=1).values
    exp_imp = -y.use.loc[y.com, "F050"].values           # total imports by commodity (positive)
    fd = y.use.loc[y.com, [c for c in fin if c != "F050"]].sum(axis=1).values - m_fin
    r = y.rollup(fd, m_fin)
    print("2017 final uses excl. imports col:", fd.sum() + m_fin.sum())
    print({k: round(r[k].sum()) for k in ("comp", "topi", "gos")}, "imports", round(r["imports"]), "leak", round(r["leak"]))
    print("use-table VA totals:", {k: round(y.use.loc[r_, y.ind].sum()) for k, r_ in (("comp", "V001"), ("topi", "V002"), ("gos", "V003"))},
          "total imports (F050):", round(exp_imp.sum()))
    for c in ("621", "622", "623", "524", "325"):
        d, m = y.col_shares(c) if c in y.ind else (None, None)
        print(c, "II import share", round(m.sum(), 3), "VA share of output", round(sum(y.v[k][y.ind.index(c)] for k in y.v), 3))
