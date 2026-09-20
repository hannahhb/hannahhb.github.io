#!/usr/bin/env python3
"""Recover abstracts from the response cache - no network needed.

Titles alone are too thin to place a paper in a research area: "Thought
Anchors" says nothing without its abstract. Every arXiv and OpenAlex response
we ever fetched is on disk, so the abstracts are already here.

    python3 extract_abstracts.py   ->  data/abstracts.json
"""
import glob, json, os, re
from common import CACHE, save

ARXIV_ID = re.compile(r"<id>http://arxiv\.org/abs/([^<]+)</id>")
FIELD = re.compile(r"<(title|summary)>(.*?)</\1>", re.S)


def clean(t):
    return re.sub(r"\s+", " ", t).strip()


def unabstract(inv):
    if not inv:
        return ""
    out = []
    for word, spots in inv.items():
        for s in spots:
            out.append((s, word))
    return " ".join(w for _, w in sorted(out))


def main():
    out, files = {}, sorted(glob.glob(os.path.join(CACHE, "*.json")))
    arx = oa = 0
    for i, f in enumerate(files):
        try:
            body = json.load(open(f, encoding="utf-8")).get("body", "")
        except Exception:
            continue

        if "<entry>" in body:
            for entry in re.findall(r"<entry>(.*?)</entry>", body, re.S):
                m = ARXIV_ID.search(entry)
                if not m:
                    continue
                aid = m.group(1).split("v")[0].lower()
                fields = dict((k, clean(v)) for k, v in FIELD.findall(entry))
                if fields.get("summary"):
                    out.setdefault(aid, {"id": aid, "title": fields.get("title", ""),
                                         "abstract": fields["summary"][:2500], "src": "arxiv"})
                    arx += 1
        elif '"abstract_inverted_index"' in body:
            try:
                data = json.loads(body)
            except Exception:
                continue
            for w in data.get("results", []) or []:
                ab = unabstract(w.get("abstract_inverted_index"))
                if not ab:
                    continue
                doi = (w.get("doi") or "").lower()
                key = doi.replace("https://doi.org/10.48550/arxiv.", "") if "arxiv" in doi else (w.get("id") or "")
                if key:
                    out.setdefault(key, {"id": key, "title": w.get("display_name") or "",
                                         "abstract": ab[:2500], "src": "openalex"})
                    oa += 1
        if (i + 1) % 400 == 0:
            print(f"  {i+1}/{len(files)} cache files, {len(out)} abstracts", flush=True)

    print(f"\n{len(out)} distinct abstracts ({arx} arXiv hits, {oa} OpenAlex hits)")
    lens = sorted(len(v["abstract"]) for v in out.values())
    print(f"length: median {lens[len(lens)//2]}, p90 {lens[int(len(lens)*.9)]}")
    save("abstracts.json", out)


if __name__ == "__main__":
    main()
