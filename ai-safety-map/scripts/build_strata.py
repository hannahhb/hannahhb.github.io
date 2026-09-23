#!/usr/bin/env python3
"""Precompute the stacked impact surfaces - one per year.

Each layer is a height field over the same ground plane the other maps use:
citation mass smoothed across the area positions. Stacked, they show how the
shape of the field moved year to year, and a pin dropped through every layer at
an area's position lets you trace that one place through time.

Smoothing happens here rather than in the browser: a 56x56 grid per year is a
few kilobytes, where shipping every work and kernel-smoothing at load time
would be megabytes and slow.

    python3 build_strata.py   ->  data/strata.json
"""
import json, math
from collections import defaultdict
from common import load, save

GRID = 56          # cells per side
EXTENT = 520       # world units from centre
SIGMA = 86         # kernel width, in world units


def main():
    imp = load("impact.json", {}) or {}
    areas, works = imp.get("areas", []), imp.get("works", [])
    QS = imp.get("quarters", [])
    if not areas:
        raise SystemExit("run build_impact.py first")

    pos = {a["name"]: (a["x"], a["y"]) for a in areas}
    years = sorted({int(QS[w["q"]][:4]) for w in works if w.get("q") is not None})
    print(f"{len(works)} works across years {years}")

    # a work sits at the weighted centre of its areas, with deterministic jitter
    def place(w, i):
        x = y = tw = 0.0
        for m in w.get("a", []):
            p = pos.get(m["a"])
            if p:
                x += p[0] * m["w"]; y += p[1] * m["w"]; tw += m["w"]
        if not tw:
            return None
        x, y = x / tw, y / tw
        h = (hash(w["t"]) ^ (i * 2654435761)) & 0xFFFFFF
        ang = (h % 360) * math.pi / 180
        rad = math.sqrt(((h >> 9) % 1000) / 1000) * 54
        return x + math.cos(ang) * rad, y + math.sin(ang) * rad

    step = (EXTENT * 2) / (GRID - 1)
    coords = [-EXTENT + i * step for i in range(GRID)]
    inv2s2 = 1.0 / (2 * SIGMA * SIGMA)
    reach = SIGMA * 2.6

    layers = []
    for yr in years:
        grid = [[0.0] * GRID for _ in range(GRID)]
        n = 0
        for i, w in enumerate(works):
            if w.get("q") is None or int(QS[w["q"]][:4]) != yr:
                continue
            p = place(w, i)
            if not p:
                continue
            val = math.log10(1 + (w.get("c") or 0)) ** 1.6      # tame the long tail
            if val <= 0:
                continue
            n += 1
            lo_x = max(0, int((p[0] - reach + EXTENT) / step))
            hi_x = min(GRID - 1, int((p[0] + reach + EXTENT) / step))
            lo_y = max(0, int((p[1] - reach + EXTENT) / step))
            hi_y = min(GRID - 1, int((p[1] + reach + EXTENT) / step))
            for gx in range(lo_x, hi_x + 1):
                dx = coords[gx] - p[0]
                for gy in range(lo_y, hi_y + 1):
                    dy = coords[gy] - p[1]
                    grid[gy][gx] += val * math.exp(-(dx * dx + dy * dy) * inv2s2)
        peak = max(max(r) for r in grid) or 1
        layers.append({"year": yr, "works": n, "peak": round(peak, 2),
                       "z": [[round(v, 3) for v in row] for row in grid]})
        print(f"  {yr}: {n:>5} works, peak {peak:.1f}")

    # pins: the areas worth tracing through the stack
    ranked = sorted(areas, key=lambda a: -a["mass"][-1])[:10]
    pins = [{"name": a["name"], "x": a["x"], "y": a["y"],
             "mass": [round(a["mass"][-1], 1)]} for a in ranked]

    gmax = max(l["peak"] for l in layers) or 1
    save("strata.json", {"grid": GRID, "extent": EXTENT, "sigma": SIGMA,
                         "layers": layers, "pins": pins, "peak": round(gmax, 2),
                         "areas": [{"name": a["name"], "x": a["x"], "y": a["y"],
                                    "mass": round(a["mass"][-1], 1)} for a in areas]})


if __name__ == "__main__":
    main()
