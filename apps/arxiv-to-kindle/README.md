# arxiv-to-kindle

Send arXiv papers to the jailbroken Kindle as reflowable **EPUB** (or the original PDF),
over Wi‑Fi SSH. Platform: [kindle](../../platforms/kindle/) (needs `ssh kindle` working).

```bash
brew install pandoc                                   # once

apps/arxiv-to-kindle/arxiv2kindle.py 2601.03220       # id, abs/pdf URL, or old-style hep-th/9711200
apps/arxiv-to-kindle/arxiv2kindle.py 2601.03220 2405.12345 ...
apps/arxiv-to-kindle/arxiv2kindle.py --pdf 2601.03220           # original PDF
apps/arxiv-to-kindle/arxiv2kindle.py --out ~/Desktop 2601.03220 # save locally, no upload
```

Papers land in `/mnt/us/documents/Papers/` as `Title - Author et al (YEAR, ID).epub` and
show up in KOReader's file browser. Open them with KOReader (not the stock reader).

## How the EPUB is made

1. arXiv API → title, authors, year, latest version.
2. Fetch arXiv's HTML rendering (`arxiv.org/html/<id>`, LaTeXML) and keep only the
   `<article>` — drops the site header, issue‑report forms, footer.
3. Make figure URLs absolute so pandoc embeds them; rewrite author macros pandoc's TeX
   parser doesn't know (`\argmax`, `\quantity`, `\mathbbm`, …) in the math annotations.
4. `pandoc -t epub3 --mathml --toc --split-level=2` with a Lua filter that unwraps
   LaTeXML's section `<div>`s (so it can split one chapter per section — keeps each
   XHTML file small for the K4's 256 MB RAM) and an e‑ink stylesheet.
5. Upload via `ssh kindle`: stream into `/mnt/us/.gadgets-upload/` (outside `documents/`,
   so the Kindle's indexer can't grab a half‑written file — that caused
   "Stale NFS file handle"), then `mv` into place and check the size.

Papers with no HTML version (older or non‑LaTeX submissions) fall back to the PDF.
A few formulas with unusual macros may be left as raw TeX; the tool reports how many.
