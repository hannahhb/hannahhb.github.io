# AI Safety Field Map

Who is publishing in AI safety, how much, on what, and from inside which kind of
organisation. Built from public research output — not from scraped profiles.

**→ [hannahhb.github.io/ai-safety-map](https://hannahhb.github.io/ai-safety-map/)**

## What counts as a person in this dataset

Someone with **at least two public AI-safety works**. Papers, preprints and
Alignment Forum / LessWrong posts all count, because a great deal of real safety
work is published as posts and never sees a venue — a dataset that counted only
papers would systematically miss the people closest to the field's centre.

Everyone carries their **three strongest works** (most cited for papers, most
upvoted for posts) and their **three most recent**, as links.

## Sources

| Source | What it gives | Access |
|---|---|---|
| [OpenAlex](https://openalex.org) | papers, citations, topics, institutions | open API, CC0 |
| [LessWrong / Alignment Forum](https://www.lesswrong.com) | posts, karma, tags, coauthors | public GraphQL API |
| [Field-growth org list](https://www.lesswrong.com/posts/8QjAnWyuE9fktPRgS/ai-safety-field-growth-analysis-2025) | org names, founding years, headcount, category | published spreadsheet |

### On LinkedIn

LinkedIn is deliberately **not** a source. Scraping it breaches their terms, most
profile data sits behind authentication, and — the part that actually matters — it
holds job titles, not publications, citations or topics. Every axis this dataset
clusters on comes from research output, which the sources above expose properly.
Affiliation comes from the institutions on people's own papers.

## How people are placed

**Sector** is about who signs the cheque, not what the team works on. A safety
researcher at a frontier lab is still inside a frontier lab, and that is the
distinction that makes the comparison worth drawing:

- `frontier_lab` — Anthropic, OpenAI, Google DeepMind, Meta, Microsoft, xAI …
- `safety_org` — MIRI, Redwood, ARC, Apollo, METR, FAR AI, Timaeus, Goodfire, MATS …
- `government` — UK AISI, NIST/CAISI, national labs, EU AI Office …
- `policy_org` — GovAI, RAND, CSET, Epoch AI, FLI …
- `academia` — universities and university groups
- `unknown` — no institution on any indexed work

Where someone has several affiliations, a frontier lab wins, then a safety org,
then government, then policy, then academia.

**Career stage** is inferred from authorship position and publishing span:
last-author position is the strongest available signal of running a group.
Anyone who can't be placed confidently lands in `mid` rather than being pushed
into one of the two categories being compared.

**Topic clusters** come from TF-IDF over each person's top works — titles,
venues and OpenAlex topic labels — then agglomerative clustering, with each
cluster named after the topics its members actually share.

## Rebuilding

```bash
cd scripts
pip install scikit-learn numpy
python3 fetch_lesswrong.py      # -> data/lesswrong_authors.json
python3 fetch_openalex.py       # -> data/openalex_authors.json, openalex_works.json
python3 build_dataset.py        # -> data/people.json
```

Responses are cached under `scripts/.cache`, so re-runs are cheap and the
harvesters can be interrupted and resumed. Delete the cache to refresh.

## Current state, honestly

The infrastructure is finished and reproducible. The data is not finished, and
the gap is worth stating plainly before anyone builds on it.

**Solid.** The 967 people sourced from LessWrong / the Alignment Forum are AI
safety researchers by construction — there is no way for an orthopaedic surgeon
to end up in that set. The org registry covers 115/115 orgs from both census
sheets. Affiliations read from people's own profile bios are current and
self-reported, which beats a stale affiliation printed on a five-year-old paper.

**Not solid.** People sourced from OpenAlex full-text search carry a noisy tail.
Roughly a third of them still cluster under labels like *Medicine, Real-World*
or *Neuropsychology* — applied-AI papers that borrow safety vocabulary. Four
rounds of filtering cut the harvest from 4,319 works to 2,441 and removed the
worst of it (knee arthroplasty, genomics, astrophysics), but search-based recall
has a precision ceiling that regex cannot fix.

**The real fix**, blocked on an OpenAlex API key: stop discovering people by
full-text search and seed instead from the 115 registry orgs and from the
citation graph around canonical safety papers. That is a precision-first design
rather than a recall-first one, and it needs the author and institution
endpoints.

Until then, filter on `confidence` and `strong_works` rather than treating every
row as equally real.

## Known limits

Worth stating plainly, because they shape what the map can and cannot show:

- **Pseudonymous writers don't merge.** Someone posting as a handle on LessWrong
  and publishing under their legal name appears twice, or only once. Matching is
  by name, and there is no honest way around that without guessing at identities.
- **Coverage of non-academic labs is uneven.** OpenAlex indexes institutions as
  they appear on papers; researchers at labs that publish little, or publish
  without affiliations, are under-represented.
- **Citation counts favour older work**, so "most cited" skews senior. The
  recency list is there as the counterweight.
- **Topic clusters are editorial.** The similarity structure underneath them is
  not, but where the boundaries fall is a judgement call.
- **Search-based recall is not exhaustive.** The harvest finds work matching a
  fixed set of AI-safety queries; work phrased unusually will be missed.

Data about named people is included only where they published it themselves.
