#!/usr/bin/env python3
"""Merge the LessWrong and OpenAlex harvests into one dataset of people.

Inclusion rule: at least two public AI-safety works, counting peer-reviewed
papers and preprints (OpenAlex) and Alignment Forum / LessWrong posts alike.
Each person carries their three most-cited (or most-upvoted) and three most
recent works as links, a sector, a career stage, and a topic cluster derived
from those top works.

    python3 build_dataset.py [--clusters 14]

Writes data/people.json.
"""
import argparse, datetime, math, re
from collections import defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

from common import load, norm_name, save
from orgs import classify, SECTOR_LABEL, SIDE

YEAR = datetime.date.today().year

# LessWrong tag slug -> a readable topic, so both sources speak the same language
TAG_TOPIC = {
    "ai-risk": "AI risk", "ai-governance": "AI governance", "ai-control": "AI control",
    "ai-evaluations": "Evaluations", "ai-timelines": "Forecasting & timelines",
    "deceptive-alignment": "Deception & scheming", "agent-foundations": "Agent foundations",
    "ai-alignment-fieldbuilding": "Field-building", "chain-of-thought-alignment": "Chain of thought",
    "ai-rights-welfare": "AI welfare", "ai-sentience": "AI welfare",
    "debate-ai-safety-technique-1": "Debate & oversight", "aligned-ai-proposals": "Alignment proposals",
    "ai-assisted-alignment": "Automated alignment research", "ai-safety-2": "AI safety",
    "ai-boxing-containment": "Containment", "ai-takeoff": "Takeoff dynamics",
    "deception": "Deception & scheming", "ai-safety-public-materials-1": "Communication",
    "inner-alignment": "Inner alignment", "goal-directedness": "Agency & goals",
    "existential-risk": "Existential risk", "corrigibility-1": "Corrigibility",
    "decision-theory": "Decision theory", "embedded-agency": "Embedded agency",
    "agency": "Agency & goals", "ai-oversight": "Debate & oversight", "ai-robustness": "Robustness",
}

TIERS = [(2, 3, "2-3 works"), (4, 9, "4-9 works"), (10, 24, "10-24 works"),
         (25, 10**6, "25+ works")]


def tier(n):
    for lo, hi, label in TIERS:
        if lo <= n <= hi:
            return label
    return TIERS[0][2]


def career_stage(p):
    """How long someone has been publishing IN AI SAFETY - not career seniority.

    This deliberately measures tenure in the field rather than career stage,
    because the harvest only sees safety work: Yoshua Bengio has a short safety
    record and a very long career, and calling him 'early career' would be
    wrong. Use leads_work (last-author count) as the PI signal instead.

    Last-author position is the strongest signal of running a group; failing
    that, how long someone has been publishing. Anyone we cannot place lands
    in 'mid', never silently in one of the two categories being compared.
    """
    last_auth = p.get("oa_last_author", 0)
    first_year = p.get("oa_first_year")
    span = (YEAR - first_year) if first_year else None
    if last_auth >= 3 or (last_auth >= 2 and (span or 0) >= 6):
        return "established"
    if span is not None and span >= 9:
        return "established"
    if span is not None and span <= 4 and last_auth == 0:
        return "early"
    if first_year is None:                       # LessWrong-only writers
        lw_first = p.get("lw_first")
        if lw_first:
            yrs = YEAR - int(lw_first[:4])
            return "established" if yrs >= 9 else ("early" if yrs <= 4 else "mid")
    return "mid"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", type=int, default=14)
    args = ap.parse_args()

    profiles = load("lesswrong_profiles.json", {})
    s2 = load("s2_authors.json", {})
    lw = load("lesswrong_authors.json", {})
    oa = load("openalex_authors.json", {})
    print(f"loaded {len(lw)} LessWrong authors, {len(oa)} OpenAlex authors")

    people = {}

    def slot(name):
        key = norm_name(name)
        if not key or len(key.split()) < 2:       # drop handles like "gwern", "So8res"
            key = "handle:" + norm_name(name)
        if key not in people:
            people[key] = {"key": key, "name": name, "sources": []}
        return people[key]

    for rec in oa.values():
        p = slot(rec["name"])
        p.update({k: v for k, v in rec.items() if k != "name"})
        p["sources"].append("openalex")

    for rec in lw.values():
        p = slot(rec["name"])
        for k, v in rec.items():
            if k != "name":
                p[k] = v
        p["sources"].append("lesswrong")

    out = []
    for p in people.values():
        n_oa, n_lw = p.get("oa_works", 0), p.get("lw_posts", 0)
        total = n_oa + n_lw
        if total < 2:
            continue

        sector, inst = classify(p.get("oa_institutions") or [])
        inst_source = "paper affiliation" if inst else ""
        prof = profiles.get(p.get("lw_slug") or "") or {}
        if prof.get("institution") and prof.get("sector") != "unknown":
            # a bio someone wrote about themselves is current; a paper's
            # affiliation is whatever was true when it was published
            sector, inst = prof["sector"], prof["institution"]
            inst_source = prof.get("institution_source", "profile bio")
        topics = list(p.get("oa_topics") or [])
        topics += [TAG_TOPIC[t] for t in (p.get("lw_tags") or []) if t in TAG_TOPIC]
        seen, uniq = set(), []
        for t in topics:
            if t.lower() not in seen:
                seen.add(t.lower()); uniq.append(t)

        # three best and three newest, papers and posts pooled
        best = [dict(w, kind="paper", weight=w["cites"]) for w in (p.get("top_works") or [])]
        best += [dict(w, kind="post", weight=w["score"], year=int(w["date"][:4]))
                 for w in (p.get("top_posts") or [])]
        best.sort(key=lambda w: -w["weight"])
        recent = [dict(w, kind="paper") for w in (p.get("recent_works") or [])]
        recent += [dict(w, kind="post", year=int(w["date"][:4]))
                   for w in (p.get("recent_posts") or [])]
        recent.sort(key=lambda w: (w.get("date") or str(w.get("year") or "")), reverse=True)

        def trim(w):
            return {"title": w.get("title"), "url": w.get("url"), "kind": w["kind"],
                    "year": w.get("year"), "cites": w.get("cites"), "score": w.get("score"),
                    "venue": w.get("venue")}

        out.append({
            "key": p["key"], "name": p["name"], "sources": sorted(set(p["sources"])),
            "works_total": total, "papers": n_oa, "posts": n_lw,
            "citations": p.get("oa_citations", 0),
            "post_score": p.get("lw_score_sum", 0),
            "af_posts": p.get("lw_af_posts", 0),
            "sector": sector, "sector_label": SECTOR_LABEL[sector], "side": SIDE[sector],
            # How much to trust that this is an AI-safety researcher at all.
            # 'strong' works are those whose TITLE names a safety topic, not just
            # an abstract that mentions one in passing - which is where the
            # search noise (applied-AI papers borrowing the vocabulary) lands.
            "strong_works": p.get("oa_strong_works", 0) + n_lw,
            "confidence": ("high" if n_lw >= 2 or p.get("oa_strong_works", 0) >= 2
                           else "medium" if (p.get("oa_strong_works", 0) >= 1 or n_lw >= 1)
                           else "low"),
            "institution": inst, "institution_source": inst_source,
            "institutions": p.get("oa_institutions") or [],
            "safety_tenure": career_stage(p), "leads_work": p.get("oa_last_author", 0),
            **({"h_index": s2[p["name"]].get("h_index"),
                "total_papers": s2[p["name"]].get("s2_paper_count"),
                "total_citations": s2[p["name"]].get("s2_citations"),
                "s2_author_id": s2[p["name"]].get("s2_author_id"),
                "seniority": ("senior" if (s2[p["name"]].get("h_index") or 0) >= 25
                              else "mid" if (s2[p["name"]].get("h_index") or 0) >= 10
                              else "junior")}
               if p["name"] in s2 else {}),
            "first_year": p.get("oa_first_year") or (int(p["lw_first"][:4]) if p.get("lw_first") else None),
            "last_year": p.get("oa_last_year") or (int(p["lw_last"][:4]) if p.get("lw_last") else None),
            "tier": tier(total),
            "topics": uniq[:8],
            "openalex_id": p.get("openalex_id"),
            "lw_slug": p.get("lw_slug"),
            "top_works": [trim(w) for w in best[:3]],
            "recent_works": [trim(w) for w in recent[:3]],
        })

    print(f"{len(out)} people with 2+ AI-safety works")

    # ---- topic clusters, from the top works' titles, venues and topic labels ----
    # Cluster on what people actually wrote. OpenAlex's own topic labels are far
    # too coarse for this - "Topic Modeling" and "Ethics and Social Impacts of AI"
    # cover a third of the corpus between them and collapse everything into one
    # bucket - so titles carry the signal and safety-specific tags reinforce it.
    docs = []
    for p in out:
        titles = " ".join((w["title"] or "") for w in p["top_works"] + p["recent_works"])
        safety_tags = " ".join(t for t in p["topics"] if t in set(TAG_TOPIC.values()))
        docs.append(titles + " " + (safety_tags + " ") * 3)
    X = TfidfVectorizer(stop_words="english", max_features=8000, ngram_range=(1, 2),
                        sublinear_tf=True, min_df=3).fit_transform(docs).toarray()
    X = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    k = min(args.clusters, max(2, len(out) // 12))
    labels = AgglomerativeClustering(n_clusters=k, metric="cosine",
                                     linkage="average").fit(X).labels_

    # name each cluster after the topics its members actually share
    members = defaultdict(list)
    for p, c in zip(out, labels):
        members[int(c)].append(p)
    names = {}
    for c, group in members.items():
        tally = defaultdict(int)
        for p in group:
            for t in p["topics"][:4]:
                tally[t] += 1
        # name a cluster from the words that distinguish it, not its members' labels
        from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
        words = defaultdict(int)
        for p in group:
            for w in p["top_works"][:3]:
                for tok in re.findall(r"[a-z][a-z-]{3,}", (w["title"] or "").lower()):
                    if tok not in ENGLISH_STOP_WORDS and tok not in ("using", "towards",
                            "language", "models", "model", "large", "learning", "with"):
                        words[tok] += 1
        # distinguishing words: frequent here, rare elsewhere
        elsewhere = defaultdict(int)
        for other_c, other in members.items():
            if other_c == c:
                continue
            for q in other:
                for w in q["top_works"][:3]:
                    for tok in re.findall(r"[a-z][a-z-]{3,}", (w["title"] or "").lower()):
                        elsewhere[tok] += 1
        n_here, n_else = max(1, len(group)), max(1, len(out) - len(group))
        scored = sorted(words, key=lambda w: -((words[w] / n_here) / (elsewhere[w] / n_else + 0.004)))
        picks = [w for w in scored if words[w] >= max(2, len(group) // 25)][:3]
        safety_tag = sorted(tally, key=lambda t: -tally[t])[:1]
        names[c] = (", ".join(picks).title() if picks
                    else (safety_tag[0] if safety_tag else f"Cluster {c}"))
    for p, c in zip(out, labels):
        p["cluster"] = int(c)
        p["cluster_name"] = names[int(c)]

    out.sort(key=lambda p: (-p["works_total"], -p["citations"]))
    save("people.json", {"generated": str(datetime.date.today()),
                         "clusters": names, "people": out})

    # ---- a short read-out, so the shape of the thing is visible ----
    from collections import Counter
    print("\nby sector:")
    for kk, v in Counter(p["sector_label"] for p in out).most_common():
        print(f"  {v:>5}  {kk}")
    print("\nby tenure in AI safety:")
    for kk, v in Counter(p["safety_tenure"] for p in out).most_common():
        print(f"  {v:>5}  {kk}")
    print("\nby output tier:")
    for _, _, lab in TIERS:
        print(f"  {sum(1 for p in out if p['tier'] == lab):>5}  {lab}")
    print("\nclusters:")
    for c, nm in sorted(names.items()):
        print(f"  {len(members[c]):>5}  {nm}")


if __name__ == "__main__":
    main()
