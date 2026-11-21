#!/usr/bin/env python3
"""Send arXiv papers to the jailbroken Kindle over SSH — as EPUB (default) or PDF.

    apps/arxiv-to-kindle/arxiv2kindle.py 2601.03220
    apps/arxiv-to-kindle/arxiv2kindle.py https://arxiv.org/abs/2601.03220 hep-th/9711200 ...
    apps/arxiv-to-kindle/arxiv2kindle.py --pdf 2601.03220        # original PDF instead
    apps/arxiv-to-kindle/arxiv2kindle.py --out ~/Desktop 2601.03220   # save locally, no upload

EPUB is built from arXiv's HTML rendering (LaTeXML, math as MathML) with pandoc:
only the <article> is kept (no site chrome), figures are embedded, the book is split
per section with a table of contents. Papers without an HTML version fall back to PDF.
Files land in /mnt/us/documents/Papers/ as "Title - Author et al (YEAR, ID).epub".

Needs: `ssh kindle` working (platforms/kindle/README.md) and pandoc (brew install pandoc).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

API = "https://export.arxiv.org/api/query?id_list={}"
HTML = "https://arxiv.org/html/{}"
UA = {"User-Agent": "arxiv-to-kindle/0.1 (personal e-reader sync)"}
ATOM = {"a": "http://www.w3.org/2005/Atom"}
DEST = "/mnt/us/documents/Papers"
STAGE = "/mnt/us/.gadgets-upload"  # outside documents/ so the indexer leaves partial files alone

ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)")

# Author macros pandoc's TeX parser doesn't know (seen in LaTeXML alttext).
MACROS = {
    r"\argmax": r"\operatorname*{argmax}",
    r"\argmin": r"\operatorname*{argmin}",
    r"\E": r"\mathbb{E}",
    r"\Var": r"\operatorname{Var}",
    r"\Cov": r"\operatorname{Cov}",
    r"\KL": r"\operatorname{KL}",
    r"\R": r"\mathbb{R}",
    r"\N": r"\mathbb{N}",
    r"\D": r"\mathcal{D}",
    r"\quantity": "",          # physics pkg auto-sized brackets: keep the contents
    r"\mathbbm": r"\mathbb",
    r"\Bigl": r"\Big",
    r"\Bigr": r"\Big",
}

# LaTeXML wraps each section in <section>/<div>; pandoc then can't see the headings
# to split chapters on. Unwrap plain Divs so headings become top-level blocks.
UNWRAP_LUA = "function Div(el) return el.content end"

# E-ink friendly extras on top of pandoc's default stylesheet.
CSS = """
img, svg { max-width: 100%; height: auto; }
figure { margin: 1em 0; text-align: center; }
figcaption { font-size: 0.85em; }
table { font-size: 0.8em; border-collapse: collapse; }
td, th { padding: 0.1em 0.3em; }
math[display="block"] { display: block; margin: 0.5em 0; }
"""


def parse_id(arg: str) -> str:
    m = ID_RE.search(arg)
    if not m:
        sys.exit(f"not an arXiv id or URL: {arg}")
    return m.group(1)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def metadata(arxiv_id: str) -> dict:
    entry = ET.fromstring(fetch(API.format(arxiv_id))).find("a:entry", ATOM)
    if entry is None or entry.find("a:title", ATOM) is None:
        sys.exit(f"arXiv has no paper {arxiv_id}")
    title = " ".join(entry.find("a:title", ATOM).text.split())
    authors = [a.find("a:name", ATOM).text for a in entry.findall("a:author", ATOM)]
    year = entry.find("a:published", ATOM).text[:4]
    versioned = entry.find("a:id", ATOM).text.rsplit("/abs/", 1)[-1]  # e.g. 2601.03220v2
    pdf = next((l.get("href") for l in entry.findall("a:link", ATOM) if l.get("title") == "pdf"),
               f"https://arxiv.org/pdf/{versioned}")
    return {"id": re.sub(r"v\d+$", "", arxiv_id),
            "versioned": versioned, "title": title, "authors": authors, "year": year, "pdf": pdf}


def filename(meta: dict, ext: str) -> str:
    def clean(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|]', " ", s)).strip()

    surname = meta["authors"][0].split()[-1] if meta["authors"] else "Unknown"
    who = surname + (" et al" if len(meta["authors"]) > 1 else "")
    tail = f" - {who} ({meta['year']}, {meta['id'].replace('/', '_')}).{ext}"
    title = clean(meta["title"])[: 150 - len(tail)].rstrip(" .-")
    return clean(title + tail)


def article_html(meta: dict) -> str | None:
    """arXiv's HTML rendering reduced to the <article>, with absolute image URLs."""
    url = HTML.format(meta["versioned"])
    try:
        page = fetch(url).decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    start, end = page.find("<article"), page.rfind("</article>")
    if start < 0 or end < 0:
        return None
    art = page[start:end + len("</article>")]
    art = re.sub(r'(<img[^>]*\ssrc=")([^"]+)"',
                 lambda m: f'{m.group(1)}{urllib.parse.urljoin(url, m.group(2))}"', art)
    for k, v in MACROS.items():  # only inside TeX annotations / alttext; word-boundary safe
        art = re.sub(re.escape(k) + r"(?![A-Za-z])", lambda _: v, art)
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>{meta["title"]}</title></head><body>{art}</body></html>'


def build_epub(meta: dict, html: str, out: str) -> int:
    """Run pandoc; returns the number of formulas it had to leave as raw TeX."""
    with tempfile.TemporaryDirectory() as td:
        src, css, lua = (os.path.join(td, f) for f in ("paper.html", "eink.css", "unwrap.lua"))
        open(src, "w").write(html)
        open(css, "w").write(CSS)
        open(lua, "w").write(UNWRAP_LUA)
        cmd = ["pandoc", "-f", "html", "-t", "epub3", "--mathml", "--toc", "--split-level=2",
               "--lua-filter", lua, "--css", css, "--request-header", f"User-Agent: {UA['User-Agent']}",
               "--metadata", f"title={meta['title']}", "--metadata", f"date={meta['year']}",
               "--metadata", "lang=en", "-o", out, src]
        for a in meta["authors"]:
            cmd += ["--metadata", f"author={a}"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"pandoc failed:\n{r.stderr[-2000:]}")
        return r.stderr.count("Could not convert TeX math")


def upload(path: str, name: str, host: str) -> None:
    size = os.path.getsize(path)
    stage = f"{STAGE}/upload.part"
    cmd = (f'mkdir -p "{STAGE}" "{DEST}" && cat > "{stage}" && '
           f'mv -f "{stage}" "{DEST}/{name}" && wc -c < "{DEST}/{name}"')
    with open(path, "rb") as fh:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, cmd],
                           stdin=fh, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"upload failed: {r.stderr.decode().strip()}\n(Is the Kindle awake with SSH running?)")
    if int(r.stdout.split()[-1]) != size:
        sys.exit("upload size mismatch")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("papers", nargs="+", help="arXiv ids or URLs")
    ap.add_argument("--pdf", action="store_true", help="send the original PDF instead of an EPUB")
    ap.add_argument("--out", help="save into this local folder instead of uploading")
    ap.add_argument("--host", default="kindle", help="ssh host alias (default: kindle)")
    args = ap.parse_args()

    for p in args.papers:
        meta = metadata(parse_id(p))
        with tempfile.TemporaryDirectory() as td:
            html = None if args.pdf else article_html(meta)
            note = ""
            if html:
                name = filename(meta, "epub")
                path = os.path.join(td, name)
                raw = build_epub(meta, html, path)
                note = f", {raw} formula(s) left as TeX" if raw else ""
            else:
                if not args.pdf:
                    print(f"  {meta['id']}: no arXiv HTML version — sending PDF")
                pdf = fetch(meta["pdf"])
                if not pdf.startswith(b"%PDF"):
                    sys.exit(f"{meta['id']}: download is not a PDF")
                name = filename(meta, "pdf")
                path = os.path.join(td, name)
                open(path, "wb").write(pdf)
            size = os.path.getsize(path) / 1e6
            if args.out:
                dest = os.path.join(os.path.expanduser(args.out), name)
                shutil.copyfile(path, dest)
                print(f"✓ {name}  ({size:.1f} MB{note}) → {dest}")
            else:
                upload(path, name, args.host)
                print(f"✓ {name}  ({size:.1f} MB{note}) → kindle:{DEST}/")


if __name__ == "__main__":
    main()
