#!/usr/bin/env python3
"""Fold the topic-driven arXiv harvest into the main dataset.

The author-driven pass could only find papers by people already known. This
adds whatever the vocabulary surfaced - judged on its own title and abstract,
then given citation counts from Semantic Scholar - and admits its authors as
researchers in their own right.

    python3 merge_arxiv.py   ->  updates data/keyword_works.json, data/abstracts.json
"""
import json, sys
from collections import defaultdict
from common import S2_KEY, get, load, save, norm_name
from relevance import score as rel_score

REL_MIN = 2.0
BATCH = 500


def main():
    topics = load("arxiv_topics.json", {}) or {}
    if not topics:
        sys.exit("run fetch_arxiv_topics.py first")
    print(f"{len(topics)} harvested papers")

    keep = {k: v for k, v in topics.items()
            if rel_score(v.get("title", ""), v.get("abstract", "")) >= REL_MIN}
    print(f"relevance gate at {REL_MIN}: kept {len(keep)}")

    # citations, in batches of 500
    cites, ids = {}, [f"ARXIV:{k}" for k in keep]
    for i in range(0, len(ids), BATCH):
        try:
            res = json.loads(get("https://api.semanticscholar.org/graph/v1/paper/batch"
                                 "?fields=citationCount,externalIds,venue",
                                 data=json.dumps({"ids": ids[i:i+BATCH]}).encode(),
                                 headers={"Content-Type": "application/json",
                                          "x-api-key": S2_KEY}, pause=1.2))
        except Exception as e:
            print(f"    ! batch {i}: {e}", file=sys.stderr)
            continue
        for rec in res or []:
            if not rec:
                continue
            a = ((rec.get("externalIds") or {}).get("ArXiv") or "").lower()
            if a:
                cites[a] = {"c": rec.get("citationCount"), "v": rec.get("venue")}
        print(f"  citations {min(i+BATCH,len(ids))}/{len(ids)}", flush=True)

    # merge into the person -> works structure the pipeline already reads
    kw = load("keyword_works.json", {}) or {}
    people = kw.setdefault("people", {})
    have = {w.get("arxiv_id", "").split("v")[0].lower()
            for ws in people.values() for w in ws if w.get("arxiv_id")}
    added, new_people = 0, set()
    for aid, p in keep.items():
        if aid.lower() in have:
            continue
        c = cites.get(aid.lower(), {})
        entry = {"title": p["title"], "url": p["url"], "arxiv_id": aid, "kind": "paper",
                 "date": p["date"], "year": p["year"], "citations": c.get("c"),
                 "venue": c.get("v"), "keywords": [], "keyword_hits": 0, "strong_hits": 0,
                 "rel": round(rel_score(p["title"], p.get("abstract", "")), 2)}
        for name in p.get("authors", [])[:8]:
            if not name or len(name.split()) < 2:
                continue
            if name not in people:
                new_people.add(name)
            people.setdefault(name, []).append(entry)
        added += 1

    # abstracts, so classification can read them
    ab = load("abstracts.json", {}) or {}
    for aid, p in keep.items():
        ab.setdefault(aid.lower(), {"id": aid.lower(), "title": p["title"],
                                    "abstract": p["abstract"], "src": "arxiv-topic"})

    kw["works_total"] = sum(len(v) for v in people.values())
    print(f"\nadded {added} papers, {len(new_people)} researchers new to the dataset")
    print(f"people now: {len(people)}, work rows: {kw['works_total']}")
    save("keyword_works.json", kw)
    save("abstracts.json", ab)


if __name__ == "__main__":
    main()
