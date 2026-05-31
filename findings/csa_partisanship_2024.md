# 20 largest U.S. CSAs, ranked by how Democratic they voted (2024)

The 20 most populous U.S. Combined Statistical Areas (CSAs), ranked by their
**two-party Democratic vote share** in the 2024 presidential election:
`votes_dem / (votes_dem + votes_gop)`. "Margin" is `(dem − gop) / total_votes`.
These are whole CSAs (urban core + exurbs), so they run more Republican than the
central city alone.

| # | CSA | 2-party Dem % | Margin | Pop (2023) |
|---|-----|--------------:|-------:|-----------:|
| 1 | San Jose–San Francisco–Oakland, CA | **70.4%** | +39.4 | 9.0M |
| 2 | Seattle–Tacoma, WA | 66.0% | +30.9 | 5.0M |
| 3 | Washington–Baltimore–Arlington, DC-MD-VA-WV-PA | 63.7% | +26.7 | 10.1M |
| 4 | Chicago–Naperville, IL-IN-WI | 61.4% | +22.5 | 9.8M |
| 5 | Portland–Vancouver–Salem, OR-WA | 61.4% | +22.0 | 3.3M |
| 6 | Denver–Aurora–Greeley, CO | 60.8% | +21.0 | 3.7M |
| 7 | Philadelphia–Reading–Camden, PA-NJ-DE-MD | 60.5% | +20.8 | 7.4M |
| 8 | Boston–Worcester–Providence, MA-RI-NH | 60.4% | +20.3 | 8.3M |
| 9 | Los Angeles–Long Beach, CA | 59.3% | +18.0 | 18.3M |
| 10 | New York–Newark, NY-NJ-CT-PA | 57.4% | +14.6 | 21.9M |
| 11 | Minneapolis–St. Paul, MN-WI | 56.7% | +13.2 | 4.1M |
| 12 | Detroit–Warren–Ann Arbor, MI | 54.1% | +8.1 | 5.4M |
| 13 | Atlanta–Athens-Clarke–Sandy Springs, GA-AL | 53.9% | +7.7 | 7.2M |
| 14 | Cleveland–Akron–Canton, OH | 49.4% | −1.1 | 3.7M |
| 15 | Miami–Port St. Lucie–Fort Lauderdale, FL | 49.0% | −2.0 | 7.0M |
| 16 | Phoenix–Mesa, AZ | 47.2% | −5.6 | 5.1M |
| 17 | Houston–Pasadena, TX | 45.9% | −8.0 | 7.7M |
| 18 | Orlando–Lakeland–Deltona, FL | 45.5% | −8.9 | 4.5M |
| 19 | Charlotte–Concord, NC-SC | 45.5% | −8.9 | 3.4M |
| 20 | Dallas–Fort Worth, TX-OK | 44.7% | −10.4 | 8.7M |

## Takeaways

- The **San Jose–San Francisco–Oakland CSA is the standout** — 70% two-party
  Democratic, a ~10-point gap above #2 Seattle.
- All 13 of the top CSAs went Democratic; the bottom 7 (Cleveland down through
  Dallas–Fort Worth) all leaned Republican in 2024, with the three Texas/Florida
  Sun Belt metros and Charlotte the most so.
- Because these are whole CSAs, the urban cores of Houston, Dallas, and Phoenix
  are blue but get pulled red by their outer counties.

## Sources & method

- County → CSA crosswalk: Census 2023 metro/CSA delineation (`list1_2023`).
- CSA populations (to pick the largest 20): Census PEP `csa-est2023-alldata`.
- County presidential returns: `tonmcg/US_County_Level_Election_Results_08-24`
  (AP / state-certified). No single official `.gov` county CSV exists.

Every county in all 20 CSAs matched the returns file — no coverage gaps.

## Reproduce

```bash
scripts/download_csa_geography.sh
scripts/download_election_returns.sh 2024
scripts/rank_csa_partisanship.py --year 2024 --top 20 --out findings/csa_partisanship_2024.csv
```

The full ranked table (all numeric precision) is in
[`csa_partisanship_2024.csv`](csa_partisanship_2024.csv).
