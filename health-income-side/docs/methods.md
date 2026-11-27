# Methods note

All data were retrieved on 2026-11-27 from public, key-free URLs. Money is current dollars. The
account covers 1998–2024; the provider block alone extends to 2025.

**Tags used throughout**

| Tag | Meaning |
|---|---|
| OBS | Independently observed by the source agency from payroll, tax or financial filings |
| PUB | Published, but derived by the agency as a residual or from expenditure/revenue data |
| EST | Estimated here from published data with a stated rule |
| ASM | Assumption with no direct data; always carried with a low/high range |

## 1. Accounting framework

**Version A (direct).**

    Income-side total = provider final output + non-provider items
    Provider final output = Σ sectors (compensation + gross operating surplus + taxes less subsidies
                            + intermediate inputs) − intra-provider sales + hospital surplus add-on

**Version B (rolled up).** Every dollar of providers' intermediate inputs and of the non-provider
items is pushed through BEA input-output tables until it lands in domestic compensation, domestic
gross operating surplus, taxes on production less subsidies, or imports. Total B equals total A.

**Statistical discrepancy** = NHE − income-side total. Because non-provider items are taken from
NHEA, this equals (NHE provider services + state/local public health) − provider final output.

## 2. Boundary and double counting

| Issue | Treatment |
|---|---|
| Government providers | State/local: BEA "State and local government hospitals and health services" (general-government function). Federal (VA, IHS, civilian DoD): built from QCEW federal payroll. |
| State/local public health | Inside the BEA state/local health function, so it is compared with NHE state/local public health rather than taken from CMS. |
| Investment vs depreciation | NHE counts structures and equipment purchases and also provider revenue that recovers depreciation. The income-side total keeps both, to match the NHE boundary. `A_total_hce_basis` drops research and investment and is the clean total-cost measure, comparable to NHE health consumption expenditures. |
| Drugs used by providers vs retail | Drugs bought by hospitals and clinics are intermediate inputs of providers. Retail prescription drugs are a separate final item (CMS value, net of rebates). No overlap. |
| Wholesale and retail margins | Retail items are split into producer value, transport, wholesale and retail margins with the BEA PCE bridge, so each margin is counted once in the industry that earns it. |
| Sales among providers | Purchases of commodities 621–624 by provider sectors are removed (2023: $54 billion). |
| Nonprofit and government surplus | BEA values nonprofit and government output at cost, so their surplus is outside BEA gross output. CMS counts all hospital revenue, including non-operating revenue (Methodology Paper 2024, p. 7). The surplus is added from Medicare cost reports. |
| Out-of-scope parts of NAICS 623/624 | Assisted living (623312), other residential care (6239), child care and relief services are excluded by payroll-based scope shares. |

## 3. Sources, series and vintage

| Source | File / series | URL | Vintage | Used for | Tag |
|---|---|---|---|---|---|
| CMS NHEA | `NHE2024.csv` (type of service × source of funds, 1960–2024) | https://www.cms.gov/files/zip/national-health-expenditures-type-service-source-funds-cy-1960-2024.zip | File dated 2026-01-13; includes the 2024 benchmark revision | NHE totals; non-provider items; provider-services comparison | PUB |
| BEA GDP by industry | `GdpByInd.zip` → `KLEMS.xlsx` table TKG105 (composition of gross output) lines 685–693 (621), following blocks for 622, 623, 624 | https://apps.bea.gov/industry/Release/ZIP/GdpByInd.zip | Published 2026-09-30 | Gross output, compensation, taxes, GOS, energy/materials/services by provider industry | comp OBS-based; GOS PUB (residual) |
| BEA GDP by industry, underlying detail | `UGdpByInd.zip` → `GrossOutput.xlsx` UGO305 lines 367–380, 410; `ValueAdded.xlsx` UVA205 line 186 | https://apps.bea.gov/industry/Release/ZIP/UGdpByInd.zip | Published 2026-09-30 | Detail gross output (623 and 624 pieces; state/local hospitals and health) | PUB |
| BEA GDP by industry | `ValueAdded.xlsx` TVA113 (state/local general government), TVA105 | same zip as above | 2026-09-30 | Depreciation share of state/local value added; allocation of net interest | PUB |
| BEA input-output | `IOUse_Before_Redefinitions_PRO_1997-2023_Summary.xlsx`, `IOMake_Before_Redefinitions_PRO_1997-2023_Summary.xlsx`, `IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx` | https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip | 2024-09-26 (older than the 2026 industry accounts; used for coefficients only) | Version B roll-up; intra-provider sales; state/local hospital input mix (column GSLGH) | PUB |
| BEA import matrices | `ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx` | https://apps.bea.gov/industry/xls/io-annual/ImportMatrices_Before_Redefinitions_SUM_1997-2023.xlsx | 2024-09-26 | Imported share of intermediate and final purchases | PUB (BEA import-proportionality assumption) |
| BEA PCE bridge | `PCEBridge_Summary.xlsx` (annual), NIPA lines 40 (pharmaceutical and other medical products) and 21 (therapeutic appliances and equipment); `PCEBridge_Detail.xlsx` (industry code concordance sheet) | https://apps.bea.gov/industry/release/xlsx/PCEBridge_Summary.xlsx | 2026-09-30; detail 2025-06-13 | Producer value, transport, wholesale and retail margin shares | PUB |
| BEA NIPA | `NipaDataA.txt`: A191RC (GDP), B230RC (population), DHLCRC and DHLCRG (PCE health care services, value and price index) | https://apps.bea.gov/national/Release/TXT/NipaDataA.txt | 2026-11-25 | Comparisons | PUB |
| BEA NIPA income tables | Table 6.12D line 24 (N1822C, proprietors' income); 6.13D line 23 (N1722C); 6.15D line 21 (N1869C); 6.17D line 70 (N3074C); 6.22D line 69 (N7791C); 6.2D/6.3D line 89 (B4079C, B4179C: federal civilian compensation and wages) | same file | 2026-11-25; "D" tables start in 1998 | Proprietor labor imputation; independent capital income; federal compensation ratio | OBS-based (IRS SOI with BEA adjustments) |
| BEA fixed assets | `FixedAssets.txt`: k1n62101es00, k1n622h1es00, k1n62301es00, k1n62401es00 (net stock); m1n… (depreciation); i3n… (investment) | https://apps.bea.gov/national/FixedAssets/Release/TXT/FixedAssets.txt | 2026-09-30 | User-cost variant | PUB (perpetual inventory) |
| BEA detailed fixed assets | `detailnonres_inv1.xlsx`, sheets 6210, 622H, 6230 | https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_inv1.xlsx | 2026-09-30 | Commodity mix of health equipment investment | PUB (BEA warns detail is lower quality) |
| BLS QCEW | National annual wages by ownership, NAICS 62 detail; see `data/inputs/qcew_NOTES.md` | https://data.bls.gov/cew/data/api/<year>/a/industry/<naics>.csv (2014–2025); https://data.bls.gov/cew/data/files/<year>/csv/<year>_annual_by_industry.zip (1997–2013) | 2025 file dated 2026-08-21 | Scope shares for 623/624; federal provider payroll; payroll check | OBS |
| CMS Medicare cost reports (HCRIS) | Forms 2552-96 and 2552-10, Worksheet G-3; see `data/inputs/hcris_NOTES.md` | https://downloads.cms.gov/files/hcris/HOSP10FY<year>.zip, HOSPFY<year>.zip | Files dated 2026-10-05 | Hospital surplus; depreciation; revenue cross-check | OBS (mostly unaudited filings) |
| BLS CPI and PPI | CUUR0000SA0, SAM, SAM2, SEMF01, SEMD; PCU622110622110, PCU621111621111 (annual averages) | https://api.bls.gov/publicAPI/v2/timeseries/data/ | Retrieved 2026-11-27 | Comparisons | OBS |
| KFF Employer Health Benefits Survey | Average single and family premiums, 1999–2026 | https://files.kff.org/attachment/Tables-EHBS-2026-Section-01.xlsx (Figure 1.12) | 2026 survey | Comparisons | OBS (survey) |

Sources evaluated but not used in the estimate are listed, with the status of each URL, in
`data/inputs/source_availability.md`. The main ones:

| Source | Status | Why not used |
|---|---|---|
| FRED | Unreachable from this environment (timeout) | BLS API and BEA flat files used instead |
| `download.bls.gov`, BLS productivity pages | HTTP 403 with a generic User-Agent | BLS public API used instead |
| OECD ICIO / TiVA | HTTP 403 (bot challenge) | Imports are shown at the border, not traced abroad |
| BEA–BLS KLEMS production account | Reachable, 1997–2024 | Combines hospitals with nursing homes; BEA industry KLEMS table used |
| BEA health care satellite account | Reachable, 2000–2021 | Disease-based; not an income account |
| Census Service Annual Survey, 2022 Economic Census | Reachable, latest 2022 | Already embedded in BEA output and CMS revenue; public SAS tables carry a "disclosure prohibited" cover sheet that needs a human check |
| CMS medical loss ratio files | Reachable, 2011–2024 | Would replace the CMS insurer net cost only after 2011; listed as a gap |
| IRS SOI corporation, partnership, S-corporation tables; Form 990 extracts | Reachable | Used indirectly through NIPA tables 6.12D–6.22D; direct use listed as a gap |
| SEC EDGAR XBRL frames | API reachable | Firm-level, global; cannot be allocated to US health spending |
| BEA–CMS reconciliation (SCB Sept 2010; BEA WP2020-8) | Both reachable | Used to check boundary treatment |

## 4. Provider block, sector by sector

| Sector | Gross output and components | Tag |
|---|---|---|
| Ambulatory care (621) | BEA, unadjusted | PUB |
| Private hospitals (622) | BEA, unadjusted | PUB |
| Nursing and residential (623) | BEA 623 × scope share. Scope share = BEA detail output of the two 623 sub-industries weighted by private QCEW wage shares: (6231 + 623311) / (6231 + 6233) and 6232 / (6232 + 6239). 82–87% across years. | EST |
| Home and community services (62412) | BEA 624 × [individual and family services share of 624 output] × [QCEW private wages 62412 / 6241] × inclusion share. | EST × ASM |
| State/local government hospitals and health | BEA gross output and value added. Depreciation share of value added = 2017 benchmark (GSLGH: 17,879 / 157,195) moved with the all state/local general-government ratio. Energy/materials/services split copied from private hospitals. | PUB; split EST |
| Federal direct providers | Compensation = QCEW federal-ownership wages in NAICS 621–623 × federal civilian compensation/wages (NIPA 6.2D/6.3D). Gross output = compensation × private-hospital output/compensation × multiplier. Depreciation at the state/local rate. | EST × ASM |

**Other provider-block items**

- **Intra-provider sales (EST).** Each sector's intermediate inputs × the share of commodities
  621–624 in its I-O column.
- **Proprietor labor (ASM).** Proprietors' income for health care and social assistance (NIPA
  6.12D) is allocated to in-scope sectors by gross operating surplus, then split into labor and
  capital by an assumed labor share. Owner-physicians paid through S-corporations are already in
  compensation; their profit stays in capital income.
- **Hospital surplus add-on (OBS).** Net income (Worksheet G-3) of nonprofit and non-federal
  government hospitals, prorated to calendar years. The surplus rate is applied to cost-report
  operating expenses. For 2025, where filings are 77% complete, expenses are moved from 2024 with
  BEA hospital output (EST, flagged in the output column `hosp_surplus_is_estimate`).

## 5. Non-provider items and their roll-up

Levels are CMS NHEA values (PUB). The commodity each is assigned to for Version B:

| Item | I-O treatment | Tag |
|---|---|---|
| Retail prescription drugs | PCE bridge line 40 shares by year: producer value (mostly chemical products, 325), truck transport, wholesale, other retail. Import share of the goods = PCE import share of that commodity in the import matrix. | EST |
| Other non-durable medical products | Same vector as retail drugs | EST |
| Durable medical equipment | PCE bridge line 21 shares | EST |
| Net cost of health insurance | Insurance carriers and related activities (524), all domestic | EST (524 mixes all insurance lines and agencies) |
| Government administration | Federal → federal nondefense general government; state/local → state/local general government | EST |
| Federal public health | Federal nondefense general government | EST |
| Research | 60% educational services, 25% miscellaneous professional and scientific services, 15% federal nondefense | ASM (no range run; 1.4% of total) |
| Structures | Construction | EST |
| Equipment (includes software) | BEA detailed investment mix of industries 621–623 mapped to commodities, plus trade and transport margins at the economy-wide equipment rate | EST |

**Roll-up model.** Industry-technology Leontief model on the 71-industry tables, with domestic and
imported requirements separated by the import matrix:

    x = (I − B_d D)⁻¹ f_d ;  g = D x ;  value added_k = v_k′ g ;  imports = f_m + 1′ B_m g

A self-test on 2017 total final demand reproduces GDP components to 0.3% with zero leakage.
Years 2024 and 2025 use 2023 coefficients (EST). Provider value added always comes from the 2026
vintage; the 2024-vintage tables supply coefficients only. The labor imputation for proprietors is
applied to provider industries only, not to supplying industries.

## 6. Assumptions and ranges

| Parameter | Central | Low | High | Effect on 2024 total |
|---|---:|---:|---:|---|
| Share of NAICS 62412 output inside the NHE boundary | 0.85 | 0.70 | 1.00 | about ±$19 billion |
| Federal providers' output/compensation relative to private hospitals | 0.75 | 0.60 | 1.00 | −$22 to +$37 billion |
| Labor share of proprietors' income | 0.67 | 0.50 | 0.85 | none on the total; moves $23–25 billion between labor and capital |
| Hospital surplus added | full net income | operating only (excludes investment income and contributions) | full net income | −$27 billion in the low scenario |
| Real required return (user-cost variant) | 5% | 3% | 7% | variant only |

The low and high scenarios move all parameters together, so the band is an outer envelope, not a
confidence interval. Sampling and revision error in the source data is not included.

## 7. Independence of each component

| Component | Status |
|---|---|
| Employee compensation, private providers | Observed: BEA builds it from QCEW unemployment-insurance wage records plus employer benefit data. Check: BEA compensation / QCEW wages for 621–623 is 1.21–1.26 in every year. |
| Compensation, state/local government health | BEA, from government payroll data; the split from depreciation is estimated |
| Compensation, federal providers | QCEW observed wages × estimated benefit ratio; uniformed military medical staff are not covered |
| Gross operating surplus, private providers | Residual in BEA's accounts (output − intermediate inputs − compensation − taxes) |
| Hospital surplus | Observed in cost-report filings |
| Proprietor labor | Assumed share of observed proprietors' income |
| Taxes less subsidies | BEA allocation of observed tax and subsidy flows |
| Intermediate inputs | BEA benchmark expense surveys, extrapolated between benchmarks |
| Provider gross output | Revenue surveys (Census), the same surveys CMS uses for most provider categories |
| Non-provider items | CMS expenditure estimates; not independent |
| Supplier-chain decomposition | Derived (I-O coefficients) |
| Imports | Derived (BEA import matrices assume each industry uses imports in proportion to economy-wide supply) |

**Independent capital income.** For private NAICS 62, an alternative total is built from corporate
profits before tax (6.17D) + corporate capital consumption allowances (6.22D) + proprietors' income
(6.12D) + noncorporate capital consumption allowances (6.13D) + net interest (6.15D, allocated from
the education-plus-health line by value added, EST) + nonprofit hospital depreciation (HCRIS). It
exceeds BEA's residual by $15–70 billion (2.6–7.0% of value added). Known reasons it is not exact:
tax depreciation differs from economic depreciation; corporate profits include non-operating
income; nonprofit providers other than hospitals are missing; cost-report depreciation is missing
for 2002–04. Year-by-year values are in table I1 of `tables.md`.

## 8. Known weaknesses

- **Shared sources.** BEA provider output and CMS provider spending both rest on the Census Service
  Annual Survey and Economic Census, so a small discrepancy does not validate either.
- **QCEW break in 2013.** Private NAICS 62412 employment jumps 72% in 2013, most likely a
  reclassification of home-care workers out of private households (not verified against a BLS
  notice). The 62412 scope share is therefore understated before 2013, which lowers income-side
  output by an amount inside the scenario band.
- **Cost-report outliers.** Net income is sensitive to the outlier rule: 562 reports with net
  patient revenue above twice operating expenses were dropped (−$124 billion of net income over all
  years); 1,935 borderline reports were kept and may overstate recent net income by $7–11 billion a
  year. Filings for 2024–25 are mostly as-submitted.
- **Ownership codes.** The cost-report control-type list (1–2 nonprofit, 3–6 for-profit, 7 federal,
  8–13 other government) could not be confirmed against a CMS document.
- **Rebates.** CMS retail drug spending is net of manufacturer rebates, but the BEA margin shares
  come from gross sales, so pharmacy and wholesale shares of the retail drug dollar are approximate.
- **State/local health function.** It may include small non-NHE activities (environmental health)
  and its 2017 input mix is held fixed in all years.
- **1997.** Not produced: the NAICS-based NIPA income tables start in 1998.
- **2025.** Only the provider block exists; CMS has not published NHEA 2025.
