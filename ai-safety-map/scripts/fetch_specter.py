#!/usr/bin/env python3
"""Fetch SPECTER2 document embeddings (and TL;DRs) for every harvested work.

TF-IDF over abstracts was the weakest link in this pipeline: it needed
hand-written regex seeds to bootstrap each area, and it clusters on shared
vocabulary rather than shared meaning. SPECTER2 is trained on the citation
graph specifically so that papers about the same thing land near each other,
which is exactly the judgement the area assignment needs.

    python3 fetch_specter.py   ->  data/specter.json

768 floats per paper, so this file is large and stays out of the repo; only
the area assignments derived from it are shipped.
"""
import json, sys
from common import S2_KEY, get, load, save

BATCH = 100          # embeddings are heavy; smaller batches are kinder
FIELDS = "externalIds,title,citationCount,influentialCitationCount,venue,tldr,embedding.specter_v2"


def main():
    kw = (load("keyword_works.json", {}) or {}).get("people", {})
    ids, seen = [], set()
    for ws in kw.values():
        for w in ws:
            a = (w.get("arxiv_id") or "").split("v")[0].lower()
            if a and a not in seen:
                seen.add(a); ids.append(a)
    print(f"{len(ids)} distinct arXiv papers to embed")

    out = load("specter.json", {}) or {}
    todo = [i for i in ids if i not in out]
    print(f"{len(out)} already cached, {len(todo)} to fetch")

    for i in range(0, len(todo), BATCH):
        chunk = [f"ARXIV:{x}" for x in todo[i:i + BATCH]]
        try:
            res = json.loads(get("https://api.semanticscholar.org/graph/v1/paper/batch"
                                 f"?fields={FIELDS}",
                                 data=json.dumps({"ids": chunk}).encode(),
                                 headers={"Content-Type": "application/json",
                                          "x-api-key": S2_KEY}, pause=1.25))
        except Exception as e:
            print(f"    ! batch {i}: {e}", file=sys.stderr)
            continue
        for rec in res or []:
            if not rec:
                continue
            aid = ((rec.get("externalIds") or {}).get("ArXiv") or "").lower()
            emb = (rec.get("embedding") or {}).get("vector")
            if not aid:
                continue
            out[aid] = {
                "title": rec.get("title"), "cites": rec.get("citationCount"),
                "infl": rec.get("influentialCitationCount"), "venue": rec.get("venue"),
                "tldr": ((rec.get("tldr") or {}) or {}).get("text"),
                "v": [round(x, 4) for x in emb] if emb else None,
            }
        done = i + len(chunk)
        if (i // BATCH) % 5 == 0 or done >= len(todo):
            withv = sum(1 for r in out.values() if r.get("v"))
            print(f"  {done}/{len(todo)}  ({withv} with embeddings)", flush=True)
            save("specter.json", out)

    withv = sum(1 for r in out.values() if r.get("v"))
    withtl = sum(1 for r in out.values() if r.get("tldr"))
    print(f"\n{len(out)} papers: {withv} with embeddings, {withtl} with TL;DRs")
    save("specter.json", out)


if __name__ == "__main__":
    main()
