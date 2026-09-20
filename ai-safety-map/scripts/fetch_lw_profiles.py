#!/usr/bin/env python3
"""Read affiliation off LessWrong/Alignment Forum profiles.

OpenAlex only records an institution when a paper carries one, and a great deal
of safety work is posted or preprinted without any affiliation at all - which is
why Redwood, Apollo and DeepMind researchers were coming through as 'unknown'.
People state where they work in their own profile bio, so we read that instead,
and match it against the org registry.

    python3 fetch_lw_profiles.py   ->  data/lesswrong_profiles.json
"""
import json, re, sys
from common import get, load, save
from orgs import registry_hit, sector_of

GQL = "https://www.lesswrong.com/graphql"
QUERY = ('{user(input:{selector:{slug:"%s"}}){result{displayName slug karma '
         'jobTitle organization website biography{html}}}}')

# "chief scientist at Redwood Research", "I work at Apollo Research", "(DeepMind)"
AT = re.compile(r"(?:\bat\b|\bwith\b|\bfor\b|\bjoined\b|\bwork(?:ing|s)? (?:at|for|on .{0,20}at))\s+"
                r"(?:the\s+)?([A-Z][\w&.'’-]*(?:\s+[A-Z(][\w&.'’)-]*){0,4})")


def strip_html(h):
    h = re.sub(r"<[^>]+>", " ", h or "")
    return re.sub(r"\s+", " ", h).strip()


def affiliation_from(text, job, org):
    """Registry match first, then a plain 'at <Org>' read of the bio."""
    for candidate in ([org] if org else []) + ([job] if job else []):
        hit = registry_hit(candidate)
        if hit:
            return hit["name"], "profile field"
    if not text:
        return (org or ""), ("profile field" if org else "")
    # registry names mentioned anywhere in the bio
    for m in re.finditer(r"[A-Z][\w&.'’-]*(?:\s+[A-Z(][\w&.'’)-]*){0,4}", text[:600]):
        hit = registry_hit(m.group(0))
        if hit:
            return hit["name"], "bio mention"
    for m in AT.finditer(text[:600]):
        cand = m.group(1).strip(" .,;")
        # a bare category word is not an employer: "works at University" told us
        # nothing, yet became an org with eleven people in it
        if cand.lower() in ("university", "college", "school", "institute", "lab",
                            "labs", "company", "startup", "home", "google", "the lab",
                            "a lab", "an ai lab", "ai", "research", "the university"):
            continue
        if len(cand.split()) < 2 and len(cand) < 6:
            continue
        if sector_of(cand) != "unknown":
            return cand, "bio phrase"
    return (org or ""), ("profile field" if org else "")


def main():
    authors = load("lesswrong_authors.json", {})
    slugs = [a["lw_slug"] for a in authors.values() if a.get("lw_slug")]
    print(f"reading {len(slugs)} LessWrong profiles")

    out, found = {}, 0
    for i, slug in enumerate(slugs, 1):
        try:
            body = get(GQL, data=json.dumps({"query": QUERY % slug}).encode(),
                       headers={"Content-Type": "application/json"}, pause=0.25)
            res = (json.loads(body).get("data") or {}).get("user") or {}
            res = res.get("result") or {}
        except Exception as e:
            print(f"    ! {slug}: {e}", file=sys.stderr)
            continue
        if not res:
            continue
        bio = strip_html(((res.get("biography") or {}) or {}).get("html"))
        inst, how = affiliation_from(bio, res.get("jobTitle"), res.get("organization"))
        out[slug] = {
            "slug": slug, "name": res.get("displayName"), "karma": res.get("karma") or 0,
            "job_title": res.get("jobTitle") or "", "organization": res.get("organization") or "",
            "website": res.get("website") or "", "bio": bio[:400],
            "institution": inst, "institution_source": how,
            "sector": sector_of(inst) if inst else "unknown",
        }
        if inst:
            found += 1
        if i % 150 == 0:
            print(f"  {i}/{len(slugs)}  affiliation found for {found}")

    print(f"\n{len(out)} profiles read, {found} with an affiliation we can place")
    from collections import Counter
    for k, v in Counter(p["sector"] for p in out.values()).most_common():
        print(f"  {v:>4}  {k}")
    save("lesswrong_profiles.json", out)


if __name__ == "__main__":
    main()
