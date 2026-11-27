# Income-side estimate of US health care spending, 1998–2024

Measures US health spending as the income it generates (labor, capital income, taxes, intermediate
inputs, imports) and compares it with the CMS National Health Expenditure Accounts. Public data
only; no API keys.

| Deliverable | File |
|---|---|
| Findings summary and headline chart | [docs/findings.md](docs/findings.md) |
| Year-by-year tables (Version A, Version B, reconciliation, checks) | [docs/tables.md](docs/tables.md) |
| Methods note: series, URLs, vintages, assumptions | [docs/methods.md](docs/methods.md) |
| Gaps and the restricted data that would close them | [docs/gaps.md](docs/gaps.md) |
| Availability check of every candidate source | [data/inputs/source_availability.md](data/inputs/source_availability.md) |
| Assembled data | `data/output/*.csv`, `data/inputs/*.csv` |
| Charts | `docs/fig1`–`fig4` `.png` |

## Reproduce

```bash
cd health-income-side/code
bash 00_download.sh                          # BEA + CMS bulk files (~150 MB) into data/raw/health_income/
python3 -I 10_hcris_hospital_financials.py   # Medicare cost reports (~3.4 GB download, ~5 min)
python3 -I 11_qcew_health_wages.py           # QCEW payroll by ownership (~8 min)
python3 -I 12_comparison_series.py           # CPI, PPI, KFF premiums
python3 20_build_accounts.py                 # Versions A and B, three scenarios
python3 30_analysis.py                       # comparisons, independence check, user-cost variant, charts
python3 40_make_tables.py                    # docs/tables.md
```

Needs Python 3 with pandas, numpy, openpyxl and matplotlib. Raw downloads are git-ignored; the
assembled inputs and outputs are committed.

## Main output columns (`data/output/income_side_health_account.csv`, $ millions)

| Column | Meaning |
|---|---|
| `A_total`, `A_total_low`, `A_total_high` | Income-side total on the NHE boundary, central and scenario range |
| `A_total_hce_basis` | Same, excluding research and investment (comparable to NHE health consumption expenditures) |
| `prov_*` | Provider block: gross output, compensation, surplus, taxes, intermediate inputs, intra-provider sales, imputed proprietor labor |
| `hosp_surplus_addon` | Nonprofit and government hospital surplus from Medicare cost reports |
| `np.*` | Non-provider items taken from CMS |
| `B_*` | Version B decomposition into domestic labor, capital income, taxes, imports |
| `nhe_*`, `discrepancy*` | CMS comparators and the statistical discrepancy |
| `<sector>.<component>` | Sector detail (also in `provider_sectors_detail.csv`) |
