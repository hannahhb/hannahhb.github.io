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

Open any project, hit **+ Add yourself**, type your name, LinkedIn and email. That opens the
[Spar Atlas Sign Up](https://docs.google.com/forms/d/15baGmkFSmcKcHd6oYEKDjMqEF-dW8sgXdv90WF8rR2U/viewform)
form with every field — including which project — already filled in. One click to submit.
No GitHub account needed.

**Your name and LinkedIn are published; your email is not.** It stays in the responses sheet.

### The globe

**Globe** places anyone who gave a location on an orthographic world map — drag to spin,
click a pin for who is there and what they work on.

Geocoding is entirely local: free text is matched against a bundled gazetteer of 2,585 cities
and 244 countries built from [GeoNames](https://www.geonames.org/) (CC BY 4.0), so
"Melbourne", "Melbourne, Australia" and "AU" all resolve, ambiguous names go to the larger
city, and a country on its own gets an approximate pin at the country's centre, labelled as
such. Nothing is sent to a geocoding service. World outlines come from
[world-atlas](https://github.com/topojson/world-atlas) at 110m, decoded to plain GeoJSON.

Unmatched locations are counted and reported rather than silently dropped.

**The form needs a Location question for any of this to fill up.** Add one, then paste its
`entry.` id into `GFORM.fields.location` in `index.html`. Until that id is set the sign-up
form does not ask for a location, and the globe stays empty. The CSV reader picks up any
column headed *location*, *city*, *country* or *where* automatically.

### The live feed

`SHEET_CSV` in `index.html` points at the published responses sheet, so a sign-up appears on
the site the moment anyone reloads — no commit, no script.

The responses sheet is **published openly**, which means the email column is fetchable by
anyone who has that CSV URL, and the URL is in this page's source. The sign-up form says so
in as many words. The page itself drops any column whose header mentions *email* or
*timestamp* before parsing, so addresses never render on the map — but that is presentation,
not privacy.

To narrow it later: stop publishing, add a `Public` tab holding
`=QUERY('Form Responses 1'!A:E, "select B, C, E where B is not null", 1)`, publish only that
tab as CSV, and swap the URL in `SHEET_CSV`.

Rows naming no known project are skipped. If the sheet is ever unreachable, the committed
`people.json` still renders. Live means unmoderated — to take someone down, delete their row.

### Merging responses by hand

If you would rather curate, leave `SHEET_CSV` empty and merge from a CSV export instead:

```bash
# Sheet: File -> Download -> Comma-separated values
cd scripts
python3 merge_signups.py ~/Downloads/responses.csv --dry-run   # check first
python3 merge_signups.py ~/Downloads/responses.csv
git add ../data/people.json && git commit -m "Directory: new sign-ups" && git push
```

It matches each free-text project name back to a SPAR project id (exact, then fuzzy), skips
anyone already listed, and never writes the email column.

To remove someone, delete their object from `data/people.json` and push.

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
