#!/usr/bin/env python3
"""Fill in citations and affiliations from Semantic Scholar.

Works backwards from papers we already know are a person's, rather than
searching by name: batch-lookup every harvested arXiv paper, read the
disambiguated authorId off it, then batch-lookup those authors. Name search
cannot tell two researchers called Wei Zhang apart; an authorId attached to a
paper we already attributed can.

Returns citation counts for free in the same call, which is what the rankings
have been missing.

    python3 fetch_s2.py            -> data/s2_papers.json, data/s2_authors.json

Needs a key in ~/.config/ai-safety-map/s2_key or $S2_API_KEY.
Rate limit is 1 request/second across all endpoints, so calls are paced at 1.1s.
"""
import argparse, json, sys
from collections import Counter, defaultdict
from common import S2_KEY, get, load, norm_name, save

S2 = "https://api.semanticscholar.org/graph/v1"
PAUSE = 1.15                       # the key allows 1 req/s; stay just under
PAPER_BATCH, AUTHOR_BATCH = 500, 1000


def post(path, ids, fields):
    return json.loads(get(f"{S2}/{path}?fields={fields}",
                          data=json.dumps({"ids": ids}).encode(),
                          headers={"Content-Type": "application/json",
                                   "x-api-key": S2_KEY},
                          pause=PAUSE))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit-authors", type=int, default=0,
                    help="cap author lookups (0 = all)")
    args = ap.parse_args()
    if not S2_KEY:
        sys.exit("no Semantic Scholar key found")

    works = (load("keyword_works.json", {}) or {}).get("people", {})
    by_person = {name: [w["arxiv_id"].split("v")[0] for w in ws
                        if w.get("kind") == "paper" and w.get("arxiv_id")]
                 for name, ws in works.items()}
    all_ids = sorted({i for v in by_person.values() for i in v})
    print(f"{len(all_ids)} distinct arXiv papers across {len(by_person)} people")

    papers = {}
    for i in range(0, len(all_ids), PAPER_BATCH):
        chunk = [f"ARXIV:{x}" for x in all_ids[i:i + PAPER_BATCH]]
        try:
            res = post("paper/batch", chunk,
                       "externalIds,title,year,citationCount,influentialCitationCount,"
                       "venue,authors")
        except Exception as e:
            print(f"    ! paper batch {i}: {e}", file=sys.stderr)
            continue
        for rec in res or []:
            if not rec:
                continue
            arx = (rec.get("externalIds") or {}).get("ArXiv")
            if arx:
                papers[arx.lower()] = rec
        print(f"  papers {min(i + PAPER_BATCH, len(all_ids))}/{len(all_ids)}", flush=True)
    print(f"  matched {len(papers)} papers")

    # a person's authorId is the one recurring across the papers we attributed
    picks, unresolved = {}, []
    for name, ids in by_person.items():
        tally = Counter()
        for pid in ids:
            rec = papers.get(pid.lower())
            for a in (rec or {}).get("authors") or []:
                if a.get("authorId") and norm_name(a.get("name")) == norm_name(name):
                    tally[a["authorId"]] += 1
        if tally:
            picks[name] = {"authorId": tally.most_common(1)[0][0],
                           "papers_agreeing": tally.most_common(1)[0][1],
                           "candidates": len(tally)}
        else:
            unresolved.append(name)
    print(f"\nresolved {len(picks)} author ids, {len(unresolved)} unresolved")

    ids = [v["authorId"] for v in picks.values()]
    if args.limit_authors:
        ids = ids[:args.limit_authors]
    authors = {}
    for i in range(0, len(ids), AUTHOR_BATCH):
        try:
            res = post("author/batch", ids[i:i + AUTHOR_BATCH],
                       "name,affiliations,paperCount,citationCount,hIndex,homepage")
        except Exception as e:
            print(f"    ! author batch {i}: {e}", file=sys.stderr)
            continue
        for rec in res or []:
            if rec and rec.get("authorId"):
                authors[rec["authorId"]] = rec
        print(f"  authors {min(i + AUTHOR_BATCH, len(ids))}/{len(ids)}", flush=True)

    out = {}
    for name, pick in picks.items():
        rec = authors.get(pick["authorId"])
        if not rec:
            continue
        out[name] = {
            "name": name, "s2_author_id": pick["authorId"],
            "papers_agreeing": pick["papers_agreeing"], "id_candidates": pick["candidates"],
            "s2_name": rec.get("name"), "affiliations": rec.get("affiliations") or [],
            "s2_paper_count": rec.get("paperCount"), "s2_citations": rec.get("citationCount"),
            "h_index": rec.get("hIndex"), "homepage": rec.get("homepage"),
        }
    withaff = sum(1 for v in out.values() if v["affiliations"])
    print(f"\n{len(out)} authors fetched, {withaff} with an affiliation listed")
    save("s2_papers.json", papers)
    save("s2_authors.json", out)


if __name__ == "__main__":
    main()
