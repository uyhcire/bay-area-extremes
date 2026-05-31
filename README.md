# bay-area-extremes

Analysis of economic and demographic extremes in the Bay Area, built on public
data (Census ACS PUMS, FRED, BEA, BLS, and more). See **[CLAUDE.md](CLAUDE.md)**
for how to download every data source and for the public data mirror.

## Pitch deck

The recruiting deck lives in [`extremes-deck/`](extremes-deck/) (a self-contained
static HTML deck) and is deployed on Vercel:

- **Live:** https://bay-area-extremes.vercel.app
- Alias: https://bay-area-extremes-deck.vercel.app

> The deck is served with `noindex, nofollow` (see `extremes-deck/vercel.json`,
> the `<meta robots>` tag, and `robots.txt`), so it will **not** appear in search
> results — share the direct link above.

## Contributing a finding

The repo is a collective "journal": find a dimension where a Bay Area metro
ranks #1 or last among the 20 largest U.S. metros, confirm the number with
Claude Code against the public data, then **fork and open a pull request** to
add the entry.
