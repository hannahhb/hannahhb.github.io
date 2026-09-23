#!/usr/bin/env python3
"""Inline data/terrain.json into terrain.html's <script id="data"> block.

terrain.html ships as one self-contained file so it works from file:// and
needs no fetch, which means the JSON has to be re-embedded whenever the
pipeline rebuilds it. Doing that by hand is how the page and the data drift
apart.

    python3 inline_terrain.py   ->  rewrites ../terrain.html in place
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "..", "terrain.html")
DATA = os.path.join(HERE, "..", "data", "terrain.json")

OPEN = '<script type="application/json" id="data">'
CLOSE = "</script>"


def main():
    blob = open(DATA, encoding="utf-8").read().strip()
    json.loads(blob)                      # refuse to embed anything unparseable
    html = open(PAGE, encoding="utf-8").read()

    i = html.find(OPEN)
    if i < 0:
        sys.exit(f"no {OPEN} in terrain.html")
    j = html.find(CLOSE, i)
    if j < 0:
        sys.exit("unterminated data block")

    # "</script>" inside a string would close the block early; JSON escapes of
    # the slash are still valid JSON and the parser reads them back identically
    safe = blob.replace("</", "<\\/")
    out = html[:i + len(OPEN)] + safe + html[j:]
    open(PAGE, "w", encoding="utf-8").write(out)
    d = json.loads(blob)
    print(f"inlined {len(safe):,} bytes: {len(d['dep']):,} works, "
          f"{len(d['areas'])} areas, {len(d['quarters'])} quarters "
          f"({d['quarters'][0]}-{d['quarters'][-1]})")


if __name__ == "__main__":
    main()
