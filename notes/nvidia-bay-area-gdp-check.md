# Nvidia and Bay Area GDP: fact-check of the back-of-envelope memo

Checked 2026-09-10 against primary sources (Nvidia 10-K/10-Q filings on
EDGAR, BEA regional and industry tables downloaded key-free from
`apps.bea.gov/regional/zip/` and `apps.bea.gov/industry/Release/ZIP/`,
FRED, the Epoch AI article, and the SF Bay Area Times article).

## 1. Nvidia US-booked income (memo table is wrong for 2024 and 2025)

Nvidia's 10-K income-tax note discloses "Income before income tax: U.S. /
Foreign". Fiscal years end in late January, so FY(t+1) ≈ calendar year t.

| Fiscal year (≈ CY) | US pre-tax income | Foreign | Total | US share | Total operating income |
|---|---|---|---|---|---|
| FY2023 (≈2022) | $3.5B  | $0.7B | $4.2B | 83% | $4.2B |
| FY2024 (≈2023) | $29.5B | $4.3B | $33.8B | 87% | $33.0B |
| FY2025 (≈2024) | $77.5B | $6.6B | $84.0B | 92% | $81.5B |
| FY2026 (≈2025) | $123.2B | $18.3B | $141.5B | 87% | $130.4B |

Source: 10-K filings 0001045810-24-000029, -25-000023, -26-000021.

FY2027 to date (CY2026): GAAP operating income $53.5B (Q1) + $63.7B (Q2) =
$117.3B for H1; Q3 guidance $108B revenue, 74% gross margin, $9.2B opex
(≈$70.7B operating income). A flat-to-modestly-rising Q4 implies FY2027
operating income of roughly $258–267B, i.e. US-booked ≈ $225–245B.

Memo vs. filings:

| Memo row | Memo US-booked level | Filing | Memo increment | Recomputed increment |
|---|---|---|---|---|
| 2024 | $53–57B "from ~$17–18B" | $77.5B from $29.5B | $36–40B | **$48.0B** |
| 2025 | $115–125B | $123.2B | $60–70B | **$45.7B** (≈$50B if the $4.5B H20 charge is added back) |
| 2026 | $210–230B | ≈$225–245B (H1 actual + guidance) | $90–110B | **≈$100–125B** |

The 2024 and 2023 levels in the memo do not match any disclosed figure. The
2025 level is right, so the memo's 2025 increment is overstated because its
2024 base is too low.

## 2. Bay Area understatement, recomputed

Bay Area = 13-county San Jose–San Francisco–Oakland CSA, summed from BEA
CAGDP1 county current-dollar GDP: 2022 $1,252.3B, 2023 $1,322.2B,
2024 $1,408.3B (memo's $1.408T confirmed). 2025 assumed ≈ +6.5% ($1.50T)
since official 2025 county GDP is not out until Dec 2026.

Using a 50–70% Bay Area share of the increment (memo's assumption) over
prior-year Bay Area GDP:

| Year | Increment | Bay Area share | Understatement (pp) | Memo |
|---|---|---|---|---|
| 2024 | $48.0B | $24–34B | **1.8–2.5 (central 2.2)** | 1.4–2.1 (1.7) |
| 2025 | $45.7B | $23–32B | **1.6–2.3 (central 1.9)** | 2.1–3.5 (2.8) |
| 2026 | $102–123B | $51–86B | **3.4–5.7 (central 4.5)** | 3.2–4.8 (4.0) |

Cumulative 2024–26 at a 60% share: ≈ $123B ≈ 9.3pp of 2023 Bay Area GDP
(memo: ~8.5pp). National equivalents: 0.17pp (2024), 0.16pp (2025),
0.33–0.40pp (2026) vs memo 0.13 / 0.2 / 0.3. Epoch's own headline is
"about 0.3 percentage points" in recent quarters and ~1.8pp by Q4 2028.

## 3. Epoch AI article: correctly cited

"The Nvidia-sized hole in US GDP statistics", Epoch AI, Aug 24, 2026
(Juniewicz, Carey, Trammell, Ho). Proxy = Nvidia US-booked operating
income, adjusted for the H20 inventory charge and calendarized; they treat
all of it as missing and call this conservative. They cite ~$120B pre-tax
income Jan 2025–Jan 2026, ~$30B/quarter gap in 2025, 0.3pp understatement,
1.78pp by Q4 2028. They note GDI does capture it. They do not discuss
regional GDP. Other fabless firms (AMD, Broadcom, Qualcomm, Marvell) barely
change the total.

## 4. "Will it show up in official figures?" — largely right

- BEA's county GDP methodology (SCB, March 2020) states the regional program
  "relies on the income approach" and that "the initial regional estimates
  are then scaled to the national estimates so that all BEA estimates are
  reconciled." BEA's *GDP by State: Concepts and Methodology* says the
  state estimates "are consistent with national totals of the GDP by
  Industry Accounts" and that the allocation "yields an additive system in
  which state estimates sum to the national estimate." Manufacturing gross
  operating surplus is allocated with Economic Census and Annual Survey of
  Manufactures value added and payroll, not with corporate profits by
  location. So the regional accounts
  redistribute, but cannot add, the missing national total. Confirmed.
- BEA underlying-detail table UVA205: 2024 value added of "Semiconductor and
  other electronic component manufacturing" = **$111.4B**; all "Computer and
  electronic products" = **$299.8B**. Nvidia's US pre-tax income for CY2025
  ($123.2B) alone exceeds the whole semiconductor industry's 2024 value
  added. Memo's "~$100–150B" is right. Real semiconductor value added grew
  only 6.5% in 2024, contributing 0.02pp to US GDP growth.
- BEA's June 2026 preview of the Sept 30, 2026 national annual update and
  the Aug 2026 regional preview list no changes for factoryless goods
  producers, merchanting, or semiconductor exports. BEA's FGP research page
  says research "is currently being undertaken" with no timeline. Epoch
  reports BEA has "no plans" to change core accounts. The memo's wording
  "Sept 30 update lists none" is slightly premature (release is Sept 30;
  the preview is what exists today) but substantively correct.
- The memo's "realistic fix window ~2028–2030" is speculation. The next
  comprehensive update would fall around 2028 on the 5-year cadence
  (last: Sept 2023), but BEA has not announced one.
- Caveat on "watch the GDP–GDI wedge": GDI is currently *below* GDP
  (FRED: −0.9% in Q1 2026, −0.7% in Q2 2026), the opposite sign of what a
  Nvidia-only story predicts, so the wedge is a noisy signal.

## 5. Bay Area vs LA: geography error

- Bay Area 13-county 2024 = $1,408.3B. Confirmed.
- "LA CSA" $1,424.3B is **Los Angeles + Orange + Ventura only**. The official
  Los Angeles–Long Beach CSA (OMB Bulletin 23-01) also includes Riverside and
  San Bernardino; its 2024 GDP is **$1,697.0B** (BEA CAGDP1 sum).
- The SF Bay Area Times "2025 estimate" ($1.521T vs $1.488T) is just the
  2024 official figures grown by assumed 8.0% (Bay) and 4.5% (LA). No 2025
  county data exist yet. BEA state data show California nominal GDP grew
  5.0% in 2025 (SAGDP1), below the 5.8% of 2023–24, so 8.0% for the Bay
  Area is an aggressive assumption, not an observation.
- On a 3-county LA basis the crossover is plausible but unconfirmed; on the
  official 5-county CSA basis LA leads by ~$290B and would still lead in
  2026 (~$1.85T) even after adding $105–170B of Nvidia income to the Bay
  Area (~$1.69–1.79T).

## 6. Other checks

- Nvidia FY ends last Sunday in January: ~1 month offset. Correct.
- "Some share gain may already be in official figures": BEA CAGDP2 shows
  Santa Clara County durable-goods manufacturing value added *fell* from
  $75.4B (2021) to $71.4B (2024) while California "Computer and electronic
  product manufacturing" was flat at ~$128B (2022–24). No visible Nvidia
  effect in the official regional manufacturing numbers so far.
- Bay Area share of Nvidia income (50–70%) remains a judgment. 10-K: ~42,000
  employees in 38 countries, ~6,000 in Israel, HQ in Santa Clara with ~3M
  sq ft owned/leased. No disclosure of US or Bay Area headcount.
- Nominal/real mixing: Bay Area real GDP growth was 4.4% in 2024 vs 6.5%
  nominal; the pp understatement figures above are nominal.

## 7. Real-terms follow-up: Bay Area vs LA vs Florida

`notes/figures/real_gdp_race.tex` (pgfplots; compile with `pdflatex`) plots
real GDP in chained 2017 dollars from BEA CAGDP1/SAGDP1, with projections at
2019–24 real CAGRs (Bay Area 3.3%, LA 1.4%; Florida at its 2025 pace, 3.0%)
and a band adding 50–70% of Nvidia's US income deflated by the US GDP price
index. Data in `real_gdp_race_data.csv`.

In real terms the picture differs from nominal: the Bay Area's 2024 gap to the
official 5-county LA CSA is 10% ($1,216B vs $1,351B), not 20%, because the Bay
Area's industry mix carries lower implied prices. On the official trend the Bay
Area still trails LA ($1.34T vs $1.41T) and Florida ($1.48T) in 2027. With the
Nvidia correction ($1.46–1.56T) it passes the LA CSA and its upper half passes
Florida. Chained-dollar county sums are approximate.
