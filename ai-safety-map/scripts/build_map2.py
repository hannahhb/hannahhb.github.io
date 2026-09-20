#!/usr/bin/env python3
"""Assemble the overlap map: areas, their overlaps, and researchers under them.

The top level is areas and how they overlap - no researcher dots, because 1,900
of them drawn at once is what made the first map unreadable. Researchers are
aggregated from their works' area distributions and surface on drill-down.

    python3 build_map2.py   ->  data/map2.json
"""
import json
from collections import Counter, defaultdict
from common import load, save
from taxonomy import TAXONOMY

SUBPAT = None


def main():
    wa = load("work_areas.json", {}) or {}
    works, areas = wa.get("works", {}), wa.get("areas", [])
    ov = load("overlap.json", {}) or {}
    kw = (load("keyword_works.json", {}) or {}).get("people", {})
    people = {p["name"]: p for p in (load("people.json", {}) or {}).get("people", [])}

    # ---- researchers: aggregate their works' area distributions, citation-weighted ----
    res = []
    for name, ws in kw.items():
        dist, total, wlist = Counter(), 0.0, []
        for w in ws:
            key = w.get("arxiv_id", "").split("v")[0].lower() or w.get("url")
            rec = works.get(key)
            if not rec:
                continue
            weight = 1 + (w.get("citations") or 0) ** 0.5
            for a in rec["areas"]:
                dist[a["a"]] += a["w"] * weight
            total += weight
            wlist.append({"t": w.get("title"), "u": w.get("url"), "c": w.get("citations"),
                          "y": w.get("year"), "k": w.get("kind")})
        if not dist:
            continue
        s = sum(dist.values())
        top = dist.most_common(4)
        p = people.get(name, {})
        res.append({
            "n": name, "sec": p.get("sector", "unknown"), "org": p.get("institution") or "",
            "osrc": p.get("institution_source") or "",
            "wk": p.get("works_total", len(ws)), "cit": p.get("citations", 0),
            "h": p.get("h_index"), "sen": p.get("seniority"),
            "a": [{"a": k, "w": round(v / s, 3)} for k, v in top if v / s >= 0.08],
            "top": sorted(wlist, key=lambda x: -(x["c"] or 0))[:4],
        })

    # ---- area nodes: volume, headcount, sub-area breakdown ----
    vol = dict(zip(areas, ov.get("volume", [])))
    anodes = []
    for a in areas:
        here = [r for r in res if r["a"] and r["a"][0]["a"] == a]
        touch = [r for r in res if any(x["a"] == a for x in r["a"])]
        subs = list(TAXONOMY.get(a, {}).get("subs", {}))
        anodes.append({
            "name": a, "blurb": TAXONOMY.get(a, {}).get("blurb", ""),
            "vol": round(vol.get(a, 0), 1),
            "primary": len(here), "touching": len(touch),
            "subs": subs,
            "top_people": [r["n"] for r in sorted(here, key=lambda r: -(r["cit"] or 0))[:10]],
        })

    # ---- edges: only overlaps worth drawing ----
    J = ov.get("jaccard", [])
    edges = []
    for i in range(len(areas)):
        for j in range(i + 1, len(areas)):
            v = J[i][j] if J else 0
            if v >= 0.06:
                edges.append({"s": i, "t": j, "w": round(v, 4)})
    edges.sort(key=lambda e: -e["w"])

    print(f"{len(anodes)} areas, {len(edges)} overlap edges, {len(res)} researchers")
    print(f"researchers with 2+ areas: {sum(1 for r in res if len(r['a'])>1)}")
    save("map2.json", {"areas": anodes, "edges": edges, "people": res,
                       "matrix": {"areas": areas, "jaccard": J,
                                  "volume": ov.get("volume", [])}})


if __name__ == "__main__":
    main()
