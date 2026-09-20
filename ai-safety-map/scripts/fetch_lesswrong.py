#!/usr/bin/env python3
"""Harvest AI-safety writing from LessWrong / the Alignment Forum.

Pages through every post carrying one of the AI-safety tags below and
aggregates by author: how much they have written, how it was received, and
their three strongest and three most recent posts as links.

    python3 fetch_lesswrong.py [--since 2015] [--limit-per-tag 3000]

Writes data/lesswrong_authors.json. Uses the site's public GraphQL API.
"""
import argparse, json, sys
from collections import defaultdict
from common import get, norm_name, save

GQL = "https://www.lesswrong.com/graphql"

TAGS = [
    "ai-risk", "ai-governance", "ai-control", "ai-evaluations", "ai-timelines",
    "deceptive-alignment", "agent-foundations", "ai-alignment-fieldbuilding",
    "chain-of-thought-alignment", "ai-rights-welfare", "ai-sentience",
    "debate-ai-safety-technique-1", "aligned-ai-proposals", "ai-assisted-alignment",
    "ai-safety-2", "ai-boxing-containment", "ai-takeoff", "deception",
    "ai-safety-public-materials-1", "inner-alignment", "goal-directedness",
    "existential-risk", "corrigibility-1", "decision-theory", "embedded-agency",
    "agency", "ai-oversight", "ai-robustness",
]


def gql(query):
    body = get(GQL, data=json.dumps({"query": query}).encode(),
               headers={"Content-Type": "application/json"}, pause=0.3)
    out = json.loads(body)
    if "errors" in out and not out.get("data"):
        raise RuntimeError(out["errors"][:1])
    return out["data"]


def tag_ids():
    data = gql('{tags(input:{terms:{view:"allTagsAlphabetical",limit:500}})'
               '{results{_id name slug postCount}}}')
    by_slug = {t["slug"]: t for t in data["tags"]["results"]}
    found, missing = {}, []
    for slug in TAGS:
        if slug in by_slug:
            found[slug] = by_slug[slug]
        else:
            missing.append(slug)
    if missing:
        print(f"  (no such tag, skipped: {', '.join(missing)})", file=sys.stderr)
    return found


POST_FIELDS = ("_id title pageUrl baseScore voteCount commentCount postedAt af "
               "user{displayName slug karma} coauthors{displayName slug karma}")


def posts_for_tag(tag, cap, page=100):
    out, offset = [], 0
    while offset < cap:
        q = ('{posts(input:{terms:{view:"new",filterSettings:{tags:[{tagId:"%s",'
             'filterMode:"Required"}]},limit:%d,offset:%d}}){results{%s}}}'
             % (tag["_id"], min(page, cap - offset), offset, POST_FIELDS))
        try:
            res = gql(q)["posts"]["results"]
        except Exception as e:
            print(f"    ! {tag['slug']} at offset {offset}: {e}", file=sys.stderr)
            break
        if not res:
            break
        out.extend(res)
        offset += len(res)
        if len(res) < page:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", type=int, default=2015)
    ap.add_argument("--limit-per-tag", type=int, default=3000)
    args = ap.parse_args()

    tags = tag_ids()
    print(f"harvesting {len(tags)} AI-safety tags from LessWrong")

    seen, posts = set(), []
    for slug, tag in tags.items():
        got = posts_for_tag(tag, args.limit_per_tag)
        fresh = 0
        for p in got:
            if p["_id"] in seen:
                continue
            seen.add(p["_id"])
            if int(p["postedAt"][:4]) < args.since:
                continue
            posts.append(p)
            fresh += 1
        print(f"  {slug:<34} {len(got):>5} posts, {fresh:>5} new")

    # tag membership, second pass (cheap: reuse cache)
    tag_of = defaultdict(set)
    for slug, tag in tags.items():
        for p in posts_for_tag(tag, args.limit_per_tag):
            tag_of[p["_id"]].add(slug)

    authors = defaultdict(lambda: {"posts": [], "af_posts": 0})
    for p in posts:
        people = [p.get("user")] + (p.get("coauthors") or [])
        for u in people:
            if not u or not u.get("displayName"):
                continue
            rec = authors[u["slug"] or norm_name(u["displayName"])]
            rec["name"] = u["displayName"]
            rec["slug"] = u.get("slug")
            rec["karma_total"] = u.get("karma") or 0
            rec["posts"].append({
                "title": p["title"], "url": p["pageUrl"], "score": p.get("baseScore") or 0,
                "comments": p.get("commentCount") or 0, "date": p["postedAt"][:10],
                "af": bool(p.get("af")), "tags": sorted(tag_of.get(p["_id"], [])),
            })
            if p.get("af"):
                rec["af_posts"] += 1

    out = {}
    for key, rec in authors.items():
        ps = rec["posts"]
        if len(ps) < 2:                     # the >=2 works rule, LessWrong side
            continue
        by_score = sorted(ps, key=lambda x: -x["score"])
        by_date = sorted(ps, key=lambda x: x["date"], reverse=True)
        tally = defaultdict(int)
        for p in ps:
            for t in p["tags"]:
                tally[t] += 1
        out[key] = {
            "name": rec["name"], "lw_slug": rec.get("slug"),
            "lw_posts": len(ps), "lw_af_posts": rec["af_posts"],
            "lw_karma_total": rec["karma_total"],
            "lw_score_sum": sum(p["score"] for p in ps),
            "lw_first": min(p["date"] for p in ps), "lw_last": max(p["date"] for p in ps),
            "lw_tags": sorted(tally, key=lambda t: -tally[t])[:8],
            "top_posts": by_score[:3], "recent_posts": by_date[:3],
            # the full list, so downstream keyword scanning has something to scan
            "all_posts": by_date[:60],
        }

    print(f"\n{len(posts)} distinct posts -> {len(out)} authors with 2+ posts")
    save("lesswrong_authors.json", out)


if __name__ == "__main__":
    main()
