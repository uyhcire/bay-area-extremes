"""Plot the median college wage premium (top) and the HS/BA unemployment-rate ratio (bottom).

Reads analysis/output/{college_premium,unemployment_gap}_longrun.csv -> analysis/output/college_premium_longrun.png
Two panels on one time axis rather than two y-scales on one plot: the measures have different units.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
r = pd.read_csv("analysis/output/college_premium_longrun.csv")
# NBER through 2024, Census files after
s = pd.concat([r[r.source == "nber_morg"], r[(r.source == "census_basic") & (r.year > 2024)]]).set_index("year")
last = int(s.index.max()); months = int(s.months.iloc[-1])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
u = pd.read_csv("analysis/output/unemployment_gap_longrun.csv")
u = pd.concat([u[(u.source == "nber_morg") & (u.year < 2025)], u[(u.source == "census_basic") & (u.year > 2024)]]).set_index("year")
fig, (ax, ax2) = plt.subplots(2, 1, figsize=(10.5, 8.6), dpi=200, facecolor=SURF, sharex=True,
                              gridspec_kw={"height_ratios": [3, 2], "hspace": 0.16})
ax.set_facecolor(SURF); ax2.set_facecolor(SURF)
ax.plot(s.index, s.raw, color=ORANGE, lw=2, solid_capstyle="round")
ax.plot(s.index, s.adj, color=BLUE, lw=2, solid_capstyle="round")
for col, c in (("raw", ORANGE), ("adj", BLUE)):
    ax.plot([last], [s[col].iloc[-1]], "o", ms=6, color=c, mec=SURF, mew=1.5, zorder=5)
pk = s.adj.idxmax()
ax.annotate(f"{s.adj[1979]:.2f}", (1979, s.adj[1979]), xytext=(0, -15), textcoords="offset points", ha="center", color=INK2, fontsize=10)
ax.annotate(f"peak {pk}: {s.adj[pk]:.2f}", (pk, s.adj[pk]), xytext=(-8, 16), textcoords="offset points", ha="right", color=INK2, fontsize=10)
ax.annotate(f"Adjusted  {s.adj.iloc[-1]:.2f}", (last, s.adj.iloc[-1]), xytext=(9, -4), textcoords="offset points", color=INK, fontsize=10.5)
ax.annotate(f"Raw  {s.raw.iloc[-1]:.2f}", (last, s.raw.iloc[-1]), xytext=(9, -4), textcoords="offset points", color=INK, fontsize=10.5)
h = [plt.Line2D([], [], color=BLUE, lw=2), plt.Line2D([], [], color=ORANGE, lw=2)]
ax.legend(h, ["Adjusted for experience, sex, race/ethnicity (median regression)", "Raw gap between group medians"],
          loc="lower right", bbox_to_anchor=(0.93, 0.03), frameon=False, fontsize=10, labelcolor=INK2, handlelength=1.6)
REC = [(1980, 1982.9, "1980–82"), (1990.5, 1991.2, "1990–91"), (2001.2, 2001.9, "2001"), (2007.9, 2009.5, "2007–09"), (2020.1, 2020.3, "2020")]
for a in (ax, ax2):
    for x0, x1, _ in REC:
        a.axvspan(x0, x1, color=GRID, alpha=0.7, lw=0)
ax.text(1981.45, 0.985, "recessions\nshaded", transform=ax.get_xaxis_transform(), ha="center", va="top", color=INK2, fontsize=9)
u["ratio"] = u.u_hs / u.u_ba
ax2.plot(u.index, u.ratio, color=AQUA, lw=2, solid_capstyle="round")
ax2.plot([last], [u.ratio.iloc[-1]], "o", ms=6, color=AQUA, mec=SURF, mew=1.5, zorder=5)
ax2.annotate(f"{u.ratio.iloc[-1]:.1f}×", (last, u.ratio.iloc[-1]), xytext=(9, -4), textcoords="offset points", color=INK, fontsize=10.5)
for y, dy in ((1979, -15), (1982, 7), (2000, 7), (2010, 9)):
    ax2.annotate(f"{u.ratio[y]:.1f}", (y, u.ratio[y]), xytext=(0, dy), textcoords="offset points", ha="center", color=INK2, fontsize=10)
ax2.set_title("Unemployment ratio: high-school rate divided by college rate", loc="left", color=INK, fontsize=11.5, pad=8)
ax2.set_ylim(1.5, 3.1); ax2.set_yticks([1.5, 2.0, 2.5, 3.0]); ax2.set_ylabel("ratio", color=INK2)
ax2.yaxis.grid(True, color=GRID, lw=1); ax2.set_axisbelow(True)
for sp in ("top", "right", "left"): ax2.spines[sp].set_visible(False)
ax2.spines["bottom"].set_color(GRID); ax2.tick_params(colors=INK2, length=0)
ax.set_xlim(1978, last + 6); ax.set_xticks(range(1980, last + 1, 5))
lo = np.floor(min(s.adj.min(), s.raw.min()) * 10) / 10
ax.set_ylim(lo, np.ceil(max(s.adj.max(), s.raw.max()) * 10) / 10 + 0.02)
ax.yaxis.grid(True, color=GRID, lw=1); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, length=0)
ax.set_ylabel("log points", color=INK2)
fig.suptitle("Median college wage premium, 1979–%d" % last, x=0.065, y=0.982, ha="left", fontsize=15, color=INK, fontweight="bold")
fig.text(0.065, 0.925, "Log hourly wage gap, bachelor’s degree or more vs. exactly high school. Wage and salary workers aged 18–64.",
         color=INK2, fontsize=10.5)
fig.text(0.065, 0.012, f"Source: CPS outgoing rotation groups (NBER extracts 1979–2024, Census basic monthly files 2025–{last}). "
         f"{last} is the first {months} available months.\nMedians, so top-coding does not enter. Imputed earnings excluded where flagged "
         "(flags incomplete 1989–95). Education coding changes in 1992.\nUnemployment: same ages, exactly high school vs. bachelor’s or more; labour-force questions redesigned in 1994.", color=INK2, fontsize=8.5, va="bottom")
fig.subplots_adjust(left=0.065, right=0.985, top=0.895, bottom=0.115)
fig.savefig("analysis/output/college_premium_longrun.png", facecolor=SURF)
