#!/usr/bin/env python3
"""Place works and people into the taxonomy.

Assignment is multi-label: a paper on steering an evaluation-aware model
genuinely belongs to both steering and evaluation awareness, and forcing one
label would misrepresent it. A person's areas are then where the weight of
their work falls, with citations used as the weight so that what someone is
known for counts more than what they tried once.

    python3 assign_taxonomy.py   ->  data/taxonomy.json, adds areas to people.json
"""
import json, re
from collections import Counter, defaultdict
from common import load, save
from taxonomy import TAXONOMY, flat, stats

RULES = [(area, sub, re.compile(pat, re.I)) for area, sub, pat in flat()]


def match(work):
    text = (work.get("title") or "") + " " + " ".join(work.get("keywords") or [])
    hits = []
    for area, sub, rx in RULES:
        if rx.search(text):
            hits.append((area, sub))
    return hits


def main():
    n_area, n_sub = stats()
    print(f"taxonomy: {n_area} areas, {n_sub} sub-areas")

    kw = load("keyword_works.json", {}) or {}
    works_by_person = kw.get("people", {})
    people = load("people.json", {}) or {}
    plist = people.get("people", [])
    by_name = {p["name"]: p for p in plist}

    area_works, sub_works = defaultdict(list), defaultdict(list)
    unmatched, total = 0, 0
    person_areas = defaultdict(Counter)
    person_subs = defaultdict(Counter)

    for name, works in works_by_person.items():
        for w in works:
            total += 1
            hits = match(w)
            if not hits:
                unmatched += 1
                continue
            # weight by citations so a person's areas reflect their impact,
            # with a floor so an uncited recent paper still counts for something
            weight = 1 + (w.get("citations") or 0) ** 0.5
            for area, sub in hits:
                person_areas[name][area] += weight
                person_subs[name][f"{area} / {sub}"] += weight
                if len(area_works[area]) < 400:
                    area_works[area].append({"person": name, **{k: w.get(k) for k in
                                            ("title", "url", "kind", "year", "citations")}})
                if len(sub_works[f"{area} / {sub}"]) < 200:
                    sub_works[f"{area} / {sub}"].append(
                        {"person": name, **{k: w.get(k) for k in
                         ("title", "url", "kind", "year", "citations")}})

    print(f"works: {total}, matched {total - unmatched} "
          f"({100 * (total - unmatched) // max(1, total)}%), unmatched {unmatched}")

    for p in plist:
        areas = person_areas.get(p["name"])
        if not areas:
            p["areas"] = []
            p["primary_area"] = None
            continue
        ranked = areas.most_common()
        p["primary_area"] = ranked[0][0]
        p["areas"] = [a for a, _ in ranked[:4]]
        p["sub_areas"] = [s for s, _ in person_subs[p["name"]].most_common(4)]

    # headline counts per node
    tax = {}
    for area, spec in TAXONOMY.items():
        subs = {}
        for sub in spec["subs"]:
            key = f"{area} / {sub}"
            ws = sub_works.get(key, [])
            subs[sub] = {
                "works": len(ws),
                "people": len({w["person"] for w in ws}),
                "top_works": sorted(ws, key=lambda w: -(w.get("citations") or 0))[:8],
            }
        people_in = sum(1 for p in plist if area in (p.get("areas") or []))
        tax[area] = {
            "blurb": spec["blurb"],
            "works": len(area_works.get(area, [])),
            "people": people_in,
            "primary_people": sum(1 for p in plist if p.get("primary_area") == area),
            "subs": subs,
        }

    save("taxonomy.json", {"areas": tax,
                           "matched_works": total - unmatched, "total_works": total})
    people["taxonomy_version"] = 1
    save("people.json", people)

    print("\narea                                   people  primary  works")
    for area, rec in sorted(tax.items(), key=lambda kv: -kv[1]["people"]):
        print(f"  {area[:36]:<38}{rec['people']:>5}{rec['primary_people']:>9}{rec['works']:>7}")


if __name__ == "__main__":
    main()
