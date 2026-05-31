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

### Updating the website

The Vercel project (`bay-area-extremes-deck`) is **not** connected to GitHub, so
pushing or merging does **not** redeploy it. You deploy by uploading the files in
`extremes-deck/` directly. Edit `extremes-deck/index.html`, then redeploy.

Easiest, with the [Vercel CLI](https://vercel.com/docs/cli) (`npm i -g vercel`):

```bash
cd extremes-deck
vercel deploy --prod      # uploads this folder and promotes it to production
```

No CLI? Deploy via the REST API with a token in `VERCEL_ACCESS_TOKEN`
(team `eric-yus-projects-7f811cc3`, project id
`prj_685UPGr3pAiIKbGIMu7wGs79KAqJ`):

1. SHA-1 + upload each file (`index.html`, `robots.txt`, `vercel.json`) to
   `POST https://api.vercel.com/v2/files` with an `x-vercel-digest: <sha1>` header.
2. `POST https://api.vercel.com/v13/deployments?teamId=<team>` with
   `{"name":"bay-area-extremes-deck","project":"<projectId>","target":"production",
   "files":[{"file","sha","size"}…]}`.

Vercel automatically points the `bay-area-extremes.vercel.app` /
`bay-area-extremes-deck.vercel.app` aliases at the new production deployment once
it reaches `READY`.

## Contributing a finding

The repo is a collective "journal": find a dimension where a Bay Area metro
ranks #1 or last among the 20 largest U.S. metros, confirm the number with
Claude Code against the public data, then **fork and open a pull request** to
add the entry.
