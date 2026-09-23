#!/usr/bin/env python3
"""Lay works out by what they are about, not by which area owns them.

Until now a work's position was its area's centre plus a hash-based jitter, so
neighbouring dots had no relationship at all - which quietly made zooming in
meaningless. Here the layout comes from the SPECTER2 embeddings themselves:
PCA down to a manageable number of dimensions, then t-SNE to two, so works
about the same thing land together whether they are heavily cited or not.

Areas are not used to place anything. Where they end up - contiguous or
fragmented - is then a finding rather than an assumption.

    python3 build_layout.py   ->  data/layout.json
"""
import json, math
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from common import load, save

EXTENT = 620          # world half-size the layout is scaled into
PCA_DIMS = 50
PERPLEXITY = 34


def main():
    wa = (load("work_areas.json", {}) or {})
    works, areas = wa.get("works", {}), wa.get("areas", [])
    spec = load("specter.json", {}) or {}

    keys = [k for k in works if (spec.get(k) or {}).get("v")]
    print(f"{len(keys)} placed works have embeddings")
    if len(keys) < 50:
        raise SystemExit("not enough embeddings; run fetch_specter.py")

    X = np.array([spec[k]["v"] for k in keys], dtype=np.float32)
    X -= X.mean(0)                       # strip the shared "ML paper" direction
    X /= (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)

    print(f"PCA {X.shape[1]} -> {PCA_DIMS}")
    Xp = PCA(n_components=PCA_DIMS, random_state=7).fit_transform(X)
    print(f"t-SNE {PCA_DIMS} -> 2 (perplexity {PERPLEXITY}) - this takes a minute")
    Y = TSNE(n_components=2, perplexity=PERPLEXITY, init="pca", random_state=7,
             max_iter=1000, metric="cosine").fit_transform(Xp)

    Y -= Y.mean(0)
    Y /= (np.abs(Y).max() + 1e-9)
    Y *= EXTENT

    pos = {k: [round(float(Y[i][0]), 1), round(float(Y[i][1]), 1)] for i, k in enumerate(keys)}

    # where does each area sit now, and does it hold together?
    aidx = {a: i for i, a in enumerate(areas)}
    by_area = {a: [] for a in areas}
    for i, k in enumerate(keys):
        top = works[k]["areas"][0]["a"] if works[k].get("areas") else None
        if top in by_area:
            by_area[top].append(Y[i])
    stats = []
    for a, pts in by_area.items():
        if not pts:
            continue
        P = np.vstack(pts)
        c = np.median(P, axis=0)
        d = np.linalg.norm(P - c, axis=1)
        stats.append((a, len(pts), float(np.median(d)), c))
    stats.sort(key=lambda s: -s[1])
    print("\narea cohesion after layout (median distance from its own centre):")
    for a, n, md, c in stats[:10]:
        tag = "tight" if md < EXTENT * 0.30 else ("spread" if md < EXTENT * 0.55 else "FRAGMENTED")
        print(f"  {n:>5} works  median {md:6.1f}  {tag:<11} {a}")

    save("layout.json", {
        "extent": EXTENT,
        "pos": pos,
        "areas": [{"name": a, "x": round(float(c[0]), 1), "y": round(float(c[1]), 1),
                   "n": n, "scatter": round(md, 1)} for a, n, md, c in stats],
    })


if __name__ == "__main__":
    main()
