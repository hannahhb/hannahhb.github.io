#!/usr/bin/env python3
"""Place works in research areas by what their abstracts say.

Regex on titles gave a hard yes/no on thin evidence, which is why areas
overlapped so messily. This is semi-supervised instead: the taxonomy's patterns
pick out high-confidence seed papers per area, a TF-IDF centroid is built from
those seeds' full abstracts, and every work is then scored against all centroids
to get a soft distribution over areas.

Overlap between two areas is then measurable: how much work genuinely sits in
both, summed over works, rather than how often two regexes happened to fire.

    python3 classify_content.py  ->  data/work_areas.json, data/overlap.json
"""
import json, re
from collections import Counter, defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from common import load, save
from taxonomy import TAXONOMY, flat

TOP_K = 4              # areas kept per work
SEED_MIN_HITS = 2      # regex hits in the abstract before a work seeds an area


def main():
    abstracts = load("abstracts.json", {}) or {}
    kw = (load("keyword_works.json", {}) or {}).get("people", {})
    print(f"{len(abstracts)} abstracts, {sum(len(v) for v in kw.values())} works to place")

    # ---- gather the works we care about, with their text ----
    works, seen = {}, set()
    for person, ws in kw.items():
        for w in ws:
            key = w.get("arxiv_id", "").split("v")[0].lower() or w.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            rec = abstracts.get(key)
            works[key] = {
                "key": key, "title": w.get("title") or "", "url": w.get("url"),
                "kind": w.get("kind"), "year": w.get("year"), "cites": w.get("citations"),
                "text": ((w.get("title") or "") + ". " + (rec["abstract"] if rec else "")).strip(),
                "has_abstract": bool(rec),
            }
    withab = sum(1 for w in works.values() if w["has_abstract"])
    print(f"{len(works)} distinct works, {withab} with an abstract "
          f"({100*withab//max(1,len(works))}%)")

    # ---- seed each area from high-confidence regex matches on the abstract ----
    areas = list(TAXONOMY)
    pats = defaultdict(list)
    for area, sub, pat in flat():
        pats[area].append(re.compile(pat, re.I))

    seeds = defaultdict(list)
    for w in works.values():
        if not w["has_abstract"]:
            continue
        for area in areas:
            hits = sum(1 for rx in pats[area] if rx.search(w["text"]))
            dense = sum(len(rx.findall(w["text"])) for rx in pats[area])
            if hits >= 1 and dense >= SEED_MIN_HITS:
                seeds[area].append(w["text"])
    print("\nseed papers per area:")
    for a in areas:
        print(f"  {len(seeds[a]):>5}  {a}")

    thin = [a for a in areas if len(seeds[a]) < 8]
    if thin:
        print(f"\n  thin seeds, centroid will be weak: {', '.join(thin)}")

    # ---- TF-IDF space over everything, centroids from the seeds ----
    corpus = [w["text"] for w in works.values()]
    vec = TfidfVectorizer(stop_words="english", max_features=40000,
                          ngram_range=(1, 2), sublinear_tf=True, min_df=3)
    X = vec.fit_transform(corpus)
    X = X / (np.sqrt(X.multiply(X).sum(1)) + 1e-9)

    cent = []
    for a in areas:
        if seeds[a]:
            S = vec.transform(seeds[a])
            v = np.asarray(S.mean(0)).ravel()
        else:
            v = np.asarray(vec.transform([" ".join(p.pattern for p in pats[a])]).todense()).ravel()
        cent.append(v / (np.linalg.norm(v) + 1e-9))
    C = np.vstack(cent)

    sim = np.asarray(X @ C.T)                       # works x areas
    order = np.argsort(-sim, axis=1)[:, :TOP_K]

    out, keys = {}, list(works)
    for i, key in enumerate(keys):
        scores = sim[i][order[i]]
        scores = np.clip(scores, 0, None)
        if scores.sum() <= 1e-6:
            continue
        share = scores / scores.sum()
        out[key] = {
            **{k: works[key][k] for k in ("title", "url", "kind", "year", "cites", "has_abstract")},
            "areas": [{"a": areas[order[i][j]], "w": round(float(share[j]), 3)}
                      for j in range(TOP_K) if share[j] >= 0.08],
        }

    # ---- area overlap: how much work genuinely sits in both ----
    n = len(areas)
    M = np.zeros((n, n))
    idx = {a: i for i, a in enumerate(areas)}
    for rec in out.values():
        a = rec["areas"]
        for x in range(len(a)):
            for y in range(len(a)):
                M[idx[a[x]["a"]], idx[a[y]["a"]]] += min(a[x]["w"], a[y]["w"])
    tot = np.diag(M).copy()
    J = np.zeros((n, n))
    for x in range(n):
        for y in range(n):
            d = tot[x] + tot[y] - M[x, y]
            J[x, y] = M[x, y] / d if d > 0 else 0

    print(f"\n{len(out)} works placed")
    print("\nstrongest area overlaps:")
    pairs = sorted(((J[x, y], areas[x], areas[y]) for x in range(n) for y in range(x + 1, n)),
                   reverse=True)[:10]
    for v, a, b in pairs:
        print(f"  {v:.3f}  {a[:30]:<32} <-> {b[:30]}")

    save("work_areas.json", {"areas": areas, "works": out})
    save("overlap.json", {"areas": areas, "volume": tot.round(1).tolist(),
                          "shared": M.round(2).tolist(), "jaccard": J.round(4).tolist()})


if __name__ == "__main__":
    main()
