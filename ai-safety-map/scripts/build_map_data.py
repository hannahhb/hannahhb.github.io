#!/usr/bin/env python3
"""Compact the dataset into what the map page needs.

people.json is 7 MB and mostly detail the map never draws. This emits only the
fields the page uses, plus each person's weighted membership across sub-areas -
which is what positions them: someone whose work spans two sub-areas is pulled
toward both and settles in the overlap.

    python3 build_map_data.py   ->  data/map.json
"""
import json, re
from collections import Counter, defaultdict
from common import load, save
from taxonomy import TAXONOMY, flat

RULES = [(area, sub, re.compile(pat, re.I)) for area, sub, pat in flat()]
MAX_MEMBERSHIPS = 4


def memberships(works):
    """sub-area -> share of this person's citation-weighted work."""
    w = Counter()
    for work in works:
        text = (work.get("title") or "") + " " + " ".join(work.get("keywords") or [])
        weight = 1 + (work.get("citations") or 0) ** 0.5
        for area, sub, rx in RULES:
            if rx.search(text):
                w[f"{area} / {sub}"] += weight
    if not w:
        return []
    total = sum(w.values())
    top = w.most_common(MAX_MEMBERSHIPS)
    return [{"sub": k, "w": round(v / total, 3)} for k, v in top]


def main():
    people = (load("people.json", {}) or {}).get("people", [])
    works = (load("keyword_works.json", {}) or {}).get("people", {})
    tax = (load("taxonomy.json", {}) or {}).get("areas", {})

    nodes, skipped = [], 0
    for p in people:
        ws = works.get(p["name"]) or []
        mem = memberships(ws)
        if not mem:
            skipped += 1
            continue
        top3 = sorted(ws, key=lambda w: -(w.get("citations") or 0))[:3]
        nodes.append({
            "n": p["name"],
            "sec": p["sector"],
            "org": p.get("institution") or "",
            "osrc": p.get("institution_source") or "",
            "side": p.get("side"),
            "wk": p.get("works_total", 0),
            "pap": p.get("papers", 0),
            "pos": p.get("posts", 0),
            "cit": p.get("citations", 0),
            "h": p.get("h_index"),
            "sen": p.get("seniority"),
            "ten": p.get("safety_tenure"),
            "conf": p.get("confidence"),
            "lw": p.get("lw_slug"),
            "s2": p.get("s2_author_id"),
            "m": mem,
            "top": [{"t": w.get("title"), "u": w.get("url"), "c": w.get("citations"),
                     "y": w.get("year"), "k": w.get("kind")} for w in top3],
        })

    # area / sub scaffolding, ordered so related areas sit near each other
    areas = []
    for area, spec in TAXONOMY.items():
        subs = []
        for sub in spec["subs"]:
            key = f"{area} / {sub}"
            n = sum(1 for x in nodes if x["m"] and x["m"][0]["sub"] == key)
            any_n = sum(1 for x in nodes if any(m["sub"] == key for m in x["m"]))
            subs.append({"name": sub, "key": key, "primary": n, "any": any_n})
        areas.append({"name": area, "blurb": spec["blurb"], "subs": subs,
                      "primary": sum(s["primary"] for s in subs)})

    orgs = Counter(x["org"] for x in nodes if x["org"])
    sectors = Counter(x["sec"] for x in nodes)
    print(f"{len(nodes)} people placed, {skipped} with no taxonomy match")
    print(f"multi-area: {sum(1 for x in nodes if len(x['m']) > 1)}")
    print(f"orgs: {len(orgs)} distinct, top 50 cover "
          f"{sum(v for _, v in orgs.most_common(50))} people")
    print("sectors:", dict(sectors))

    save("map.json", {"areas": areas, "people": nodes,
                      "orgs": orgs.most_common(60),
                      "generated": (load("people.json", {}) or {}).get("generated")})


if __name__ == "__main__":
    main()
