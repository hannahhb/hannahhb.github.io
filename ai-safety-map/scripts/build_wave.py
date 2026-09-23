#!/usr/bin/env python3
"""Per-quarter height fields for the animated impact surface.

One grid per quarter, so the page can interpolate between them and the surface
morphs rather than jumping. Two measures, because they answer different
questions:

  cumulative  - citation mass of everything published up to that quarter. The
                landscape builds; ridges only grow. "Where impact has settled."
  trailing    - citation mass of work published in the preceding four quarters.
                Ridges rise and fall. "Where the field is active now."

The ground plane is the same one the overlap map uses, so a ridge sits where
that area sits, and areas that overlap in abstract-space sit near each other -
which is what makes neighbouring ridges merge.

    python3 build_wave.py   ->  data/wave.json
"""
import json, math
from common import load, save

GRID = 62
EXTENT = 520
SIGMA = 38   # tight enough that areas read as separate hills, merging only at their feet
TRAIL = 4          # quarters in the trailing window


def main():
    imp = load("impact.json", {}) or {}
    areas, works, QS = imp.get("areas", []), imp.get("works", []), imp.get("quarters", [])
    if not areas:
        raise SystemExit("run build_impact.py first")
    # Spread the areas further across the plane than the overlap map needs them.
    # Packed tightly, every kernel lands on top of every other and the field
    # collapses to one central mass; spread out, each area raises its own ridge
    # and neighbours merge only where they genuinely overlap.
    SPREAD = 1.34
    pos = {a["name"]: (a["x"] * SPREAD, a["y"] * SPREAD) for a in areas}

    step = (EXTENT * 2) / (GRID - 1)
    coords = [-EXTENT + i * step for i in range(GRID)]
    inv2s2 = 1.0 / (2 * SIGMA * SIGMA)
    reach = SIGMA * 2.8

    # An area's footprint grows with how much work it holds, so a large field
    # covers more ground rather than piling higher on the same spot - the same
    # idea as the atlas hulls, where a bigger cluster is a bigger shape.
    vol = {}
    for a in areas:
        n = 0
        for w in works:
            if any(m["a"] == a["name"] for m in w.get("a", [])):
                n += 1
        vol[a["name"]] = n
    med = sorted(vol.values())[len(vol) // 2] or 1
    sigma_of = {k: max(24.0, min(62.0, SIGMA * (v / med) ** 0.26)) for k, v in vol.items()}
    print("area footprints (works -> kernel):")
    for k in sorted(vol, key=lambda k: -vol[k])[:6]:
        print(f"  {vol[k]:>5} works  sigma {sigma_of[k]:5.1f}  {k}")

    aidx = {a["name"]: i for i, a in enumerate(areas)}

    # one deposit per work: where it sits, how much it carries, and whose it is
    deposits = []
    for i, w in enumerate(works):
        if w.get("q") is None:
            continue
        x = y = tw = 0.0
        for m in w.get("a", []):
            p = pos.get(m["a"])
            if p:
                x += p[0] * m["w"]; y += p[1] * m["w"]; tw += m["w"]
        if not tw:
            continue
        x, y = x / tw, y / tw
        h = (hash(w["t"]) ^ (i * 2654435761)) & 0xFFFFFF
        ang = (h % 360) * math.pi / 180
        rad = math.sqrt(((h >> 9) % 1000) / 1000) * 46
        val = math.log10(1 + (w.get("c") or 0)) ** 1.6
        if val <= 0:
            continue
        top = w["a"][0]["a"] if w.get("a") else None
        if top not in aidx:
            continue
        sg = sigma_of[top]
        deposits.append((w["q"], x + math.cos(ang) * rad * (sg / SIGMA),
                         y + math.sin(ang) * rad * (sg / SIGMA), val, aidx[top], sg))
    print(f"{len(deposits)} weighted deposits across {len(QS)} quarters")

    def field(keep):
        """Total height, plus which area owns each cell and how strongly."""
        grid = [[0.0] * GRID for _ in range(GRID)]
        per = [[[0.0] * GRID for _ in range(GRID)] for _ in areas]
        for q, x, y, val, ai, sg in deposits:
            if not keep(q):
                continue
            inv = 1.0 / (2 * sg * sg)
            rch = sg * 2.8
            lo_x = max(0, int((x - rch + EXTENT) / step))
            hi_x = min(GRID - 1, int((x + rch + EXTENT) / step))
            lo_y = max(0, int((y - rch + EXTENT) / step))
            hi_y = min(GRID - 1, int((y + rch + EXTENT) / step))
            for gx in range(lo_x, hi_x + 1):
                dx = coords[gx] - x
                for gy in range(lo_y, hi_y + 1):
                    dy = coords[gy] - y
                    k = val * math.exp(-(dx * dx + dy * dy) * inv)
                    grid[gy][gx] += k
                    per[ai][gy][gx] += k
        own = [[0] * GRID for _ in range(GRID)]
        pur = [[0.0] * GRID for _ in range(GRID)]
        for gy in range(GRID):
            for gx in range(GRID):
                best = bi = 0
                tot = grid[gy][gx]
                for ai in range(len(areas)):
                    v = per[ai][gy][gx]
                    if v > best:
                        best, bi = v, ai
                own[gy][gx] = bi
                pur[gy][gx] = round(best / tot, 2) if tot > 1e-9 else 0
        return grid, own, pur

    out = {"cumulative": [], "trailing": []}
    owners = {"cumulative": [], "trailing": []}
    purity = {"cumulative": [], "trailing": []}
    for qi in range(len(QS)):
        c, co, cp = field(lambda q, qi=qi: q <= qi)
        t, to, tp = field(lambda q, qi=qi: qi - TRAIL < q <= qi)
        out["cumulative"].append([[round(v, 1) for v in row] for row in c])
        out["trailing"].append([[round(v, 1) for v in row] for row in t])
        owners["cumulative"].append(co); owners["trailing"].append(to)
        purity["cumulative"].append(cp); purity["trailing"].append(tp)
        print(f"  {QS[qi]}  cumulative peak {max(max(r) for r in c):8.1f}   "
              f"trailing peak {max(max(r) for r in t):8.1f}", flush=True)

    # every work, at the spot its deposit landed, so the view can show them
    # individually once you zoom past the point where the surface is the story
    wlist = []
    for i, w in enumerate(works):
        if w.get("q") is None or not w.get("a"):
            continue
        top = w["a"][0]["a"]
        if top not in aidx:
            continue
        x = y = tw = 0.0
        for m in w["a"]:
            pp = pos.get(m["a"])
            if pp:
                x += pp[0] * m["w"]; y += pp[1] * m["w"]; tw += m["w"]
        if not tw:
            continue
        x, y = x / tw, y / tw
        h = (hash(w["t"]) ^ (i * 2654435761)) & 0xFFFFFF
        ang = (h % 360) * math.pi / 180
        rad = math.sqrt(((h >> 9) % 1000) / 1000) * 46 * (sigma_of[top] / SIGMA)
        wlist.append({
            "x": round(x + math.cos(ang) * rad, 1), "y": round(y + math.sin(ang) * rad, 1),
            "c": w.get("c"), "q": w["q"], "a": aidx[top],
            "t": w["t"][:110], "u": w.get("u"), "k": w.get("k"),
            "au": (w.get("au") or [])[:3],
        })
    wlist.sort(key=lambda z: -(z["c"] or 0))
    print(f"\n{len(wlist)} individual works carried for zoom")

    peaks = {k: max(max(max(r) for r in g) for g in v) for k, v in out.items()}
    counts = [sum(1 for d in deposits if d[0] <= qi) for qi in range(len(QS))]
    save("wave.json", {
        "grid": GRID, "extent": EXTENT, "quarters": QS, "trail": TRAIL,
        "peak": {k: round(v, 1) for k, v in peaks.items()},
        "counts": counts,
        "areas": [{"name": a["name"], "x": a["x"], "y": a["y"],
                   "mass": [round(m, 1) for m in a["mass"]]} for a in areas],
        "fields": out, "owner": owners, "purity": purity, "works": wlist,
    })


if __name__ == "__main__":
    main()
