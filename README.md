# anoushkaghosh.com

Anoushka Ghosh's portfolio, designed in Framer and self-hosted on GitHub Pages at
[www.anoushkaghosh.com](https://www.anoushkaghosh.com).

The site is edited in Framer and published there on the free
`ghoshanoushka.framer.website` address. `build.py` copies that published site,
with all of its images, fonts and scripts, into `docs/`, which GitHub Pages serves.
The copy does not load anything from Framer.

## Updating the site

1. Edit the site in Framer and click **Publish**.
2. Rebuild and check the local copy:
   ```sh
   python3 build.py          # re-download the site into docs/
   python3 serve.py          # serve it at http://localhost:8000
   node check.mjs            # in another terminal: test every page with Framer blocked
   ```
3. Commit and push `docs/`. GitHub Pages redeploys within a minute or two.

`build.py` only uses the Python standard library. `check.mjs` needs Node 22+ and
Google Chrome. Downloads are cached in `.cache/` (not committed); delete it to
force a fresh download.

## How the copy works

- Pages are saved as `index.html` and `portfolio/<slug>.html`. GitHub Pages serves
  those at `/` and `/portfolio/<slug>`, the same URLs Framer uses.
- Images, fonts, scripts and icons are saved under `docs/assets/<original host>/`
  and every reference is rewritten to point there. Images are stored at most
  2048 px wide (`IMAGE_MAX` in `build.py`).
- Framer's CMS data files (`.framercms`) are binary and store byte offsets, so URLs
  inside them are rewritten with a same-length swap: `https://framerusercontent.com/`
  becomes `/assets/framerusercontent.com/`.
- Three changes to Framer's code make it work on a static host:
  - the CMS loader fetches whole files instead of asking Framer's server for byte
    ranges;
  - the icon components load the renamed icon files;
  - the Framer editor bar and Framer analytics are removed.
- `docs/CNAME` sets the custom domain, and `docs/.nojekyll` tells GitHub Pages to
  serve the files as they are.

If a Framer update changes its code, `build.py` may need adjusting. Run
`node check.mjs` after every rebuild to catch that.
