# vercel-test-site

A single-page static test site (`index.html`, no build step, no framework)
deployed to Vercel. This file documents how to reproduce the deployment.

## Prerequisites

- A Vercel access token exported as `VERCEL_ACCESS_TOKEN`.
  Create one at https://vercel.com/account/tokens.
- Node.js (used here just to make the HTTPS request; `curl` works too).

Verify the token and see which account it belongs to:

```bash
curl -s -H "Authorization: Bearer $VERCEL_ACCESS_TOKEN" \
  "https://api.vercel.com/v2/user"
```

## Deploy via the Vercel REST API

The `v13/deployments` endpoint accepts inline file contents, so no CLI or
git integration is required. Each file is sent as `{ "file": <path>, "data": <contents> }`.

```bash
node -e '
const fs = require("fs");
const https = require("https");

const html = fs.readFileSync("index.html", "utf8");
const payload = JSON.stringify({
  name: "bay-area-extremes-test",          // project name (created if absent)
  files: [{ file: "index.html", data: html }],
  projectSettings: { framework: null },     // plain static, no framework
  target: "production"
});

const req = https.request({
  hostname: "api.vercel.com",
  path: "/v13/deployments",
  method: "POST",
  headers: {
    "Authorization": "Bearer " + process.env.VERCEL_ACCESS_TOKEN,
    "Content-Type": "application/json",
    "Content-Length": Buffer.byteLength(payload)
  }
}, (res) => {
  let body = ""; res.on("data", d => body += d);
  res.on("end", () => console.log(body));
});
req.write(payload); req.end();
'
```

The response includes:

- `id` — deployment ID (e.g. `dpl_...`), used to poll status.
- `url` — the immutable per-deployment URL.
- `alias` — the stable production URLs.
- `inspectorUrl` — the Vercel dashboard link.

## Poll until the build is READY

```bash
curl -s -H "Authorization: Bearer $VERCEL_ACCESS_TOKEN" \
  "https://api.vercel.com/v13/deployments/<DEPLOYMENT_ID>" \
  | grep -o '"readyState":"[A-Z]*"'
```

Wait for `"readyState":"READY"` (it passes through `INITIALIZING` /
`BUILDING` first; `ERROR` means the build failed).

## Make it publicly viewable (disable SSO protection)

By default a Vercel account may have **Vercel Authentication** enabled, which
puts every `*.vercel.app` deployment behind an SSO login — the live URL then
returns **HTTP 401**. Check the project's protection settings:

```bash
curl -s -H "Authorization: Bearer $VERCEL_ACCESS_TOKEN" \
  "https://api.vercel.com/v9/projects/bay-area-extremes-test" \
  | grep -o '"ssoProtection":[^,]*'
```

If `ssoProtection` is set, disable it **for this project only** so the test
site is public:

```bash
curl -s -X PATCH \
  -H "Authorization: Bearer $VERCEL_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ssoProtection": null}' \
  "https://api.vercel.com/v9/projects/bay-area-extremes-test"
```

This only affects the named test project, not other deployments on the account.

## Verify it's live

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  "https://bay-area-extremes-test-<...>.vercel.app"   # expect HTTP 200
```

## Notes

- `VERCEL_ACCESS_TOKEN` is a secret — never commit it or paste it into files;
  always reference the environment variable.
- To tear the deployment down: delete the project from the Vercel dashboard,
  or `DELETE https://api.vercel.com/v9/projects/bay-area-extremes-test`.
