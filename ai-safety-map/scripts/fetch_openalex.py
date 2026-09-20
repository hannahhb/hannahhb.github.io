#!/usr/bin/env python3
"""Harvest AI-safety publications and their authors from OpenAlex.

Work-first: page through works matching a set of AI-safety queries, keep the
ones that look genuinely on-topic, then aggregate by author - how many safety
works, how cited, which topics, which institutions, and the three most cited
and three most recent works as links.

    python3 fetch_openalex.py [--since 2015] [--per-query 1000]

Writes data/openalex_authors.json and data/openalex_works.json.
OpenAlex is CC0 and needs no key; we use the polite pool via mailto.
"""
import argparse, json, re, sys, urllib.parse
from collections import defaultdict
from common import get, MAILTO, norm_name, save

API = "https://api.openalex.org/works"

QUERIES = [
    "AI alignment", "AI safety", "existential risk from artificial intelligence",
    "mechanistic interpretability", "interpretability of language models",
    "reinforcement learning from human feedback", "reward hacking",
    "specification gaming", "scalable oversight", "AI debate safety",
    "deceptive alignment", "situational awareness language model",
    "dangerous capability evaluation", "red teaming language models",
    "jailbreaking large language models", "adversarial robustness language model",
    "model evaluation frontier AI", "AI control protocol untrusted model",
    "chain-of-thought faithfulness", "sycophancy language model",
    "sparse autoencoder features language model", "activation steering language model",
    "value alignment machine learning", "corrigibility AI", "power-seeking AI",
    "AI governance policy", "compute governance", "frontier model regulation",
    "catastrophic risk artificial intelligence", "machine unlearning safety",
    "constitutional AI harmlessness", "emergent misalignment",
]

# A work counts only if it trips an UNAMBIGUOUS safety phrase. Bare "alignment"
# is deliberately absent: it matches sequence alignment, knee alignment, protein
# alignment and image registration, which flooded an earlier version of this
# harvest with orthopaedics and genomics.
ON_TOPIC = re.compile(
    r"\bAI safety\b|\bAGI safety\b|safety of (AI|AGI|language models|frontier)|"
    r"\bAI alignment\b|aligning (AI|language models|LLMs|AGI)|alignment of (AI|language models|LLMs)|"
    r"\bmisalign|\bmisaligned\b|value alignment|alignment faking|emergent misalignment|"
    r"existential risk|catastrophic risk|\bx-risk\b|extinction risk|superintelligen|"
    r"mechanistic interpretab|interpretability of (language models|neural networks|transformers)|"
    r"sparse autoencoder|activation (steering|patching|addition)|logit lens|probing classifier|"
    r"\bRLHF\b|reinforcement learning from human feedback|reward (hacking|misspecification|tampering)|"
    r"specification gaming|goal misgeneral|scalable oversight|weak.to.strong generaliz|"
    r"deceptive alignment|\bsandbag|situational awareness|strategic deception|scheming|"
    r"dangerous capabilit|capability evaluation|model evaluations? for|\bevals?\b.{0,20}frontier|"
    r"red.?team|jailbreak|prompt injection|sycophan|deceptive behaviou?r|"
    r"chain.of.thought (faithful|monitor|legib)|faithful(ness)? of (reasoning|explanations)|"
    r"corrigib|power.seeking|instrumental convergence|\bAI control\b|untrusted monitor|"
    r"AI governance|compute governance|frontier (model|AI) (regulation|governance|policy)|"
    r"model welfare|AI welfare|constitutional AI|harmlessness|"
    r"unlearning|machine unlearning|\bwatermark|dual.use",
    re.I)

# Applied-AI papers that borrow safety vocabulary. "AI alignment is all your need
# for future drug discovery" is a real paper that passed every earlier filter.
OFF_TITLE = re.compile(
    r"drug (discovery|design)|clinical|patient|radiolog|pharmac|oncolog|cancer|"
    r"diagnos|healthcare|medical imaging|protein|genom|molecul|surgery|surgical|"
    r"nursing|dental|agricultur|crop|materials discovery|battery|catalys|"
    r"wireless|antenna|traffic|manufactur|supply chain|finance|stock market",
    re.I)

# Whole research domains that cannot be AI safety, no matter what words appear.
OFF_DOMAIN = re.compile(
    r"Medicine|Biochem|Genetic|Genomic|Molecular Biology|Immunolog|Neuroscience|"
    r"Pharmacolog|Health|Nursing|Dentistry|Veterinary|Agricultur|Materials Science|"
    r"Chemistry|Chemical Engineering|Physics and Astronomy|Earth and Planetary|"
    r"Energy|Environmental Science|Economics, Econometrics|Business, Management",
    re.I)
# ... unless the work is squarely in one of these, which governance work often is
ON_DOMAIN = re.compile(r"Computer Science|Mathematics|Decision Sciences|Engineering|"
                       r"Social Sciences|Arts and Humanities|Psychology", re.I)

FIELDS = ("id,doi,title,display_name,publication_year,publication_date,cited_by_count,"
          "authorships,primary_location,topics,type,abstract_inverted_index")


def unabstract(inv):
    if not inv:
        return ""
    out = []
    for word, spots in inv.items():
        for s in spots:
            out.append((s, word))
    return " ".join(w for _, w in sorted(out))[:1200]


def page(query, since, cap):
    got, cursor = [], "*"
    while len(got) < cap and cursor:
        url = (f"{API}?search={urllib.parse.quote(query)}"
               f"&filter=from_publication_date:{since}-01-01,type:article|preprint"
               f"&per-page=200&cursor={urllib.parse.quote(cursor)}"
               f"&select={FIELDS}&mailto={MAILTO}")
        try:
            body = json.loads(get(url, pause=0.6))
        except Exception as e:
            print(f"    ! {query}: {e}", file=sys.stderr)
            break
        got.extend(body.get("results", []))
        cursor = (body.get("meta") or {}).get("next_cursor")
        if not body.get("results"):
            break
    return got[:cap]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=2015)
    ap.add_argument("--per-query", type=int, default=1000)
    args = ap.parse_args()

    works, skipped = {}, 0
    for q in QUERIES:
        hits = page(q, args.since, args.per_query)
        kept = 0
        for w in hits:
            wid = w.get("id")
            if not wid or wid in works:
                continue
            text = " ".join([w.get("display_name") or "", unabstract(w.get("abstract_inverted_index"))])
            if not ON_TOPIC.search(text):
                skipped += 1
                continue
            if OFF_TITLE.search(w.get("display_name") or ""):
                skipped += 1
                continue
            fields = {(t.get("field") or {}).get("display_name", "") for t in (w.get("topics") or [])}
            fields = " ; ".join(sorted(f for f in fields if f))
            if OFF_DOMAIN.search(fields) and not ON_DOMAIN.search(fields):
                skipped += 1
                continue
            if fields and not ON_DOMAIN.search(fields):
                skipped += 1
                continue
            loc = w.get("primary_location") or {}
            works[wid] = {
                "id": wid,
                "title": w.get("display_name") or w.get("title") or "",
                "year": w.get("publication_year"),
                "date": w.get("publication_date") or "",
                "cites": w.get("cited_by_count") or 0,
                "url": (loc.get("landing_page_url") or w.get("doi")
                        or wid.replace("https://openalex.org/", "https://openalex.org/")),
                "venue": ((loc.get("source") or {}) or {}).get("display_name") or "",
                "title_match": bool(ON_TOPIC.search(w.get("display_name") or "")),
                "topics": [t["display_name"] for t in (w.get("topics") or [])[:3]],
                "fields": sorted({(t.get("field") or {}).get("display_name","") for t in (w.get("topics") or [])} - {""}),
                "authors": [{
                    "id": (a.get("author") or {}).get("id"),
                    "name": (a.get("author") or {}).get("display_name"),
                    "insts": [i.get("display_name") for i in (a.get("institutions") or [])],
                    "pos": a.get("author_position"),
                } for a in (w.get("authorships") or [])],
            }
            kept += 1
        print(f"  {q[:44]:<46} {len(hits):>5} hits, {kept:>4} kept")

    print(f"\n{len(works)} on-topic works ({skipped} off-topic discarded)")

    people = defaultdict(lambda: {"works": [], "insts": defaultdict(int),
                                  "topics": defaultdict(int), "first_author": 0, "last_author": 0})
    for w in works.values():
        for a in w["authors"]:
            if not a["id"] or not a["name"]:
                continue
            rec = people[a["id"]]
            rec["name"] = a["name"]
            rec["works"].append({"title": w["title"], "url": w["url"], "year": w["year"],
                                 "date": w["date"], "cites": w["cites"], "venue": w["venue"],
                                 "strong": w["title_match"]})
            for i in a["insts"]:
                rec["insts"][i] += 1
            for t in w["topics"]:
                rec["topics"][t] += 1
            if a["pos"] == "first":
                rec["first_author"] += 1
            if a["pos"] == "last":
                rec["last_author"] += 1

    out = {}
    for aid, rec in people.items():
        ws = rec["works"]
        if len(ws) < 2:                      # the >=2 works rule, publication side
            continue
        by_cites = sorted(ws, key=lambda x: -x["cites"])
        by_date = sorted(ws, key=lambda x: x["date"] or "", reverse=True)
        out[aid] = {
            "name": rec["name"], "openalex_id": aid,
            "oa_works": len(ws),
            "oa_strong_works": sum(1 for w in ws if w.get("strong")),
            "oa_citations": sum(w["cites"] for w in ws),
            "oa_first_author": rec["first_author"], "oa_last_author": rec["last_author"],
            "oa_first_year": min((w["year"] for w in ws if w["year"]), default=None),
            "oa_last_year": max((w["year"] for w in ws if w["year"]), default=None),
            "oa_institutions": sorted(rec["insts"], key=lambda i: -rec["insts"][i])[:4],
            "oa_topics": sorted(rec["topics"], key=lambda t: -rec["topics"][t])[:8],
            "top_works": by_cites[:3], "recent_works": by_date[:3],
        }

    print(f"{len(out)} authors with 2+ on-topic works")
    save("openalex_works.json", list(works.values()))
    save("openalex_authors.json", out)


if __name__ == "__main__":
    main()
