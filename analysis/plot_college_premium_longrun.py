"""Plot analysis/output/college_premium_longrun.csv -> analysis/output/college_premium_longrun.png"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE = "#2a78d6", "#eb6834"
r = pd.read_csv("analysis/output/college_premium_longrun.csv")
# NBER through 2024, Census files after
s = pd.concat([r[r.source == "nber_morg"], r[(r.source == "census_basic") & (r.year > 2024)]]).set_index("year")
last = int(s.index.max()); months = int(s.months.iloc[-1])

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11})
fig, ax = plt.subplots(figsize=(10.5, 6), dpi=200, facecolor=SURF)
ax.set_facecolor(SURF)
ax.plot(s.index, s.raw, color=ORANGE, lw=2, solid_capstyle="round")
ax.plot(s.index, s.adj, color=BLUE, lw=2, solid_capstyle="round")
for col, c in (("raw", ORANGE), ("adj", BLUE)):
    ax.plot([last], [s[col].iloc[-1]], "o", ms=6, color=c, mec=SURF, mew=1.5, zorder=5)
pk = s.adj.idxmax()
ax.annotate(f"{s.adj[1979]:.2f}", (1979, s.adj[1979]), xytext=(0, -15), textcoords="offset points", ha="center", color=INK2, fontsize=10)
ax.annotate(f"peak {pk}: {s.adj[pk]:.2f}", (pk, s.adj[pk]), xytext=(0, 9), textcoords="offset points", ha="center", color=INK2, fontsize=10)
ax.annotate(f"{s.adj.iloc[-1]:.2f}", (last, s.adj.iloc[-1]), xytext=(9, -4), textcoords="offset points", color=INK2, fontsize=10)
ax.annotate(f"{s.raw.iloc[-1]:.2f}", (last, s.raw.iloc[-1]), xytext=(9, -4), textcoords="offset points", color=INK2, fontsize=10)
# direct labels (ink text; the line carries the color)
ax.annotate("Adjusted for experience, sex, race", (1996, s.adj[1996]), xytext=(0, -30), textcoords="offset points",
            ha="left", color=INK, fontsize=10.5)
ax.annotate("Raw gap between medians", (1994, s.raw[1994]), xytext=(0, 22), textcoords="offset points",
            ha="right", color=INK, fontsize=10.5)
ax.axvspan(1980, 1982.9, color=GRID, alpha=0.7, lw=0)
ax.text(1981.45, 0.985, "1980–82\nrecessions", transform=ax.get_xaxis_transform(), ha="center", va="top", color=INK2, fontsize=9)
ax.set_xlim(1978, last + 3.5); ax.set_xticks(range(1980, last + 1, 5))
lo = np.floor(min(s.adj.min(), s.raw.min()) * 10) / 10
ax.set_ylim(lo, np.ceil(max(s.adj.max(), s.raw.max()) * 10) / 10 + 0.02)
ax.yaxis.grid(True, color=GRID, lw=1); ax.set_axisbelow(True)
for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
ax.spines["bottom"].set_color(GRID); ax.tick_params(colors=INK2, length=0)
ax.set_ylabel("log points", color=INK2)
fig.suptitle("Median college wage premium, 1979–%d" % last, x=0.065, y=0.975, ha="left", fontsize=15, color=INK, fontweight="bold")
fig.text(0.065, 0.895, "Log hourly wage gap, bachelor’s degree or more vs. exactly high school. Wage and salary workers aged 18–64.",
         color=INK2, fontsize=10.5)
fig.text(0.065, 0.02, f"Source: CPS outgoing rotation groups (NBER extracts 1979–2024, Census basic monthly files 2025–{last}). "
         f"{last} is the first {months} available months.\nMedians, so top-coding does not enter. Imputed earnings excluded where flagged "
         "(flags incomplete 1989–95). Education coding changes in 1992.", color=INK2, fontsize=8.5, va="bottom")
fig.subplots_adjust(left=0.065, right=0.985, top=0.86, bottom=0.14)
fig.savefig("analysis/output/college_premium_longrun.png", facecolor=SURF)
