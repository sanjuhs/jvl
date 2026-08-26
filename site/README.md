# JVL website

The public site for JVL — landing, Learn (the tour + syntax + "convert your
doc"), Docs hub, and a Playground.

**Pure static** HTML/CSS/JS. No build step, no framework, no runtime
dependencies. The only external request is Google Fonts.

```
site/
  index.html        landing page
  learn.html        the language tour, syntax reference, conversion guide
  docs.html         documentation hub
  playground.html   worked examples + real compiler output
  styles.css        one stylesheet (dark-first, light via [data-theme])
  app.js            JVL syntax highlighter, terminal colorizer, tabs, nav
  assets/           logo mark + full lockup (SVG)
  vercel.json       clean URLs + cache/security headers
```

## Preview locally

```bash
cd site && python3 -m http.server 8799
# http://localhost:8799
```

## Deploy

See [`../DEPLOY.md`](../DEPLOY.md). The fastest path: import the repo on Vercel
with **Root Directory = `site`**.

## Editing content

- The **Learn** page is the canonical on-site teaching content; keep it in sync
  with `docs/02-language-tour.md`.
- Code samples use `<code class="jvl">` (syntax-highlighted) and
  `<code class="term">` (terminal-colorized) — the highlighter lives in `app.js`.
- If you add a language keyword, add it to the `KEYWORDS` regex in `app.js`.
