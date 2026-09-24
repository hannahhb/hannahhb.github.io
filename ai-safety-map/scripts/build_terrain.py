#!/usr/bin/env python3
"""Emit deposits, not grids, so the terrain can be resolved at any zoom.

The earlier wave shipped pre-smoothed height grids - one per quarter, per
measure - which fixed the level of detail at build time and cost megabytes.
This ships the raw deposits instead: one point per work, with its position,
weight and quarter. The page sums the kernel itself at whatever extent it is
showing, so zooming in genuinely resolves finer structure rather than
magnifying a blurry bitmap, and the payload is a fraction of the size.

    python3 build_terrain.py   ->  data/terrain.json
"""
import math
from collections import Counter
from common import load, save
from methodness import method_only


def main():
    imp = load("impact.json", {}) or {}
    m2 = load("map2.json", {}) or {}
    areas, works, QS = imp.get("areas", []), imp.get("works", []), imp.get("quarters", [])
    if not areas:
        raise SystemExit("run build_impact.py first")

    aidx = {a["name"]: i for i, a in enumerate(areas)}
    # Positions now come from the works themselves - see build_layout.py. Areas
    # are labelled wherever their works ended up, rather than deciding where
    # their works go.
    lay = load("layout.json", {}) or {}
    POS = lay.get("pos", {})
    ACENT = {a["name"]: a for a in lay.get("areas", [])}
    if not POS:
        raise SystemExit("run build_layout.py first")

    vol = Counter()
    for w in works:
        for m in w.get("a", []):
            vol[m["a"]] += 1

    # match works to their layout position by title, since impact.json keys on
    # the work record and the layout keys on the arXiv id
    wa = (load("work_areas.json", {}) or {}).get("works", {})
    ab = load("abstracts.json", {}) or {}
    by_title, mo_by_title = {}, {}
    for k, r in wa.items():
        if k in POS and r.get("title"):
            by_title[r["title"][:90]] = POS[k]
            mo_by_title[r["title"][:90]] = method_only(
                r["title"], (ab.get(k) or {}).get("abstract", ""))

    dep, meta, missed = [], [], 0
    for i, w in enumerate(works):
        if w.get("q") is None or not w.get("a"):
            continue
        top = w["a"][0]["a"]
        if top not in aidx:
            continue
        p = by_title.get((w.get("t") or "")[:90])
        if not p:
            missed += 1
            continue
        x, y = p
        c = w.get("c") or 0
        weight = math.log10(1 + c) ** 1.6
        if weight <= 0:
            continue
        dep.append([round(x, 1), round(y, 1), round(weight, 3), w["q"], aidx[top]])
        rec = {"t": w["t"][:120], "u": w.get("u"), "c": c, "k": w.get("k"),
               "au": (w.get("au") or [])[:3]}
        if mo_by_title.get((w.get("t") or "")[:90]):
            rec["mo"] = 1                 # preference-tuning machinery, no named harm
        meta.append(rec)

    xs = [d[0] for d in dep]; ys = [d[1] for d in dep]
    nmo = sum(1 for m in meta if m.get("mo"))
    cmo = sum(m["c"] for m in meta if m.get("mo"))
    ctot = sum(m["c"] for m in meta) or 1
    print(f"{len(dep)} deposits, x {min(xs):.0f}..{max(xs):.0f}, y {min(ys):.0f}..{max(ys):.0f}"
          f"  ({missed} works had no layout position)")
    print(f"  method-only: {nmo} works ({100*nmo/len(meta):.1f}%) "
          f"carrying {cmo:,} citations ({100*cmo/ctot:.1f}% of the total)")

    out = {
        "quarters": QS, "trail": 4,
        "areas": [{"name": a["name"], "blurb": a.get("blurb", ""),
                   "x": (ACENT.get(a["name"]) or {}).get("x", 0),
                   "y": (ACENT.get(a["name"]) or {}).get("y", 0),
                   "mass": [round(m, 1) for m in a["mass"]],
                   "works": vol.get(a["name"], 0),
                   "scatter": (ACENT.get(a["name"]) or {}).get("scatter", 120),
                   "spread": (ACENT.get(a["name"]) or {}).get("scatter", 120)}
                  for a in areas],
        "edges": m2.get("edges", []),
        "dep": dep, "meta": meta,
    }
    save("terrain.json", out)


if __name__ == "__main__":
    main()
