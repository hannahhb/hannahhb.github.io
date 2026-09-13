# SPAR Project Atlas

An interactive map of all **230 SPAR Fall 2026 projects**, clustered into **15 themes** and
**56 sub-clusters of 3–5** so you can see which projects are actually asking neighbouring
questions — plus a public directory of who is working on what.

**→ [hannahhb.github.io/spar-atlas](https://hannahhb.github.io/spar-atlas/)**

Source data: the project index published by [SPAR](https://sparai.org/projects/f26/index.txt)
(Kairos). Applications for the Fall 2026 round closed on 18 August 2026; the round runs
14 September – 14 December 2026. This is a map of the field, not an application tool.

## What's on the page

| | |
|---|---|
| **Web** | Force layout — every project pulls on its nearest neighbours, so themes visibly bleed into one another. Drag a circle to reshape it; double-click to release. |
| **Clusters** | The same data as nested circle packing. Better for reading the taxonomy, worse for seeing overlap. |
| **Who's here** | The directory, grouped by theme. Projects with people get a ring on the map. |

Circle size is hours/week. Lines are topic similarity. Filters cover hours, mentor
involvement and team size; the shortlist (★) is stored in your own browser only.

## Adding yourself to the directory

Open any project, hit **+ Add yourself**, fill in the form. It opens a pre-filled GitHub
issue — nothing is published until that issue is merged into `data/people.json` by hand.

Only put in what you're happy to have publicly readable: the file is in a public repo and
the page renders it to anyone who opens it. To be removed, open an issue saying so.

## How the clustering works

1. Fetch the project index (one plain-text entry per project).
2. Parse title, id, mentors, research areas, hours, team size, mentor involvement, summary, prerequisites.
3. Assign each project to one of 15 themes: the curated area tags score first, title/summary
   keywords second, with a hand-audited override table for the ~40 projects whose tags mislead
   (persona and character work, for instance, is scattered across four different area tags).
4. Split each theme into sub-clusters with agglomerative clustering over TF-IDF vectors,
   rebalanced until **every** cluster holds 3–5 projects.
5. Emit nodes plus similarity edges (mutual top-6 above 0.10, plus every intra-cluster pair).

The themes and the 56 cluster names are editorial; the similarity structure underneath them
is not. Reasonable people would draw some of these boundaries differently.

## Rebuilding

```bash
cd scripts
pip install scikit-learn numpy
python3 build_atlas.py            # writes ../data/spar-f26-atlas.json
```

`build_atlas.py` reproduces the shipped dataset exactly — 230/230 theme assignments,
230/230 sub-cluster assignments, 1052 edges. It caches `index.txt` on first run.

## Files

```
index.html                      the whole app, data inlined, D3 from cdnjs
data/spar-f26-atlas.json        nodes + edges + theme/cluster names
data/spar-f26-projects-raw.json the parsed index, before clustering
data/people.json                the public directory
scripts/build_atlas.py          the pipeline
scripts/theme_overrides.json    hand-audited theme reassignments, keyed by SPAR project id
scripts/subcluster_names.json   the 56 cluster labels
```

Project descriptions and mentor names belong to SPAR and the individual mentors.
