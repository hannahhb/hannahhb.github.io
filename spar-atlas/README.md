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

Without a Geoapify key, geocoding is local: free text is matched against a bundled gazetteer of 2,585 cities
and 244 countries built from [GeoNames](https://www.geonames.org/) (CC BY 4.0), so
"Melbourne", "Melbourne, Australia" and "AU" all resolve, ambiguous names go to the larger
city, and a country on its own gets an approximate pin at the country's centre, labelled as
such. In offline mode, nothing is sent to a geocoding service. World outlines come from
[world-atlas](https://github.com/topojson/world-atlas) at 110m, decoded to plain GeoJSON.

Unmatched locations are counted and reported rather than silently dropped. The globe opens
facing wherever people actually are — a headcount-weighted average of the pins — so it never
presents an empty hemisphere.

Someone who submits the form more than once (to add a location, to fix a link) gets one entry
per project, with later non-empty answers overriding earlier ones. Resubmitting is the
supported way to correct yourself.

The form's Location question feeds this. Responses submitted before that question existed
have no location and simply do not appear on the globe — type one into their row in the sheet
to place them. The CSV reader picks up any column headed *location*, *city*, *country* or
*where*, so renaming the question will not break it.

### The live feed

`SHEET_CSV` in `index.html` points at the published responses sheet, so a sign-up appears after
submission and a page reload, once Google refreshes the published CSV — no commit, no script.

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

## Testing sign-ups safely

Run the offline regression tests with Node.js (no dependencies or network requests):

```sh
node --test tests/*.test.cjs
```

For browser review, run from this directory:

```sh
python3 scripts/preview_local.py --seed
```

Open http://127.0.0.1:8765 and select **Globe**, then **Lenoir, United States**.
The seed is a synthetic participant on the topology project. Open that project and use
**Add yourself** with a test name and `lenoir, nc`; the location preview should say
**Globe location: Lenoir, United States**. Continue opens a local mock form. Click
**Submit locally**, return to the atlas, reload, and select Globe to see the new entry.

The preview replaces the live spreadsheet, Google Form, committed roster and database
integration. It stores sign-ups only in server memory, which disappears when stopped.
The page still loads public rendering assets (D3/fonts); roster requests and form
submissions are restricted to the local server. Omit `--seed` for an empty roster.

The Lenoir regression previously resolved to New Caledonia because `NC` was interpreted
as an ISO country code and Lenoir was absent from the gazetteer. The supplemental city
centroid comes from [GeoNames 4475640](https://www.geonames.org/4475640/), CC BY 4.0,
verified in the GeoNames cities15000 export. City/state pairs now interpret US state
suffixes before country codes; a country code on its own remains a country lookup.
For an explicit non-US country, use its full name or a city/state/country address.
Unlisted cities with a recognized country receive an approximate country pin; the form
now shows that result before submission. State-level disambiguation between cities
with identical names remains outside the bundled gazetteer's capabilities.

## Optional Geoapify city search

1. Create a free project at https://myprojects.geoapify.com/ and copy its API key.
2. Set `apiKey` in `geocoding-config.js`. This is a browser-visible key; restrict its
   allowed origins/referrers to your deployment in the Geoapify dashboard. For local
   testing, allow the localhost origin you use as well.
3. Deploy `geocoder.js` and `geocoding-config.js` alongside `index.html`.

With a key, **Find city** searches Geoapify for city-level results. The user chooses
one; its city/state/country label is sent through the existing Google Form Location
field. No spreadsheet columns or form question IDs need to change. The atlas also
resolves existing public roster locations, so older free-text sign-ups benefit.
Country-only entries retain approximate offline pins. Equally ranked or low-confidence
city matches remain unplaced instead of choosing a result arbitrarily.

Only location text is sent to Geoapify, not participant names, emails or projects.
Lookups are serialized, coalesced for duplicate strings, and cached in the visitor's
browser for 30 days (up to 500 locations). Failures trigger a short cooldown and retain
the offline gazetteer as fallback. Different visitors have separate caches, so this
reduces usage but is not a site-wide quota guarantee. The free plan currently includes
3,000 credits/day; check current [pricing](https://www.geoapify.com/pricing/).
Provider and OpenStreetMap attribution is displayed in the interface.

### Isolated and live-provider testing

The mock preview runs the same client against a local Geoapify-shaped response for
Lenoir, with no real account or API requests:

```sh
python3 scripts/preview_local.py --seed --mock-geocoder --port 8766
```

For an actual API test, save a test key in a local file outside this repository and run:

```sh
python3 scripts/preview_local.py --seed --geoapify-key-file /absolute/path/to/key --port 8767
```

The latter contacts Geoapify for city lookups but still uses synthetic roster data and
local form submissions. It never reads or writes the production signup sheet. The test
key is injected by the local server; it does not modify the deployable configuration.
Hannah can set her own key in `geocoding-config.js` before publishing.

Validation completed: offline regression tests and browser testing with the mocked
provider, including selecting Lenoir's full label. A live-provider test requires a key.
