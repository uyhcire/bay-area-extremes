#!/usr/bin/env python3
"""Comparisons, independence checks, user-cost variant and charts.  Run after 20_build_accounts.py.
Writes data/output/{comparison_levels,comparison_growth,volatility_summary,independence_check,user_cost_variant}.csv
and docs/fig*.png."""
import os, importlib
import numpy as np, pandas as pd
import hi_lib as L
B = importlib.import_module("20_build_accounts")

YEARS = L.YEARS
DOCS = os.path.join(L.ROOT, "docs")
acc = pd.read_csv(os.path.join(L.OUT, "income_side_health_account.csv"), index_col=0)
I = B.load_inputs()
cmp_ = pd.read_csv(os.path.join(L.INP, "comparison_series.csv"))
C = lambda sid: cmp_[cmp_.series_id == sid].set_index("year")["value"].reindex(YEARS)
N = lambda code: L.nipa_series(code)
nhe_ok = acc["nhe_total"].notna()

# ------------------------------------------------------------------ 1. comparison levels
gdp, pop = N("A191RC"), N("B230RC") / 1e3            # $ millions; millions of persons
lev = pd.DataFrame(index=YEARS)
lev["income_side_total_A"] = acc["A_total"]
lev["income_side_total_A_low"] = acc["A_total_low"]; lev["income_side_total_A_high"] = acc["A_total_high"]
lev["income_side_hce_basis"] = acc["A_total_hce_basis"]
lev["income_side_provider_output"] = acc["prov_final_output"]
lev["provider_compensation_observed"] = acc["prov_comp"]
lev["domestic_labor_B"] = acc["B_labor"]; lev["domestic_capital_B"] = acc["B_capital"]
lev["nhe_total"] = acc["nhe_total"]; lev["nhe_hce"] = acc["nhe_hce"]; lev["nhe_phc"] = acc["nhe_phc"]
lev["nhe_provider_boundary"] = acc["nhe_provider_boundary"]
lev["pce_health_care_services"] = N("DHLCRC")
lev["gdp"] = gdp; lev["population_millions"] = pop
lev["nhe_share_gdp_pct"] = 100 * lev["nhe_total"] / gdp
lev["income_side_share_gdp_pct"] = 100 * lev["income_side_total_A"] / gdp
lev["nhe_per_capita_usd"] = lev["nhe_total"] / pop
lev["income_side_per_capita_usd"] = lev["income_side_total_A"] / pop
lev["kff_family_premium_usd"] = C("KFF_EHBS_PREMIUM_FAMILY"); lev["kff_single_premium_usd"] = C("KFF_EHBS_PREMIUM_SINGLE")
lev["cpi_medical_care"] = C("CUUR0000SAM"); lev["cpi_all_items"] = C("CUUR0000SA0")
lev["pce_health_care_price_index"] = N("DHLCRG")
# years after the last NHEA year: the non-provider block is unavailable, so totals are blank there
for k in ("income_side_total_A", "income_side_total_A_low", "income_side_total_A_high", "income_side_hce_basis",
          "income_side_share_gdp_pct", "income_side_per_capita_usd", "domestic_labor_B", "domestic_capital_B"):
    lev.loc[~nhe_ok, k] = np.nan
lev.to_csv(os.path.join(L.OUT, "comparison_levels.csv"), float_format="%.2f")

gcols = ["income_side_total_A", "income_side_hce_basis", "income_side_provider_output", "provider_compensation_observed",
         "domestic_labor_B", "domestic_capital_B", "nhe_total", "nhe_hce", "nhe_phc", "nhe_provider_boundary",
         "pce_health_care_services", "gdp", "nhe_per_capita_usd", "income_side_per_capita_usd",
         "kff_family_premium_usd", "kff_single_premium_usd", "cpi_medical_care", "cpi_all_items", "pce_health_care_price_index"]
gr = 100 * lev[gcols].pct_change(fill_method=None)
gr.to_csv(os.path.join(L.OUT, "comparison_growth.csv"), float_format="%.2f")

def stats(x):
    x = x.dropna()
    d = x.diff().dropna()
    return pd.Series({"first_year": x.index.min(), "last_year": x.index.max(), "mean_growth_pct": x.mean(), "sd_growth_pct": x.std(),
                      "sd_change_in_growth_pp": d.std(), "min_growth_pct": x.min(), "max_growth_pct": x.max(),
                      "g2008": x.get(2008), "g2009": x.get(2009), "g2020": x.get(2020), "g2021": x.get(2021), "g2022": x.get(2022)})
common = gr.loc[2000:2024]          # common window in which every series (incl. KFF) has growth rates
vol = pd.concat({"1998-latest": gr.apply(stats).T, "2000-2024 common window": common.apply(stats).T,
                 "2000-2019 pre-COVID": gr.loc[2000:2019].apply(stats).T})
vol.to_csv(os.path.join(L.OUT, "volatility_summary.csv"), float_format="%.2f")

# ------------------------------------------------------------------ 2. independence check (private NAICS 62)
ind = pd.DataFrame(index=YEARS)
ind["bea_comp_621_623"] = I["621"]["comp"] + I["622"]["comp"] + I["623"]["comp"]
ind["qcew_private_wages_621_623"] = B.qw(I, 5, ["621", "622", "623"])
ind["bea_comp_over_qcew_wages"] = ind["bea_comp_621_623"] / ind["qcew_private_wages_621_623"]
ind["bea_gos_62_residual"] = sum(I[k]["gos"] for k in ("621", "622", "623", "624"))
ind["corp_profits_before_tax_62"] = B.nipa("T61700D", "Health care and social assistance")
ind["corp_capital_consumption_allow_62"] = B.nipa("T62200D", "Health care and social assistance")
ind["proprietors_income_62"] = B.nipa("T61200D", "Health care and social assistance")
ind["noncorp_capital_consumption_allow_62"] = B.nipa("T61300D", "Health care and social assistance")
va62 = sum(I[k]["va"] for k in ("621", "622", "623", "624"))
va6162 = L.bea_ind_table("GdpByInd/ValueAdded.xlsx", "TVA105-A").set_index("label").loc["Educational services, health care, and social assistance", YEARS].astype(float)
ind["net_interest_62_allocated"] = B.nipa("T61500D", "Educational services, health care, and social assistance") * va62 / va6162   # EST
h = I["hcris"]; hn = h[h.ownership_class == "nonprofit"].set_index("year")
ind["hcris_nonprofit_hosp_depreciation"] = (hn["depreciation"] / 1e6).reindex(YEARS)
ind["hcris_nonprofit_hosp_interest"] = (hn["interest_expense_capital_a7"] / 1e6).reindex(YEARS)
obs = ["corp_profits_before_tax_62", "corp_capital_consumption_allow_62", "proprietors_income_62",
       "noncorp_capital_consumption_allow_62", "net_interest_62_allocated", "hcris_nonprofit_hosp_depreciation"]
ind["capital_income_independent_sum"] = ind[obs].sum(axis=1, min_count=len(obs))
ind["gap_bea_gos_minus_independent"] = ind["bea_gos_62_residual"] - ind["capital_income_independent_sum"]
ind["gap_pct_of_va_62"] = 100 * ind["gap_bea_gos_minus_independent"] / va62
ind["fa_current_cost_depreciation_62"] = sum(L.nipa_series(c, "fa") for c in ("m1n62101es00", "m1n622h1es00", "m1n62301es00", "m1n62401es00"))
ha = h[h.ownership_class == "all"].set_index("year")
ind["hcris_all_hosp_total_revenue"] = (ha["total_revenue"] / 1e6).reindex(YEARS)
ind["nhe_hospital_care"] = I["nhe"]["Total Hospital Expenditures"].loc["TOTAL"].reindex(YEARS)
ind["hcris_all_hosp_net_income"] = (ha["net_income"] / 1e6).reindex(YEARS)
ind["hcris_all_hosp_report_years"] = ha["n_report_years"].reindex(YEARS)
ind.to_csv(os.path.join(L.OUT, "independence_check.csv"), float_format="%.1f")

# ------------------------------------------------------------------ 3. user-cost variant (private provider industries)
sc = pd.read_csv(os.path.join(L.OUT, "scope_shares.csv"), index_col=0)
w = {"62101": 1.0, "622h1": 1.0, "62301": sc["scope_623"], "62401": sc["scope_624"]}
K = sum(L.nipa_series(f"k1n{c}es00", "fa") * w[c] for c in w)          # current-cost net stock, year-end, $ millions
D = sum(L.nipa_series(f"m1n{c}es00", "fa") * w[c] for c in w)          # current-cost depreciation
Inv = sum(L.nipa_series(f"i3n{c}es00", "fa") * w[c] for c in w)        # investment (nominal)
Kavg = (K + K.shift(1)) / 2; Kavg[YEARS[0]] = K[YEARS[0]]
priv = ["ambulatory_621", "hospitals_private_622", "nursing_residential_623_scoped", "home_community_62412_scoped"]
uc = pd.DataFrame(index=YEARS)
uc["net_stock_private_providers"] = K; uc["depreciation_private_providers"] = D; uc["investment_private_providers"] = Inv
uc["observed_capital_income_private"] = sum(acc[f"{p}.gos"] for p in priv) - acc["prov_prop_labor"] + acc["hosp_surplus_addon"]
for nm, r in (("central", B.PARAMS["real_return"][0]), ("low", B.PARAMS["real_return"][1]), ("high", B.PARAMS["real_return"][2])):
    uc[f"capital_services_{nm}"] = D + r * Kavg
    uc[f"residual_{nm}"] = uc["observed_capital_income_private"] - uc[f"capital_services_{nm}"]
uc["residual_central_pct_of_A_total"] = 100 * uc["residual_central"] / acc["A_total"]
uc["nhe_structures_equipment"] = acc["np.structures"] + acc["np.equipment"]
uc["sl_gov_health_cfc"] = acc["state_local_gov_hospitals_health.gos"]
uc.to_csv(os.path.join(L.OUT, "user_cost_variant.csv"), float_format="%.1f")

# ------------------------------------------------------------------ 4. charts (static PNG; palette = dataviz reference instance)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
BLUE, ORANGE, AQUA, YELLOW, MAGENTA = "#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac"
INK, MUTED, GRID = "#191919", "#666666", "#e6e6e6"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
                     "figure.facecolor": "white", "axes.facecolor": "white", "savefig.dpi": 200})
yy = [y for y in YEARS if nhe_ok[y]]

def title(ax, t, sub):
    ax.set_title(t, loc="left", color=INK, fontsize=12, fontweight="bold", pad=22)
    ax.text(0, 1.03, sub, transform=ax.transAxes, color=MUTED, fontsize=9)

XT = list(range(2000, yy[-1] + 1, 4))
def finish(fig, ax, name, right=0.74, bottom=0.12):
    ax.set_xticks(XT); fig.subplots_adjust(left=0.08, right=right, top=0.84, bottom=bottom)
    fig.savefig(os.path.join(DOCS, name)); plt.close(fig)

# fig 1: headline -- share of GDP
fig, ax = plt.subplots(figsize=(9, 4.8))
a = lev.loc[yy]
ax.fill_between(yy, 100 * a["income_side_total_A_low"] / a["gdp"], 100 * a["income_side_total_A_high"] / a["gdp"], color=BLUE, alpha=0.18, lw=0)
ax.plot(yy, a["nhe_share_gdp_pct"], color=ORANGE, lw=2); ax.plot(yy, a["income_side_share_gdp_pct"], color=BLUE, lw=2)
pb = 100 * a["income_side_provider_output"] / a["gdp"]; nb = 100 * a["nhe_provider_boundary"] / a["gdp"]
ax.plot(yy, nb, color=ORANGE, lw=2, ls=(0, (4, 2))); ax.plot(yy, pb, color=BLUE, lw=2, ls=(0, (4, 2)))
e = yy[-1]
ax.text(e + 0.4, a["nhe_share_gdp_pct"][e] + 0.3, "NHE total (CMS)", color=INK, va="center", fontsize=9)
ax.text(e + 0.4, a["income_side_share_gdp_pct"][e] - 0.3, "Income-side total", color=INK, va="center", fontsize=9)
ax.text(e + 0.4, nb[e] + 0.3, "NHE provider services", color=INK, va="center", fontsize=9)
ax.text(e + 0.4, pb[e] - 0.3, "Income-side providers", color=INK, va="center", fontsize=9)
ax.annotate("2020: CMS counts federal relief\nas spending; provider output fell", xy=(2020, a["nhe_share_gdp_pct"][2020]), xytext=(2009.3, 19.6),
            fontsize=8.5, color=MUTED, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.set_xlim(yy[0], e); ax.set_ylim(8, 20.5); ax.set_ylabel("% of GDP")
ax.plot([], [], color=ORANGE, lw=2, label="CMS expenditure side"); ax.plot([], [], color=BLUE, lw=2, label="Income side (this study)")
ax.plot([], [], color=MUTED, lw=2, ls=(0, (4, 2)), label="Dashed: provider block only")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.07), fontsize=8.5, ncol=3)
title(ax, "Income-side health spending tracks NHE within 1-2%, except 2020-22",
      "Percent of GDP. Band = low/high assumption scenarios.")
finish(fig, ax, "fig1_headline_share_of_gdp.png", bottom=0.16)

# fig 2: version B composition (share of total)
fig, ax = plt.subplots(figsize=(9, 4.8))
parts = [("Domestic labor", "B_labor", BLUE), ("Domestic capital income", "B_capital", ORANGE),
         ("Taxes less subsidies", "B_taxes", AQUA), ("Imports", "B_imports", YELLOW)]
tot = acc.loc[yy, "B_total"]; bot = np.zeros(len(yy))
for name, col, colr in parts:
    v = (100 * acc.loc[yy, col] / tot).values
    ax.bar(yy, v, bottom=bot, color=colr, width=0.82, edgecolor="white", linewidth=1.2, label=name)
    ax.text(yy[-1] + 0.8, bot[-1] + v[-1] / 2, f"{name}  {v[-1]:.0f}%", va="center", color=INK, fontsize=9)
    bot += v
ax.set_xlim(yy[0] - 0.8, yy[-1] + 0.6); ax.set_ylim(0, 100); ax.set_ylabel("% of income-side total"); ax.grid(axis="x", visible=False)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=4, fontsize=8.5)
title(ax, "Where the health dollar ends up (Version B)",
      "Share of income-side total after tracing supplier chains through input-output tables; imports at the border.")
finish(fig, ax, "fig2_versionB_composition.png", bottom=0.16)

# fig 3: growth rates
fig, ax = plt.subplots(figsize=(9, 4.6))
g = gr.loc[1999:yy[-1]]
for x0, x1 in ((2007.5, 2009.5), (2019.5, 2021.5)): ax.axvspan(x0, x1, color="#f2f2f2", lw=0)
for col, colr, lab in (("nhe_provider_boundary", ORANGE, "NHE provider services"), ("income_side_provider_output", BLUE, "Income-side provider output"),
                       ("provider_compensation_observed", AQUA, "Provider compensation (payroll-based)")):
    ax.plot(g.index, g[col], color=colr, lw=2, label=lab)
    ax.text(yy[-1] + 0.4, g[col][yy[-1]], lab, color=INK, fontsize=9, va="center")
ax.axhline(0, color=MUTED, lw=0.8); ax.set_ylabel("annual growth, %"); ax.set_xlim(1999, yy[-1])
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=3)
title(ax, "Provider block: income side fell in 2020 while NHE kept growing", "Annual percent change, current dollars. Shaded: 2008-09 and 2020-21.")
finish(fig, ax, "fig3_growth_rates.png", right=0.70, bottom=0.16)

# fig 4: statistical discrepancy
fig, ax = plt.subplots(figsize=(9, 4.4))
d = acc.loc[yy]
ax.fill_between(yy, d["discrepancy_pct_nhe_low"], d["discrepancy_pct_nhe_high"], color=BLUE, alpha=0.18, lw=0)
ax.plot(yy, d["discrepancy_pct_nhe"], color=BLUE, lw=2, label="Central (band = low/high assumptions)")
ax.plot(yy, d["discrepancy_ex_other_federal_programs_pct_nhe"], color=ORANGE, lw=2, label="Excluding 'other federal programs' relief funding")
ax.text(yy[-1] + 0.4, d["discrepancy_pct_nhe"][yy[-1]] + 0.2, "Central", color=INK, fontsize=9, va="center")
ax.text(yy[-1] + 0.4, d["discrepancy_ex_other_federal_programs_pct_nhe"][yy[-1]] - 0.2, "Excl. relief funding", color=INK, fontsize=9, va="center")
ax.axhline(0, color=MUTED, lw=0.8); ax.set_ylabel("% of NHE"); ax.set_xlim(yy[0], yy[-1])
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.07), ncol=2)
title(ax, "Statistical discrepancy: NHE minus income-side total", "Percent of NHE. Positive = CMS expenditure estimate exceeds the income traced here.")
finish(fig, ax, "fig4_discrepancy.png", right=0.80, bottom=0.16)

pd.set_option("display.width", 250); pd.options.display.float_format = "{:,.2f}".format
print(vol.loc["2000-2024 common window"].to_string())
print(vol.loc["2000-2019 pre-COVID"][["mean_growth_pct", "sd_growth_pct", "sd_change_in_growth_pp"]].to_string())
print((ind[["bea_comp_over_qcew_wages", "bea_gos_62_residual", "capital_income_independent_sum", "gap_bea_gos_minus_independent", "gap_pct_of_va_62",
            "hcris_all_hosp_total_revenue", "nhe_hospital_care"]].loc[[1998, 2000, 2005, 2010, 2015, 2019, 2021, 2023, 2024]]).to_string())
print(uc[["observed_capital_income_private", "capital_services_central", "residual_low", "residual_central", "residual_high", "residual_central_pct_of_A_total"]].loc[[1998, 2005, 2010, 2015, 2019, 2021, 2023, 2024]].to_string())
