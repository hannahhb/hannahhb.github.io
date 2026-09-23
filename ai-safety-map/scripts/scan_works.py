#!/usr/bin/env python3
"""Pull a person's recent technical work and rank it by keyword-matched impact.

Finds their papers on arXiv and their posts on LessWrong / the Alignment Forum,
keeps only those published since --since that hit the technical keyword
vocabulary, and ranks them. Papers outrank posts regardless of score, per the
rule that a preprint is a stronger signal than a forum post.

    python3 scan_works.py --person "Neel Nanda"
    python3 scan_works.py --all --min-works 4        # everyone in people.json
    python3 scan_works.py --person "Neel Nanda" --since 2021 --top 10

Citations come from OpenAlex when OPENALEX_API_KEY is set, or Semantic Scholar
when S2_API_KEY is set. With neither, works are ranked by recency and keyword
density and marked `citations: null` rather than guessed at.
"""
import argparse, datetime, concurrent.futures as futures, json, os, re, sys, threading, urllib.parse
from common import get, load, save, norm_name

ARXIV = "https://export.arxiv.org/api/query"
PAUSE = 3.2          # seconds between arXiv requests; lowered when parallel
YEARS = 3.0          # harvest window in years; set from --since, scales the per-person quota
S2 = "https://api.semanticscholar.org/graph/v1"
OA = "https://api.openalex.org/works"
S2_KEY = os.environ.get("S2_API_KEY", "").strip()
OA_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()


# Model releases and capability tech reports mention red-teaming in their cards,
# so they trip the safety vocabulary while not being safety research. Left in,
# they dominate every ranking: "The Llama 3 Herd of Models" has 18,734 citations
# and shows up for each of its co-authors.
CAPABILITY_PAPER = re.compile(
    r"\b(herd of models|technical report|model card|system card)\b|"
    r"^(llama|qwen|gemma|gemini|mistral|deepseek|phi|olmo|yi|baichuan|internlm|"
    r"glm|command|claude|gpt-?\d|grok|falcon|bloom|pythia|starcoder)\b.{0,40}"
    r"(technical report|model|family|series|herd)?$|"
    r"\b(a family of|open (weight|source) (foundation|language) models|"
    r"frontier model family)\b",
    re.I)


def vocabulary():
    kw = load("keywords.json", {})
    terms = sorted(kw.get("terms", {}), key=len, reverse=True)
    if not terms:
        sys.exit("no keywords.json - run build_keywords.py first")
    # one alternation; longest-first so "sparse autoencoder" wins over "autoencoder"
    rx = re.compile(r"(?<![a-z])(" + "|".join(re.escape(t) for t in terms) + r")(?![a-z])", re.I)
    return kw["terms"], rx


def arxiv_works(name, since, cap=120):
    q = f'au:"{name}"'
    url = (f"{ARXIV}?search_query={urllib.parse.quote(q)}&start=0&max_results={cap}"
           f"&sortBy=submittedDate&sortOrder=descending")
    try:
        xml = get(url, pause=PAUSE)
    except Exception as e:
        print(f"    ! arxiv {name}: {e}", file=sys.stderr)
        return []
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        def tag(t):
            m = re.search(rf"<{t}>(.*?)</{t}>", e, re.S)
            return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
        published = tag("published")[:10]
        if not published or int(published[:4]) < since:
            continue
        authors = re.findall(r"<name>(.*?)</name>", e)
        if not any(norm_name(name) == norm_name(a) for a in authors):
            continue                        # arXiv author search is fuzzy
        aid = re.search(r"<id>http://arxiv\.org/abs/([^<]+)", e)
        out.append({
            "title": tag("title"), "abstract": tag("summary"),
            "date": published, "year": int(published[:4]),
            "arxiv_id": aid.group(1) if aid else "",
            "url": f"https://arxiv.org/abs/{aid.group(1)}" if aid else "",
            "doi": f"10.48550/arXiv.{aid.group(1).split('v')[0]}" if aid else "",
            "kind": "paper", "authors": authors,
        })
    return out


_LW_BY_NAME = None


def lw_index():
    """LessWrong authors keyed by normalised display name."""
    global _LW_BY_NAME
    if _LW_BY_NAME is None:
        _LW_BY_NAME = {}
        for rec in (load("lesswrong_authors.json", {}) or {}).values():
            if rec.get("name"):
                _LW_BY_NAME[norm_name(rec["name"])] = rec
    return _LW_BY_NAME


def lw_posts(name, since):
    rec = lw_index().get(norm_name(name)) or {}
    out = []
    for key in ("all_posts", "top_posts", "recent_posts"):
        for p in rec.get(key, []) or []:
            if p.get("date", "")[:4].isdigit() and int(p["date"][:4]) >= since:
                out.append({"title": p["title"], "abstract": "", "date": p["date"],
                            "year": int(p["date"][:4]), "url": p["url"],
                            "kind": "post", "score": p.get("score", 0)})
    seen, uniq = set(), []
    for p in out:
        if p["url"] not in seen:
            seen.add(p["url"]); uniq.append(p)
    return uniq


_S2_PAPERS = None


def s2_papers():
    global _S2_PAPERS
    if _S2_PAPERS is None:
        _S2_PAPERS = load("s2_papers.json", {}) or {}
    return _S2_PAPERS


def citations_for(works):
    """Fill citation counts where a key makes it possible; otherwise leave null."""
    cache = s2_papers()
    if cache:
        hit = 0
        for w in works:
            rec = cache.get(w.get("arxiv_id", "").split("v")[0].lower())
            if rec:
                w["citations"] = rec.get("citationCount")
                w["influential_citations"] = rec.get("influentialCitationCount")
                if rec.get("venue"):
                    w["venue"] = rec["venue"]
                hit += 1
        if hit:
            return "semanticscholar (cached)"
    if OA_KEY:
        for w in works:
            if w["kind"] != "paper" or not w.get("doi"):
                continue
            try:
                body = json.loads(get(f"{OA}/https://doi.org/{w['doi']}"
                                      f"?select=cited_by_count&mailto=drvkbansal@gmail.com",
                                      pause=0.2))
                w["citations"] = body.get("cited_by_count")
            except Exception:
                pass
        return "openalex"
    if S2_KEY:
        ids = [f"ARXIV:{w['arxiv_id'].split('v')[0]}" for w in works
               if w["kind"] == "paper" and w.get("arxiv_id")]
        for i in range(0, len(ids), 100):
            try:
                body = get(f"{S2}/paper/batch?fields=citationCount,externalIds",
                           data=json.dumps({"ids": ids[i:i + 100]}).encode(),
                           headers={"Content-Type": "application/json",
                                    "x-api-key": S2_KEY}, pause=1.0)
                for rec in json.loads(body):
                    if not rec:
                        continue
                    aid = ((rec.get("externalIds") or {}).get("ArXiv") or "").lower()
                    for w in works:
                        if w.get("arxiv_id", "").split("v")[0].lower() == aid:
                            w["citations"] = rec.get("citationCount")
            except Exception as e:
                print(f"    ! semanticscholar: {e}", file=sys.stderr)
        return "semanticscholar"
    return None


def depth_for(person, years=3.0):
    """How many works to keep. An established researcher with a long record
    needs a wider sample before their interests are legible; someone with a
    handful of works is fully described by ten.

    The quota scales with the harvest window. hits are ranked by citations, so
    holding the quota fixed while widening the window lets older, better-cited
    work crowd the recent work out of a person's slots - the window would grow
    at the back and quietly shrink at the front."""
    span = max(1.0, years / 3.0)
    if not person:
        base = 10
    elif person.get("works_total", 0) >= 25 or person.get("leads_work", 0) >= 3:
        base = 20
    elif person.get("works_total", 0) >= 10:
        base = 15
    else:
        base = 10
    return int(round(base * span))


def scan(name, person, terms, rx, since, top):
    works = arxiv_works(name, since) + lw_posts(name, since)
    hits = []
    for w in works:
        found = {m.group(1).lower() for m in rx.finditer(w["title"] + " " + w.get("abstract", ""))}
        # a seed term is a term of art; a mined term is weaker evidence
        strong = {t for t in found if terms.get(t, {}).get("source") == "seed"}
        if not found:
            continue
        if CAPABILITY_PAPER.search(w["title"] or ""):
            continue
        w["keywords"] = sorted(found)[:12]
        w["keyword_hits"] = len(found)
        w["strong_hits"] = len(strong)
        w.pop("abstract", None)
        hits.append(w)

    source = citations_for(hits)
    # papers before posts, then citations, then keyword strength, then recency
    hits.sort(key=lambda w: (0 if w["kind"] == "paper" else 1,
                             -(w.get("citations") if w.get("citations") is not None
                               else w.get("score", 0) / 10),
                             -w["strong_hits"], w["date"]), reverse=False)
    return hits[:top], source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--person", help="one person by name")
    ap.add_argument("--all", action="store_true", help="everyone in people.json")
    ap.add_argument("--names", help="extra names to scan, one per line, unioned with --all. "
                    "people.json is the curated roster; the literature is written by more "
                    "people than that, and dropping them shrinks the map at its recent edge")
    ap.add_argument("--min-works", type=int, default=6,
                    help="with --all, only scan people at least this productive")
    ap.add_argument("--since", type=int, default=2021)
    ap.add_argument("--top", type=int, default=0,
                    help="fixed depth; 0 (default) scales it to how established "
                         "someone is - more works means a fuller picture is useful")
    ap.add_argument("--workers", type=int, default=8,
                    help="parallel arXiv fetches. arXiv asks for one request every "
                         "3s; raising this ignores that, and they do block clients "
                         "that push too hard - 8 is brisk without being abusive")
    ap.add_argument("--skip-confidence", default="low",
                    help="comma-separated confidence levels to skip with --all")
    args = ap.parse_args()

    terms, rx = vocabulary()
    print(f"vocabulary: {len(terms)} terms")
    people = {p["name"]: p for p in (load("people.json", {}) or {}).get("people", [])}

    if args.person:
        targets = [args.person]
    elif args.all:
        skip = {x.strip() for x in args.skip_confidence.split(",") if x.strip()}
        targets = [n for n, p in people.items()
                   if p["works_total"] >= args.min_works and p["confidence"] not in skip]
    elif not args.names:
        sys.exit("pass --person NAME, --all or --names FILE")
    else:
        targets = []

    if args.names:
        extra = [l.strip() for l in open(args.names, encoding="utf-8") if l.strip()]
        seen = set(targets)
        targets = targets + [n for n in extra if not (n in seen or seen.add(n))]

    global PAUSE
    if args.workers > 1:
        PAUSE = max(0.2, 3.2 / args.workers)
    global YEARS
    YEARS = max(1.0, datetime.date.today().year + 1 - args.since)
    print(f"scanning {len(targets)} people for work since {args.since} "
          f"({YEARS:.0f}y window, depth x{max(1.0, YEARS/3.0):.2f}) "
          f"on {args.workers} workers\n")

    out, src, lock, done = {}, None, threading.Lock(), [0]

    def one(name):
        person = people.get(name)
        return name, scan(name, person, terms, rx, args.since,
                          args.top or depth_for(person, YEARS))

    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for name, (hits, source) in pool.map(one, targets):
            with lock:
                src = src or source
                if hits:
                    out[name] = hits
                done[0] += 1
                if args.person or done[0] % 50 == 0:
                    works = sum(len(v) for v in out.values())
                    print(f"  [{done[0]}/{len(targets)}] {len(out)} people, "
                          f"{works} works so far", flush=True)

    if not src:
        print("\n  NOTE: no citation source available (set OPENALEX_API_KEY or S2_API_KEY);"
              "\n        works are ranked by type, keyword strength and recency, and"
              "\n        citations are left null rather than guessed.", file=sys.stderr)
    total = sum(len(v) for v in out.values())
    print(f"\n{len(out)} people with keyword-matched work, {total} works total")
    save("keyword_works.json", {"since": args.since, "citation_source": src,
                                "people_scanned": len(targets), "works_total": total,
                                "people": out})


if __name__ == "__main__":
    main()
