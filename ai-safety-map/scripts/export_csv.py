#!/usr/bin/env python3
"""Flatten people.json into a spreadsheet, top works as links.

    python3 export_csv.py            -> data/people.csv  (everything)
    python3 export_csv.py --high     -> only high-confidence rows
"""
import argparse, csv, os
from common import DATA, load

COLUMNS = ["name", "sector_label", "side", "institution", "institution_source",
           "safety_tenure", "leads_work", "works_total", "papers", "posts",
           "strong_works", "confidence", "citations", "post_score", "af_posts",
           "tier", "first_year", "last_year", "cluster_name", "topics",
           "sources", "openalex_id", "lw_slug"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--high", action="store_true", help="only high-confidence people")
    ap.add_argument("--out", default=os.path.join(DATA, "people.csv"))
    args = ap.parse_args()

    people = load("people.json", {}).get("people", [])
    if args.high:
        people = [p for p in people if p["confidence"] == "high"]

    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS + ["top_1", "top_1_url", "top_2", "top_2_url",
                              "top_3", "top_3_url", "recent_1", "recent_1_url"])
        for p in people:
            row = []
            for c in COLUMNS:
                v = p.get(c)
                row.append("; ".join(v) if isinstance(v, list) else ("" if v is None else v))
            for key, n in (("top_works", 3), ("recent_works", 1)):
                works = p.get(key) or []
                for i in range(n):
                    wk = works[i] if i < len(works) else {}
                    row += [wk.get("title", ""), wk.get("url", "")]
            w.writerow(row)

    print(f"wrote {args.out}  ({len(people)} rows, {os.path.getsize(args.out)//1024} KB)")





def works_csv(out_path=None):
    """One row per (person, work) - the link collection, flat."""
    import csv as _csv, os as _os
    from common import DATA as _DATA, load as _load
    data = _load("keyword_works.json", {})
    people = _load("people.json", {}).get("people", [])
    meta = {p["name"]: p for p in people}
    out_path = out_path or _os.path.join(_DATA, "keyword_works.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = _csv.writer(fh)
        w.writerow(["person", "sector", "side", "institution", "safety_tenure",
                    "rank", "kind", "date", "year", "title", "url", "citations",
                    "post_score", "keyword_hits", "strong_hits", "keywords"])
        for name, works in (data.get("people") or {}).items():
            p = meta.get(name, {})
            for i, wk in enumerate(works, 1):
                w.writerow([name, p.get("sector", ""), p.get("side", ""),
                            p.get("institution", ""), p.get("safety_tenure", ""),
                            i, wk["kind"], wk.get("date", ""), wk.get("year", ""),
                            wk.get("title", ""), wk.get("url", ""),
                            wk.get("citations", ""), wk.get("score", ""),
                            wk.get("keyword_hits", 0), wk.get("strong_hits", 0),
                            "; ".join(wk.get("keywords", []))])
    print(f"wrote {out_path}  ({sum(len(v) for v in (data.get('people') or {}).values())} rows)")


if __name__ == "__main__":
    import sys
    if "--works" in sys.argv:
        works_csv()
    else:
        main()
