#!/usr/bin/env python3
"""Assign works to research areas using SPECTER2 embeddings.

Same shape as the TF-IDF version it replaces, but the space is different in a
way that matters: SPECTER2 is trained so that papers citing and cited by each
other sit close, so two papers about activation steering land together even
when they share almost no vocabulary. TF-IDF could only ever match words.

Seeds still come from the taxonomy's patterns - a small, high-confidence set
per area - but the centroid they define now lives in semantic space, and every
other work is placed by cosine distance to it.

    python3 classify_specter.py   ->  data/work_areas.json
"""
import json, re, sys
from collections import defaultdict

import numpy as np

from common import load, save
from relevance import score as rel_score
from taxonomy import TAXONOMY, flat

TOP_K = 4
REL_MIN = 2.0
SEED_MIN = 2          # regex hits before a work seeds an area
TEMP = 0.55           # softmax temperature, applied to z-scored similarity


def main():
    spec = load("specter.json", {}) or {}
    ab = load("abstracts.json", {}) or {}
    kw = (load("keyword_works.json", {}) or {}).get("people", {})
    if not spec:
        sys.exit("run fetch_specter.py first")

    # gather the works we care about, with text for relevance + seeding
    works, seen = {}, set()
    for ws in kw.values():
        for w in ws:
            key = (w.get("arxiv_id") or "").split("v")[0].lower() or w.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            s = spec.get(key) or {}
            rec = ab.get(key) or {}
            title = w.get("title") or s.get("title") or ""
            abstract = rec.get("abstract", "")
            works[key] = {
                "key": key, "title": title, "url": w.get("url"), "kind": w.get("kind"),
                "year": w.get("year"), "date": w.get("date"),
                "cites": s.get("cites", w.get("citations")),
                "tldr": s.get("tldr"), "venue": s.get("venue"),
                "rel": rel_score(title, abstract),
                "v": s.get("v"), "text": title + ". " + abstract,
            }

    embedded = [k for k, w in works.items() if w["v"]]
    print(f"{len(works)} works, {len(embedded)} with embeddings "
          f"({100*len(embedded)//max(1,len(works))}%)")

    keep = {k: w for k, w in works.items() if w["rel"] >= REL_MIN and w["v"]}
    print(f"relevance gate at {REL_MIN}: kept {len(keep)}")

    areas = list(TAXONOMY)
    pats = defaultdict(list)
    for area, sub, pat in flat():
        pats[area].append(re.compile(pat, re.I))

    # seeds: works whose text plainly belongs to an area
    # Every paper here is an ML paper, so raw SPECTER2 vectors all point much
    # the same way - pairwise cosine averages 0.87 with sd 0.03, which leaves a
    # softmax nothing to bite on. Removing the corpus mean strips out that
    # shared direction and widens the spread about fivefold; what remains is
    # the part that actually distinguishes one paper from another.
    raw = {k: np.array(w["v"], dtype=np.float32) for k, w in keep.items()}
    mu = np.mean(np.vstack(list(raw.values())), axis=0)
    V = {}
    for k, v in raw.items():
        d = v - mu
        V[k] = d / (np.linalg.norm(d) + 1e-9)

    cents, counts = [], []
    for a in areas:
        vs = []
        for k, w in keep.items():
            dense = sum(len(rx.findall(w["text"])) for rx in pats[a])
            if dense >= SEED_MIN:
                vs.append(V[k])
        counts.append(len(vs))
        if vs:
            c = np.mean(vs, axis=0)
        else:                                    # fall back to the area's own name
            c = np.mean([V[k] for k in list(V)[:50]], axis=0)
        cents.append(c / (np.linalg.norm(c) + 1e-9))
    C = np.vstack(cents)
    print("\nseeds per area:")
    for a, n in sorted(zip(areas, counts), key=lambda z: -z[1]):
        print(f"  {n:>5}  {a}")

    keys = list(keep)
    M = np.vstack([V[k] for k in keys])
    sim = M @ C.T                                  # cosine, both normalised

    out = {}
    for i, k in enumerate(keys):
        s = sim[i]
        # z-score across areas first: what matters is how much better the best
        # area fits than the rest for THIS paper, not the absolute similarity,
        # which varies with how typical the paper is overall
        z = (s - s.mean()) / (s.std() + 1e-6)
        e = np.exp((z - z.max()) / TEMP)
        p = e / e.sum()
        order = np.argsort(-p)[:TOP_K]
        w = keep[k]
        out[k] = {
            "title": w["title"], "url": w["url"], "kind": w["kind"], "year": w["year"],
            "date": w["date"], "cites": w["cites"], "rel": w["rel"], "tldr": w["tldr"],
            "venue": w["venue"], "has_abstract": True,
            "areas": [{"a": areas[j], "w": round(float(p[j]), 3)}
                      for j in order if p[j] >= 0.06],
        }

    # how decisive is the assignment? a healthy split has a clear leader
    lead = [max(m["w"] for m in r["areas"]) for r in out.values() if r["areas"]]
    lead.sort()
    print(f"\n{len(out)} works placed")
    print(f"top-area share: median {lead[len(lead)//2]:.2f}, "
          f"p10 {lead[len(lead)//10]:.2f}, p90 {lead[int(len(lead)*.9)]:.2f}")

    # overlap, same definition as before so the numbers stay comparable
    n = len(areas)
    idx = {a: i for i, a in enumerate(areas)}
    Mx = np.zeros((n, n))
    for rec in out.values():
        a = rec["areas"]
        for x in range(len(a)):
            for y in range(len(a)):
                Mx[idx[a[x]["a"]], idx[a[y]["a"]]] += min(a[x]["w"], a[y]["w"])
    tot = np.diag(Mx).copy()
    J = np.zeros((n, n))
    for x in range(n):
        for y in range(n):
            d = tot[x] + tot[y] - Mx[x, y]
            J[x, y] = Mx[x, y] / d if d > 0 else 0

    print("\nstrongest overlaps:")
    for v, a, b in sorted(((J[x, y], areas[x], areas[y])
                           for x in range(n) for y in range(x+1, n)), reverse=True)[:8]:
        print(f"  {v:.3f}  {a[:30]:<32} <-> {b[:30]}")

    save("work_areas.json", {"areas": areas, "works": out})
    save("overlap.json", {"areas": areas, "volume": tot.round(1).tolist(),
                          "shared": Mx.round(2).tolist(), "jaccard": J.round(4).tolist()})


if __name__ == "__main__":
    main()
