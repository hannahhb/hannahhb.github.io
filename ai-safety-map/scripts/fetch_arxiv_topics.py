#!/usr/bin/env python3
"""Harvest arXiv by topic, to reach work the author-based pass never saw.

The earlier arXiv harvest searched per person, so it could only find papers by
people already in the dataset. This searches the vocabulary itself - including
the workshop phrasing that conference-and-workshop papers carry in their
comments - and picks up whoever wrote them.

    python3 fetch_arxiv_topics.py   ->  data/arxiv_topics.json
"""
import re, sys, time, urllib.parse
from common import get, save

API = "https://export.arxiv.org/api/query"
PAUSE = 3.2          # arXiv asks for one request every three seconds

QUERIES = [
  'abs:"mechanistic interpretability"', 'abs:"sparse autoencoder" AND abs:"language model"',
  'abs:"activation patching"', 'abs:"activation steering"', 'abs:"circuit discovery"',
  'abs:"linear probe" AND abs:"language model"', 'abs:"crosscoder" OR abs:"transcoder"',
  'abs:"chain-of-thought" AND abs:"faithfulness"', 'abs:"chain of thought monitoring"',
  'abs:"deceptive alignment"', 'abs:"alignment faking"', 'abs:"emergent misalignment"',
  'abs:"reward hacking"', 'abs:"specification gaming"', 'abs:"goal misgeneralization"',
  'abs:"scalable oversight"', 'abs:"weak-to-strong generalization"', 'abs:"AI control"',
  'abs:"untrusted monitoring"', 'abs:"dangerous capability" AND abs:evaluation',
  'abs:"situational awareness" AND abs:"language model"', 'abs:"evaluation awareness"',
  'abs:"sandbagging"', 'abs:"sycophancy"', 'abs:"model organism" AND abs:misalignment',
  'abs:"jailbreak" AND abs:"language model"', 'abs:"prompt injection"',
  'abs:"machine unlearning" AND abs:safety', 'abs:"constitutional AI"',
  'abs:"AI safety" AND abs:"frontier model"', 'abs:"safety case" AND abs:"AI system"',
  'abs:"interpretability" AND abs:"transformer"', 'abs:"refusal" AND abs:"language model"',
  'abs:"steering vector"', 'abs:"secret knowledge" OR abs:"eliciting latent knowledge"',
  'co:"Mechanistic Interpretability Workshop"', 'co:"NeurIPS 2025"', 'co:"ICLR 2026"',
  'co:"ICML 2025 Workshop"', 'co:"SoLaR"',
]
ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)


def field(e, t):
    m = re.search(rf"<{t}>(.*?)</{t}>", e, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def main():
    out, seen = {}, set()
    for qi, q in enumerate(QUERIES, 1):
        got = 0
        for start in (0, 200, 400):
            url = (f"{API}?search_query={urllib.parse.quote(q)}&start={start}"
                   f"&max_results=200&sortBy=submittedDate&sortOrder=descending")
            try:
                xml = get(url, pause=PAUSE)
            except Exception as e:
                print(f"    ! {q[:40]}: {e}", file=sys.stderr)
                break
            entries = ENTRY.findall(xml)
            if not entries:
                break
            for e in entries:
                m = re.search(r"<id>http://arxiv\.org/abs/([^<]+)</id>", e)
                if not m:
                    continue
                aid = m.group(1).split("v")[0]
                if aid in seen:
                    continue
                seen.add(aid)
                pub = field(e, "published")[:10]
                if not pub or int(pub[:4]) < 2023:
                    continue
                out[aid] = {
                    "arxiv_id": aid, "title": field(e, "title"),
                    "abstract": field(e, "summary")[:2500], "date": pub,
                    "year": int(pub[:4]), "comment": field(e, "arxiv:comment"),
                    "authors": re.findall(r"<name>(.*?)</name>", e),
                    "url": f"https://arxiv.org/abs/{aid}",
                }
                got += 1
            if len(entries) < 200:
                break
        print(f"  [{qi}/{len(QUERIES)}] {q[:46]:<48} +{got:<4} total {len(out)}", flush=True)

    print(f"\n{len(out)} distinct arXiv papers since 2023")
    save("arxiv_topics.json", out)


if __name__ == "__main__":
    main()
