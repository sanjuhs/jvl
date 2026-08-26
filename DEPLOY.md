# Deploying the JVL website

The site lives in [`site/`](site/) and is **pure static HTML/CSS/JS** — no build
step, no framework, no dependencies. That makes hosting it trivial.

## Option A — Vercel Git integration (recommended, ~2 minutes)

This gives you automatic deploys on every push with zero secrets to manage.

1. Go to <https://vercel.com/new> and **Import** the `sanjuhs/jvl` repository.
2. In the import screen, set **Root Directory** to `site`.
3. Framework preset: **Other**. Build command: leave **empty**. Output
   directory: leave as `.` (Vercel serves the static files directly).
4. Click **Deploy**.

Vercel now redeploys automatically whenever `main` changes. You'll get a URL like
`https://jvl.vercel.app` (and can add a custom domain in the project settings).

## Option B — GitHub Action

The workflow at [`.github/workflows/deploy-site.yml`](.github/workflows/deploy-site.yml)
deploys `site/` to Vercel on push. It **skips cleanly** unless you add three
repository secrets (Settings → Secrets and variables → Actions):

- `VERCEL_TOKEN` — from <https://vercel.com/account/tokens>
- `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` — from the project's
  `.vercel/project.json` after running `vercel link` locally, or from the
  project settings.

## Option C — any static host

Because it's plain static files, you can also drop `site/` on GitHub Pages,
Netlify, Cloudflare Pages, or an S3 bucket. Point the host at the `site/`
directory and you're done.

## Enabling the AI helper (optional)

The editor's "Draft JVL from plain English" button calls a Vercel serverless
function at [`site/api/assist.js`](site/api/assist.js). To turn it on, add an
environment variable in the Vercel project (Settings → Environment Variables):

- `ANTHROPIC_API_KEY` — your Anthropic API key. **Server-side only**; it is never
  sent to the browser.
- `JVL_ASSIST_MODEL` *(optional)* — the model to use. Defaults to
  `claude-sonnet-5` (fast). Set to `claude-opus-5` for maximum quality.

Without the key, the button still works as a fallback: it copies a ready-made
prompt to the clipboard to paste into any LLM. Redeploy after adding the
variable so the function picks it up.

## Local preview

```bash
cd site && python3 -m http.server 8799
# open http://localhost:8799
```

## What's deployed

`site/vercel.json` enables clean URLs (`/learn` instead of `/learn.html`), long
cache headers for `assets/`, and a couple of sensible security headers. Nothing
in the site calls out to a backend; the only external requests are Google Fonts.
