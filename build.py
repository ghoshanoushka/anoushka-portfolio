"""Mirror the published Framer site into ./docs with all assets served locally.

Pages are fetched from BASE, then every image, font, script, icon module and CMS
data file they reference (directly, or via scripts that import other scripts) is
downloaded into docs/assets/<host>/... and references are rewritten to point there.
Downloads are cached in .cache/ so re-running only fetches what changed.

framerusercontent.com URLs are rewritten by swapping the prefix
  https://framerusercontent.com/  ->  /assets/framerusercontent.com/
which is the same length (Framer's binary .framercms CMS files store byte offsets,
so their strings must not change length). Query strings such as ?scale-down-to=512
are left in place; static hosts ignore them, so every size variant of an image is
served by one local file, stored downscaled to at most IMAGE_MAX px.
"""
import hashlib, re, shutil, sys, urllib.error, urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

BASE = "https://ghoshanoushka.framer.website/"
ROOT = Path(__file__).parent
OUT = ROOT / "docs"
CACHE = ROOT / ".cache"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
IMAGE_MAX = 2048

FUC = "https://framerusercontent.com/"
FUC_LOCAL = "/assets/framerusercontent.com/"
assert len(FUC) == len(FUC_LOCAL)

# Hosts whose files get copied locally. framer.com only for /m/ (icon modules).
URL_RE = re.compile(
    r"https://(?:framerusercontent\.com|fonts\.gstatic\.com|i\.ytimg\.com|framer\.com/m/)"
    r"[^\s\"'`<>()\\,{}$]*"
)
URL_RE_BYTES = re.compile(rb"https://framerusercontent\.com/[^\s\"'`<>()\\,{}$\x00-\x1f]*")
# Relative module specifiers in JS import statements: from"./x.mjs", import(`../y.js`)
REL_RE = re.compile(r"""(\b(?:from|import)\s*\(?\s*)(["'`])(\.\.?/[^"'`\s]+?\.m?js)\2""")
# CMS chunk URLs built at runtime: new URL(`./x.framercms`,`https://.../X.js`).href.replace(`/modules/`,`/cms/`)
NEW_URL_RE = re.compile(r"new URL\(`(\./[^`]+)`,`(https://framerusercontent\.com/[^`]+)`\)(\.href\.replace\(`/modules/`,`/cms/`\))?")

# Icon components import `${base}${name}.js@0.0.57` at runtime; match the renamed files.
ICON_IMPORT_RE = re.compile(r"(\$\{\w+\})\.(m?js)@([\w.]+)`")
# The icon list each component ships, followed by its module base URL:
#   `Acorn.AddressBook...`.split(`.`),je=`https://framer.com/m/phosphor-icons/`
ICON_LIST_RE = re.compile(r"`([A-Za-z0-9.]+)`\.split\(`\.`\),(\w+)=`https://framer\.com/m/([\w-]+)/`")

# The CMS loader asks Framer's server for byte ranges via ?range=a-b,c-d and expects
# only those bytes back. Static hosts ignore the query and send the whole file, so
# replace the loader with one that fetches the whole file once and slices locally.
CMS_RANGE_RE = re.compile(
    r"async function (\w+)\((\w+),(\w+)\)\{(?:(?!async function).)*?searchParams\.set\(`range`"
    r"(?:(?!async function).)*?Unexpected response length(?:(?!async function).)*?"
    r"return \3\.map\(\w+=>\w+\.read\([^)]*\)\)\}"
)
CMS_RANGE_FIX = (
    r"async function \1(\2,\3){let f=await __cmsFile(\2);return \3.map(r=>f.slice(r.from,r.to))}"
    r"var __cmsFiles=new Map;function __cmsFile(u){u=String(u);let p=__cmsFiles.get(u);"
    r"if(!p){p=fetch(u).then(r=>{if(!r.ok)throw Error(`Request failed: ${r.status}`);return r.arrayBuffer()})"
    r".then(b=>new Uint8Array(b));p.catch(()=>__cmsFiles.delete(u));__cmsFiles.set(u,p)}return p}"
)

# Framer's "edit this page" bar is fetched from framer.com on every visit; stub it out.
EDITOR_IMPORT = "import(`https://framer.com/edit/init.mjs`)"
EDITOR_STUB = "Promise.resolve({createEditorBar:()=>()=>null})"
# Inline script that preloads the editor bar for logged-in Framer users.
EDITOR_PRELOAD_RE = re.compile(r'<script>try\{if\(localStorage\.getItem\("__framer_force_showing_editorbar_since"\)\).*?</script>')
# Framer analytics beacon (reports to the Framer dashboard; not useful off Framer).
ANALYTICS_RE = re.compile(r'<script[^>]*events\.framer\.com[^>]*>\s*</script>')

queue, done, failed = [], set(), []
icon_libs = []  # (library, version, [icon names]) found in downloaded scripts


def fetch(url):
    key = CACHE / hashlib.sha1(url.encode()).hexdigest()
    if key.exists():
        return key.read_bytes()
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    CACHE.mkdir(exist_ok=True)
    key.write_bytes(data)
    return data


def local_path(url):
    """Site-relative path for a remote file (query string dropped), e.g.
    https://framer.com/m/phosphor-icons/Code.js@0.0.57
      -> assets/framer.com/m/phosphor-icons/Code@0.0.57.js   (served as JavaScript)
    """
    u = urlparse(url)
    path = re.sub(r"\.(m?js)@([^/]+)$", r"@\2.\1", unquote(u.path))
    return f"assets/{u.netloc}{path}"


def enqueue(url):
    """Queue a file for download; skip bare hosts and URL prefixes ending in /."""
    if urlparse(url).path not in ("", "/") and not url.endswith("/"):
        queue.append(url)


def localize(text, base_url):
    """Rewrite remote asset URLs and relative imports to local paths."""
    def new_url_sub(m):
        rel, base, to_cms = m.groups()
        target = urljoin(base, rel)
        enqueue(target.replace("/modules/", "/cms/", 1) if to_cms else target)
        # new URL() needs an absolute base, so build it from the page origin
        return f"new URL(`{rel}`,location.origin+`/{local_path(base)}`){to_cms or ''}"

    def abs_sub(m):
        raw = m.group(0)
        if raw.startswith(FUC):  # same-length swap, query kept; see module docstring
            url = re.split(r"&(?:quot|lt|gt|#x?[0-9a-fA-F]+);|&amp;|\?", raw)[0]
            enqueue(url)
            return FUC_LOCAL + raw[len(FUC):]
        if urlparse(raw).path in ("", "/"):  # bare host, e.g. a preconnect hint
            return raw
        enqueue(raw)
        return "/" + local_path(raw)

    def rel_sub(m):
        url = urljoin(base_url, m.group(3))
        enqueue(url)
        return m.group(1) + m.group(2) + "/" + local_path(url) + m.group(2)

    for names, var, lib in ICON_LIST_RE.findall(text):
        m = re.search(r"\$\{" + var + r"\}\$\{\w+\}\.m?js@([\w.]+)`", text)
        if m:
            icon_libs.append((lib, m.group(1), names.split(".")))

    text = NEW_URL_RE.sub(new_url_sub, text)
    text = ICON_IMPORT_RE.sub(r"\1@\3.\2`", text)
    text = URL_RE.sub(abs_sub, text)
    text = REL_RE.sub(rel_sub, text)
    text = CMS_RANGE_RE.sub(CMS_RANGE_FIX, text)
    return text.replace(EDITOR_IMPORT, EDITOR_STUB)


def localize_cms(data):
    """Same-length prefix swap inside a binary .framercms file."""
    for m in URL_RE_BYTES.finditer(data):
        enqueue(m.group(0).decode("utf-8", "replace").split("?")[0])
    return data.replace(FUC.encode(), FUC_LOCAL.encode())


def process_asset(url):
    dest = OUT / local_path(url)
    src = url
    if "/images/" in url and not re.search(r"\.(svg|gif)$", url, re.I):
        src = f"{url}?scale-down-to={IMAGE_MAX}"
    try:
        data = fetch(src)
    except Exception as e:
        failed.append((url, str(e)))
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.suffix in {".mjs", ".js", ".css", ".json"}:
        dest.write_text(localize(data.decode("utf-8"), url))
    elif dest.suffix == ".framercms":
        dest.write_bytes(localize_cms(data))
    else:
        dest.write_bytes(data)


def clean_page(html, url):
    html = ANALYTICS_RE.sub("", html)
    html = EDITOR_PRELOAD_RE.sub("", html)
    return localize(html, url)


def save_404_page():
    """Framer's not-found page, which GitHub Pages serves for any unknown URL."""
    url = urljoin(BASE, "/__page-that-does-not-exist__")
    try:
        urllib.request.urlopen(urllib.request.Request(url, headers=UA))
        return  # no custom 404 page
    except urllib.error.HTTPError as e:
        if e.code != 404:
            failed.append((url, str(e)))
            return
        html = e.read().decode()
    # Served at arbitrary paths, so relative links like ./#projects must be root-based
    html = clean_page(html, url).replace('href="./', 'href="/')
    (OUT / "404.html").write_text(html)
    print("page  404")


def crawl_pages():
    seen, todo = set(), ["/"]
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        url = urljoin(BASE, path)
        try:
            html = urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read().decode()
        except Exception as e:
            failed.append((url, str(e)))
            continue
        for href in re.findall(r'href="(\.{1,2}/[^"#?]*|/[^"#?/][^"#?]*)', html):
            p = urlparse(urljoin(url, href)).path.rstrip("/") or "/"
            if p not in seen:
                todo.append(p)
        html = clean_page(html, url)
        dest = OUT / "index.html" if path == "/" else OUT / (path.lstrip("/") + ".html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html)
        print(f"page  {path}")


def drain_queue():
    while queue:
        url = queue.pop()
        if url not in done:
            done.add(url)
            process_asset(url)


def enqueue_used_icons():
    """Icons are picked at runtime from a name or search text set in Framer, which
    only appears as a string literal somewhere in the page code. Apply the icon
    component's own lookup (exact name, else first name containing the text) to
    every literal and download the result. This over-fetches, but icons are tiny."""
    literals = set()
    for f in OUT.rglob("*"):
        if f.suffix in {".html", ".mjs", ".js"} and "framer.com/m/" not in f.as_posix():
            # Lookarounds so a stray quote in text can't shift which spans count as strings
            literals.update(re.findall(r"(?<=[`\"'])([^`\"'\n]{1,40})(?=[`\"'])", f.read_text()))
    terms = {t for t in (s.lower().replace("-", "").replace(" ", "") for s in literals) if t}
    for lib, version, names in icon_libs:
        by_lower = {n.lower(): n for n in names}
        used = {by_lower.get(t) or next((n for n in names if t in n.lower()), None) for t in terms} - {None}
        print(f"icons {lib}: {len(used)} of {len(names)}")
        for name in sorted(used):
            enqueue(f"https://framer.com/m/{lib}/{name}.js@{version}")


def main():
    if OUT.exists():
        for p in OUT.iterdir():
            if p.name != "CNAME":
                shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(exist_ok=True)
    (OUT / ".nojekyll").touch()  # serve files as-is on GitHub Pages
    crawl_pages()
    save_404_page()
    drain_queue()
    enqueue_used_icons()
    drain_queue()
    print(f"assets {len(done) - len(failed)} downloaded, {len(failed)} failed")
    for url, err in failed:
        print(f"  FAIL {url}: {err}", file=sys.stderr)
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"site size {size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
