#!/usr/bin/env python3
"""Build the income-side health account, versions A (direct) and B (rolled-up), 1997-2025.

Run:  python3 20_build_accounts.py
Reads raw files under data/raw/health_income/ (see 00_download.sh) and data/inputs/*.csv (scripts 10-12).
Writes data/output/*.csv.  All money in $ millions unless a column says otherwise.

Every number that is not a published statistic is tagged in the `flag` columns / FLAGS list:
  OBS   independently observed (payroll / tax / financial filings) as published by the agency
  PUB   published statistic that the agency itself derives (e.g. BEA residual GOS, CMS expenditure estimate)
  EST   estimated here from published data with a stated assumption
  ASM   pure assumption (no data), always carried with a low/high range
"""
import os, sys, json
import numpy as np, pandas as pd
import hi_lib as L, io_engine as E

YEARS = L.YEARS
H = ["621", "622", "623", "624"]            # provider commodities (intra-sector sales are netted out)

# ------------------------------------------------------------------ scenario parameters (central, low, high)
PARAMS = {
    #                       central low   high   what
    "incl_62412":          (0.85,  0.70, 1.00),  # ASM share of NAICS 62412 (elderly/disabled services) output inside NHEA boundary
    "fed_go_over_comp":    (0.75,  0.60, 1.00),  # ASM federal providers' GO/compensation as a multiple of the private-hospital ratio
    "prop_labor_share":    (0.67,  0.50, 0.85),  # ASM labor share of proprietors' income in provider industries
    "surplus_mode":        ("full", "operating", "full"),  # nonprofit/gov hospital surplus added: full net income (NHEA counts non-operating revenue) vs operating only
    "real_return":         (0.05,  0.03, 0.07),  # ASM real required return for the user-cost variant
}
def P(name, scn):
    return PARAMS[name][{"central": 0, "low": 1, "high": 2}[scn]]


# ------------------------------------------------------------------ helpers
def s(x):
    return pd.Series(x, index=YEARS, dtype=float)

def nipa_code(table, label, nth=0):
    t = L.table_lines(table)
    m = t[t.label.str.strip() == label]
    if len(m) <= nth:
        raise KeyError(f"{table}: {label} #{nth}")
    return m.iloc[nth]["code"]

def nipa(table, label, nth=0):
    return L.nipa_series(nipa_code(table, label, nth))

def ind_block(tab, label, nth=0):
    """Rows following an industry label in TKG105 (GO, VA, comp, topi, gos, II, energy, materials, services)."""
    idx = [i for i, l in enumerate(tab.label) if l == label]
    i = idx[nth]
    blk = tab.iloc[i:i + 9]
    names = ["go", "va", "comp", "topi", "gos", "ii", "ii_energy", "ii_materials", "ii_services"]
    assert blk.label.iloc[1] == "Value added" and blk.label.iloc[5] == "Intermediate inputs", blk.label.tolist()
    return pd.DataFrame({n: blk.iloc[k][YEARS].astype(float).values for k, n in enumerate(names)}, index=YEARS)


def load_inputs():
    I = {}
    I["nhe"] = L.load_nhe()
    kg = L.bea_ind_table("GdpByInd/KLEMS.xlsx", "TKG105-A")
    I["vintage_gdpind"] = kg.attrs["meta"]
    for k, lab in (("621", "Ambulatory health care services"), ("622", "Hospitals"),
                   ("623", "Nursing and residential care facilities"), ("624", "Social assistance"),
                   ("524", "Insurance carriers and related activities")):
        I[k] = ind_block(kg, lab)
    go = L.bea_ind_table("UGdpByInd/GrossOutput.xlsx", "UGO305-A").set_index("label")
    I["go_detail"] = go[YEARS].astype(float)
    va = L.bea_ind_table("UGdpByInd/ValueAdded.xlsx", "UVA205-A").set_index("label")
    I["va_detail"] = va[YEARS].astype(float)
    tv = L.bea_ind_table("GdpByInd/ValueAdded.xlsx", "TVA113-A")
    i = [k for k, l in enumerate(tv.label) if l == "State and local"][0]
    assert tv.label.iloc[i + 4] == "General government"
    I["slgg_va"] = tv.iloc[i + 4][YEARS].astype(float); I["slgg_gos"] = tv.iloc[i + 7][YEARS].astype(float)
    q = os.path.join(L.INP, "qcew_health_national.csv")
    I["qcew"] = pd.read_csv(q, dtype={"industry_code": str}) if os.path.exists(q) else None
    h = os.path.join(L.INP, "hcris_hospital_financials.csv")
    I["hcris"] = pd.read_csv(h) if os.path.exists(h) else None
    return I


def qw(I, own, ind):
    """QCEW national total annual wages ($ millions) for ownership code and NAICS code(s)."""
    q = I["qcew"]
    if isinstance(ind, str): ind = [ind]
    m = q[(q.own_code == own) & (q.industry_code.isin(ind))]
    return m.groupby("year").total_annual_wages.sum().reindex(YEARS) / 1e6


FLAGS = []   # (item, years, tag, note)


# ------------------------------------------------------------------ provider block
def provider_block(I, scn="central"):
    """Returns dict sector -> DataFrame(go, comp, topi, gos, ii, ii_energy, ii_materials, ii_services), in-scope only."""
    S = {}
    S["ambulatory_621"] = I["621"].copy()
    S["hospitals_private_622"] = I["622"].copy()

    # --- 623: keep nursing care (6231), CCRCs (623311) and residential MH/SA (6232); drop assisted living (623312) and 6239
    g = I["go_detail"]
    N = g.loc["Nursing and community care facilities"]; R = g.loc["Residential mental health, substance abuse, and other residential care facilities"]
    wN_in = qw(I, 5, ["6231", "623311"]); wN_all = qw(I, 5, ["6231", "6233"])
    wR_in = qw(I, 5, ["6232"]); wR_all = qw(I, 5, ["6232", "6239"])
    sN = (wN_in / wN_all); sR = (wR_in / wR_all)
    s623 = (N * sN + R * sR) / (N + R)
    S["nursing_residential_623_scoped"] = I["623"].mul(s623, axis=0)
    I["scope_623"] = pd.DataFrame({"share_nursing_ccrc_of_6231_6233": sN, "share_6232_of_6232_6239": sR, "scope_623": s623})

    # --- 624: only services for the elderly and persons with disabilities (62412), times an inclusion share (ASM)
    go624 = g.loc[["Individual and family services", "Child day care services",
                   "Community food, housing, and other relief services, including rehabilitation services"]].sum()
    s62412 = g.loc["Individual and family services"] / go624 * (qw(I, 5, ["62412"]) / qw(I, 5, ["6241"]))
    s624 = s62412 * P("incl_62412", scn)
    S["home_community_62412_scoped"] = I["624"].mul(s624, axis=0)
    I["scope_624"] = pd.DataFrame({"go_share_62412_in_624": s62412, "scope_624": s624})

    # --- State & local government hospitals and health services (BEA general-government function)
    go_sl = g.loc["State and local government (hospitals and health services)"]
    va_sl = I["va_detail"].loc["State and local government hospitals and health services"]
    # CFC share of value added: 2017 benchmark detail (GSLGH: GOS 17,879 / VA 157,195) moved with the S&L general-government ratio
    k_all = I["slgg_gos"] / I["slgg_va"]
    k_sl = (17879.0 / 157195.0) * k_all / k_all[2017]
    sl = pd.DataFrame(index=YEARS)
    sl["go"] = go_sl; sl["va"] = va_sl
    sl["gos"] = va_sl * k_sl; sl["comp"] = va_sl - sl["gos"]; sl["topi"] = 0.0
    sl["ii"] = go_sl - va_sl
    for k in ("energy", "materials", "services"):  # split like private hospitals (EST)
        sl["ii_" + k] = sl["ii"] * I["622"]["ii_" + k] / I["622"]["ii"]
    S["state_local_gov_hospitals_health"] = sl

    # --- Federal direct providers (VA, IHS, civilian DoD): QCEW federal-ownership payroll in NAICS 621-623  (EST)
    w_fed = qw(I, 1, ["621", "622", "623"])
    cw = nipa("T60200D", "Civilian") / nipa("T60300D", "Civilian")          # federal civilian compensation / wages
    fed = pd.DataFrame(index=YEARS)
    fed["comp"] = w_fed * cw
    ratio = (I["622"]["go"] / I["622"]["comp"]) * P("fed_go_over_comp", scn)
    fed["go"] = fed["comp"] * ratio
    fed["gos"] = fed["comp"] * (sl["gos"] / sl["comp"]); fed["topi"] = 0.0
    fed["va"] = fed["comp"] + fed["gos"]; fed["ii"] = fed["go"] - fed["va"]
    for k in ("energy", "materials", "services"):
        fed["ii_" + k] = fed["ii"] * I["622"]["ii_" + k] / I["622"]["ii"]
    S["federal_direct_providers"] = fed
    return S


def hospital_surplus(I, S, scn="central"):
    """Nonprofit + non-federal government hospital surplus from Medicare cost reports (Worksheet G-3).
    BEA values nonprofit/government output at cost, so this income is outside BEA gross output.  $ millions."""
    h = I["hcris"]
    if h is None:
        return s(np.nan), s(False)
    d = h[h.ownership_class.isin(["nonprofit", "government_nonfederal"])].groupby("year").sum(numeric_only=True)
    a = h[h.ownership_class == "all"].set_index("year")
    mode = P("surplus_mode", scn)
    ni = d["net_income"]
    if mode == "ex_investment" and "investment_income" in d:
        sur = ni - d["investment_income"]
    elif mode == "operating" and {"investment_income", "contributions_donations"} <= set(d.columns):
        sur = ni - d["investment_income"] - d["contributions_donations"]
    else:
        sur = ni
    rate = (sur / d["total_operating_expenses"]).reindex(YEARS)
    opex = (d["total_operating_expenses"] / 1e6).reindex(YEARS)
    # completeness: report-years filed relative to the running maximum of earlier years
    n = a["n_report_years"].reindex(YEARS)
    complete = n >= 0.97 * n.rolling(4, min_periods=1).max().shift(1).fillna(n)
    complete &= rate.notna()
    base = (S["hospitals_private_622"]["go"] + S["state_local_gov_hospitals_health"]["go"])
    last = max(y for y in YEARS if complete[y])
    est = opex.copy()
    for y in YEARS:
        if not complete[y]:
            ref = last if y > last else min(yy for yy in YEARS if complete[yy])
            est[y] = opex[ref] * base[y] / base[ref]          # EST: move expenses with BEA hospital output
            if np.isnan(rate[y]): rate[y] = rate[ref]
    return est * rate, complete


# ------------------------------------------------------------------ IO shares
def detail_to_summary_map():
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(L.RAW, "bea", "PCEBridge_Detail.xlsx"), read_only=True)
    m, cur = {}, None
    for r in wb["NAICS Codes"].iter_rows(values_only=True):
        if r[1] is not None and r[0] is None and str(r[1]).strip() and r[2] is not None and r[3] is None:
            cur = str(r[1]).strip()
        if r[3] is not None and str(r[3]).strip() and cur:
            m[str(r[3]).strip()] = cur
    return m

def gslgh_shares():
    """2017 benchmark detail intermediate-input composition of 'State and local government hospitals and health
    services' (GSLGH), aggregated to summary commodities.  Returns Series of shares summing to 1."""
    import openpyxl
    f = os.path.join(L.RAW, "bea", "AllTablesIO", "IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx")
    rows = list(openpyxl.load_workbook(f, read_only=True)["2017"].iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows) if r[0] == "Code")
    j = [str(c) for c in rows[hi]].index("GSLGH")
    mp = detail_to_summary_map()
    mp.update({"S00401": "Used", "S00402": "Used", "S00300": "Other", "S00900": "Other"})
    out, miss = {}, 0.0
    for r in rows[hi + 1:]:
        code = str(r[0]) if r[0] is not None else ""
        if code.startswith(("T0", "V0")) or not code: continue
        v = r[j] if isinstance(r[j], (int, float)) else 0.0
        sc = mp.get(code)
        if sc is None:
            miss += v; continue
        out[sc] = out.get(sc, 0.0) + v
    sh = pd.Series(out); tot = sh.sum() + miss
    return sh / sh.sum(), miss / tot

def pce_bridge():
    """Annual PCE bridge (summary level): for the drug and appliance lines, shares of purchasers' value by
    (commodity at producers' value, transport, wholesale, retail)."""
    import openpyxl
    wb = openpyxl.load_workbook(os.path.join(L.RAW, "bea", "PCEBridge_Summary.xlsx"), read_only=True)
    out = {}
    for y in YEARS:
        if str(y) not in wb.sheetnames: continue
        for r in wb[str(y)].iter_rows(min_row=6, values_only=True):
            if r[0] in (21, 40) and isinstance(r[4], (int, float)):
                d = out.setdefault((y, r[0]), {})
                c = str(r[2])
                d[c] = d.get(c, 0.0) + r[4]
                d["484"] = d.get("484", 0.0) + (r[5] or 0)
                d["42"] = d.get("42", 0.0) + (r[6] or 0)
                d["4A0"] = d.get("4A0", 0.0) + (r[7] or 0)
    return {k: pd.Series(v) / sum(v.values()) for k, v in out.items()}

EQ_MAP = {  # BEA fixed-asset type -> summary IO commodity  (EST mapping)
    "EP1A": "334", "EP1B": "334", "EP1C": "334", "EP1D": "334", "EP1E": "334", "EP1F": "334", "EP1G": "334", "EP1H": "334",
    "EP20": "334", "EP34": "339", "EP35": "334", "EP36": "334", "EP31": "333", "EP12": "333", "EI12": "332",
    "EI21": "333", "EI22": "333", "EI30": "333", "EI40": "333", "EI50": "333", "EI60": "335",
    "ET11": "3361MV", "ET12": "3361MV", "ET20": "3361MV", "ET30": "3364OT", "ET40": "3364OT", "ET50": "3364OT",
    "EO11": "337", "EO12": "337", "EO30": "333", "EO21": "333", "EO40": "333", "EO22": "333", "EO50": "333",
    "EO60": "333", "EO71": "335", "EO72": "335", "EO80": "339", "ENS1": "511", "ENS2": "5415"}

def equipment_mix():
    """Commodity mix of equipment + purchased software investment by private health industries (621, 622, 623),
    BEA detailed fixed-asset investment (nominal).  Returns DataFrame(year x commodity) of shares."""
    import openpyxl
    ws = openpyxl.load_workbook(os.path.join(L.RAW, "bea", "detailnonres_inv1.xlsx"), read_only=True)["Datasets"]
    it = ws.iter_rows(values_only=True)
    hdr = next(it); yrs = [int(x) for x in hdr[1:]]
    acc = {}
    for r in it:
        code = str(r[0])
        ind, asset = code[3:7], code[8:12]
        if ind in ("6210", "622H", "6230") and asset in EQ_MAP:
            v = pd.Series([x if isinstance(x, (int, float)) else 0.0 for x in r[1:]], index=yrs)
            acc[EQ_MAP[asset]] = acc.get(EQ_MAP[asset], 0) + v
    d = pd.DataFrame(acc).reindex(YEARS)
    return d.div(d.sum(axis=1), axis=0)


# ------------------------------------------------------------------ main build
def build(I, IO, scn="central", detail=False):
    S = provider_block(I, scn)
    nhe = I["nhe"]
    T = lambda blk, row="TOTAL": nhe[blk].loc[row].reindex(YEARS)
    surplus, complete = hospital_surplus(I, S, scn)

    # proprietors' income attributable to in-scope provider industries (EST allocation by GOS)
    pi62 = nipa("T61200D", "Health care and social assistance")
    gos_base = I["621"]["gos"] + I["623"]["gos"] + I["624"]["gos"]
    gos_in = S["ambulatory_621"]["gos"] + S["nursing_residential_623_scoped"]["gos"] + S["home_community_62412_scoped"]["gos"]
    pi_in = pi62 * gos_in / gos_base
    prop_labor = pi_in * P("prop_labor_share", scn)

    gsl_sh, gsl_miss = gslgh_shares()
    bridge = pce_bridge()
    eqmix = equipment_mix()

    colmap = {"ambulatory_621": "621", "hospitals_private_622": "622", "nursing_residential_623_scoped": "623",
              "home_community_62412_scoped": "624", "federal_direct_providers": "622"}
    rows, cat_rows, intra = [], [], s(0.0)
    for y in YEARS:
        io = IO[min(y, max(IO))]
        com = io.com
        imp_ratio = np.divide((io.Bm * io.g).sum(axis=1), ((io.Bd + io.Bm) * io.g).sum(axis=1),
                              out=np.zeros(len(com)), where=((io.Bd + io.Bm) * io.g).sum(axis=1) > 0)
        cats = {}   # category -> (fd vector, fm vector)

        # ---- providers' purchases from outside the provider sector
        fd = np.zeros(len(com)); fm = np.zeros(len(com)); intra_y = 0.0
        for sec, df in S.items():
            ii = df.loc[y, "ii"]
            if sec == "state_local_gov_hospitals_health":
                sh = gsl_sh.reindex(com).fillna(0).values
                d, m = sh * (1 - imp_ratio), sh * imp_ratio
            else:
                d, m = io.col_shares(colmap[sec])
            hidx = [com.index(c) for c in H]
            intra_y += ii * (d[hidx].sum() + m[hidx].sum())
            d = d.copy(); m = m.copy(); d[hidx] = 0; m[hidx] = 0
            fd += ii * d; fm += ii * m
        intra[y] = intra_y
        cats["providers_intermediate"] = (fd, fm)

        def goods_vector(total, shares, fcols):
            fd = np.zeros(len(com)); fm = np.zeros(len(com))
            for c, sh in shares.items():
                if c not in com or sh == 0: continue
                k = com.index(c); v = total * sh
                ms = io.final_import_share(c, fcols) if c[0] == "3" else 0.0
                fd[k] += v * (1 - ms); fm[k] += v * ms
            return fd, fm

        by = min(y, max(k[0] for k in bridge))
        cats["retail_rx_drugs"] = goods_vector(T("Total Prescription Drug Expenditures")[y], bridge[(by, 40)], ["F010"])
        cats["other_nondurable_products"] = goods_vector(T("Other Non-Durable Medical Products Expenditures")[y], bridge[(by, 40)], ["F010"])
        cats["durable_medical_equipment"] = goods_vector(T("Total Durable Medical Equipment Expenditures")[y], bridge[(by, 21)], ["F010"])
        cats["net_cost_health_insurance"] = goods_vector(T("Non-Medical Insurance Expenditures")[y], {"524": 1.0}, ["F010"])
        cats["gov_admin_federal"] = goods_vector(T("Federal Administration Expenditures")[y], {"GFGN": 1.0}, [])
        cats["gov_admin_state_local"] = goods_vector(T("State and Local  Administration Expenditures")[y], {"GSLG": 1.0}, [])
        cats["public_health_federal"] = goods_vector(T("Public Health Activity", "Federal Funds")[y], {"GFGN": 1.0}, [])
        cats["research"] = goods_vector(T("Research")[y], {"61": 0.60, "5412OP": 0.25, "GFGN": 0.15}, [])   # ASM
        cats["structures"] = goods_vector(T("Total Structures and Equipment", "Structures")[y], {"23": 1.0}, [])
        # equipment: goods at producers' prices + trade/transport margins in the proportion of the F02E column
        f02 = io.use.loc[com, "F02E"]
        marg = [c for c in com if c in ("42", "441", "445", "452", "4A0", "481", "482", "483", "484", "485", "486", "487OS", "493")]
        goods = [c for c in com if c[0] == "3"]
        mrate = f02[marg].clip(lower=0) / f02[goods].sum()
        mix = eqmix.loc[min(y, eqmix.dropna().index.max())]
        gshare = mix[[c for c in mix.index if c[0] == "3"]].sum()
        sh = dict(mix)
        for c in marg: sh[c] = sh.get(c, 0) + gshare * mrate[c]
        tot = sum(sh.values()); sh = {c: v / tot for c, v in sh.items()}
        cats["equipment"] = goods_vector(T("Total Structures and Equipment", "Equipment")[y], sh, ["F02E"])

        rec = {"year": y}
        up = {}
        for c, (fdv, fmv) in cats.items():
            r = io.rollup(fdv, fmv)
            up[c] = dict(final=fdv.sum() + fmv.sum(), comp=r["comp"].sum(), topi=r["topi"].sum(), gos=r["gos"].sum(),
                         imports=r["imports"], leak=r["leak"])
            cat_rows.append(dict(year=y, category=c, **up[c]))
            if detail and y in detail:
                for k in ("comp", "topi", "gos"):
                    for i_, code in enumerate(io.ind):
                        rec.setdefault("_ind", []).append((c, k, code, r[k][i_]))
        # ---- direct provider layer
        for sec, df in S.items():
            for k in ("go", "comp", "topi", "gos", "ii", "ii_energy", "ii_materials", "ii_services"):
                rec[f"{sec}.{k}"] = df.loc[y, k]
            cat_rows.append(dict(year=y, category="direct:" + sec, final=df.loc[y, "go"] - df.loc[y, "ii"], comp=df.loc[y, "comp"],
                                 topi=df.loc[y, "topi"], gos=df.loc[y, "gos"], imports=0.0, leak=0.0))
        rec["prov_go"] = sum(df.loc[y, "go"] for df in S.values())
        rec["prov_comp"] = sum(df.loc[y, "comp"] for df in S.values())
        rec["prov_topi"] = sum(df.loc[y, "topi"] for df in S.values())
        rec["prov_gos"] = sum(df.loc[y, "gos"] for df in S.values())
        rec["prov_ii"] = sum(df.loc[y, "ii"] for df in S.values())
        for k in ("energy", "materials", "services"):
            rec["prov_ii_" + k] = sum(df.loc[y, "ii_" + k] for df in S.values())
        rec["prov_intra_sales"] = intra_y
        rec["prov_prop_labor"] = prop_labor[y]
        rec["hosp_surplus_addon"] = surplus[y]
        rec["hosp_surplus_is_estimate"] = not bool(complete[y])
        rec["prov_final_output"] = rec["prov_go"] - intra_y + surplus[y]
        for c in cats:
            if c != "providers_intermediate":
                rec["np." + c] = up[c]["final"]
        rec["nonprovider_total"] = sum(up[c]["final"] for c in cats if c != "providers_intermediate")
        rec["A_total"] = rec["prov_final_output"] + rec["nonprovider_total"]
        # ---- version B
        U = {k: sum(up[c][k] for c in cats) for k in ("comp", "topi", "gos", "imports", "leak")}
        Upi = {k: up["providers_intermediate"][k] for k in ("comp", "topi", "gos", "imports", "leak")}
        rec.update({
            "B_labor_direct_employee": rec["prov_comp"],
            "B_labor_direct_proprietor_imputed": prop_labor[y],
            "B_labor_upstream_provider_inputs": Upi["comp"],
            "B_labor_nonprovider_chains": U["comp"] - Upi["comp"],
            "B_capital_direct": rec["prov_gos"] - prop_labor[y],
            "B_capital_hospital_surplus": surplus[y],
            "B_capital_upstream_provider_inputs": Upi["gos"],
            "B_capital_nonprovider_chains": U["gos"] - Upi["gos"],
            "B_taxes_direct": rec["prov_topi"],
            "B_taxes_upstream": U["topi"],
            "B_imports": U["imports"],
            "B_unallocated_leak": U["leak"],
        })
        rec["B_labor"] = rec["B_labor_direct_employee"] + rec["B_labor_direct_proprietor_imputed"] + U["comp"]
        rec["B_capital"] = rec["B_capital_direct"] + rec["B_capital_hospital_surplus"] + U["gos"]
        rec["B_taxes"] = rec["B_taxes_direct"] + rec["B_taxes_upstream"]
        rec["B_total"] = rec["B_labor"] + rec["B_capital"] + rec["B_taxes"] + rec["B_imports"] + rec["B_unallocated_leak"]
        rec["io_coeff_year"] = min(y, max(IO))
        rows.append(rec)
    out = pd.DataFrame(rows).set_index("year")
    # ---- NHEA side and discrepancy
    out["nhe_total"] = T("Total National Health Expenditures")
    out["nhe_hce"] = T("Health Consumption Expenditures")
    out["nhe_phc"] = T("Personal Health Care")
    prov_cats = ["Total Hospital Expenditures", "Total Physician and Clinical Expenditures", "Total Dental Services Expenditures",
                 "Total Other Professional Services Expenditures", "Total Home Health Care Expenditures",
                 "Total Nursing Care Facilities and Continuing Care Retirement Communities",
                 "Total Other Health, Residential, and Personal Care Expenditures"]
    out["nhe_provider_services"] = sum(T(c) for c in prov_cats)
    out["nhe_public_health_state_local"] = T("Public Health Activity", "State/Local Funds")
    out["nhe_provider_boundary"] = out["nhe_provider_services"] + out["nhe_public_health_state_local"]
    out["discrepancy"] = out["nhe_total"] - out["A_total"]                 # = NHEA provider boundary - income-side provider output
    out["discrepancy_pct_nhe"] = 100 * out["discrepancy"] / out["nhe_total"]
    # memo: federal COVID-era relief (Provider Relief Fund, PPP) that CMS books as provider spending under
    # "Other Federal Programs"; BEA books it as subsidies (negative TOPI), not output
    out["memo_nhe_other_federal_programs_in_provider_services"] = sum(T(c, "Other Federal Programs*") for c in prov_cats).fillna(0.0)
    out["discrepancy_ex_other_federal_programs"] = out["discrepancy"] - out["memo_nhe_other_federal_programs_in_provider_services"]
    out["discrepancy_ex_other_federal_programs_pct_nhe"] = 100 * out["discrepancy_ex_other_federal_programs"] / out["nhe_total"]
    out["A_total_hce_basis"] = out["A_total"] - out["np.research"] - out["np.structures"] - out["np.equipment"]
    return out, pd.DataFrame(cat_rows), S


def main():
    os.makedirs(L.OUT, exist_ok=True)
    I = load_inputs()
    if I["qcew"] is None or I["hcris"] is None:
        sys.exit("missing data/inputs/qcew_health_national.csv or hcris_hospital_financials.csv (run scripts 10, 11)")
    IO = E.years()
    res = {}
    for scn in ("central", "low", "high"):
        res[scn], cats, S = build(I, IO, scn)
        if scn == "central":
            cats.to_csv(os.path.join(L.OUT, "version_B_by_category_long.csv"), index=False, float_format="%.1f")
            pd.concat({k: v for k, v in S.items()}, axis=1).to_csv(os.path.join(L.OUT, "provider_sectors_detail.csv"), float_format="%.1f")
            I["scope_623"].join(I["scope_624"]).to_csv(os.path.join(L.OUT, "scope_shares.csv"), float_format="%.4f")
    c = res["central"].copy()
    for scn in ("low", "high"):
        for k in ("A_total", "discrepancy", "discrepancy_pct_nhe", "B_labor", "B_capital", "prov_final_output"):
            c[f"{k}_{scn}"] = res[scn][k]
    c.to_csv(os.path.join(L.OUT, "income_side_health_account.csv"), float_format="%.1f")
    json.dump({"params": PARAMS, "vintage_gdp_by_industry": I["vintage_gdpind"]}, open(os.path.join(L.OUT, "run_metadata.json"), "w"), indent=1)
    pd.set_option("display.width", 250); pd.options.display.float_format = "{:,.0f}".format
    show = c.loc[[1998, 2000, 2007, 2009, 2015, 2019, 2020, 2021, 2023, 2024, 2025],
                 ["prov_go", "prov_intra_sales", "hosp_surplus_addon", "prov_final_output", "nhe_provider_boundary", "nonprovider_total",
                  "A_total", "nhe_total", "discrepancy", "A_total_low", "A_total_high"]] / 1e3
    print(show.to_string())
    print((c[["discrepancy_pct_nhe", "discrepancy_pct_nhe_low", "discrepancy_pct_nhe_high"]]).round(2).T.to_string())
    b = c[["B_labor", "B_capital", "B_taxes", "B_imports", "B_unallocated_leak", "B_total", "A_total"]]
    print((b.loc[[1998, 2007, 2019, 2023, 2024]] / 1e3).to_string())
    print((100 * b[["B_labor", "B_capital", "B_taxes", "B_imports"]].div(b["B_total"], axis=0)).loc[[1998, 2007, 2019, 2023, 2024]].round(1).to_string())


if __name__ == "__main__":
    main()
