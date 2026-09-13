#!/usr/bin/env python3
"""Merge Google Form sign-ups into the public directory.

Export the "Spar Atlas Sign Up" responses as CSV (in the linked Sheet:
File -> Download -> Comma-separated values), then:

    python3 merge_signups.py ~/Downloads/responses.csv

Matches each row's free-text "Project Name" back to a SPAR project id,
skips rows already present, and never writes the email column to the
public file. Prints anything it could not match so you can fix it by hand.

    --dry-run   show what would change, write nothing
"""
import argparse, csv, difflib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.join(HERE, "..", "data", "spar-f26-atlas.json")
PEOPLE = os.path.join(HERE, "..", "data", "people.json")

# CSV header -> field. Add a line here if you add a question to the form.
COLUMNS = {
    "full name": "name",
    "linkedin profile url": "linkedin",
    "project name": "project",
    "role": "role",
    "one line": "note",
    "another link": "link",
}
NEVER_PUBLISH = {"email address", "email", "timestamp"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", str(s or "").lower()).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    atlas = json.load(open(ATLAS, encoding="utf-8"))
    titles = {norm(p["title"]): p["id"] for p in atlas["projects"]}
    by_id = {p["id"]: p["title"] for p in atlas["projects"]}

    people = json.load(open(PEOPLE, encoding="utf-8"))
    entries = people.get("entries", [])
    seen = {(e.get("projectId"), norm(e.get("name"))) for e in entries}

    added, skipped, unmatched = 0, 0, []
    with open(args.csv, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            rec = {}
            for header, value in row.items():
                key = norm(header)
                if key in NEVER_PUBLISH or not value:
                    continue
                field = COLUMNS.get(key)
                if field:
                    rec[field] = value.strip()
            name, project = rec.pop("name", ""), rec.pop("project", "")
            if not name or not project:
                continue

            pid = titles.get(norm(project))
            if not pid:
                near = difflib.get_close_matches(norm(project), titles.keys(), n=1, cutoff=0.72)
                pid = titles[near[0]] if near else None
            if not pid:
                unmatched.append((name, project))
                continue
            if (pid, norm(name)) in seen:
                skipped += 1
                continue

            rec.update(projectId=pid, name=name, createdAt=int(time.time() * 1000))
            entries.append(rec)
            seen.add((pid, norm(name)))
            added += 1
            print(f"  + {name} -> {by_id[pid]}")

    print(f"\n{added} added, {skipped} already listed, {len(unmatched)} unmatched")
    for name, project in unmatched:
        print(f"  ? {name}: could not match project {project!r}", file=sys.stderr)

    if args.dry_run:
        print("(dry run: nothing written)")
        return
    if added:
        people["entries"] = entries
        json.dump(people, open(PEOPLE, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"wrote {os.path.relpath(PEOPLE, HERE)} — commit and push to publish")


if __name__ == "__main__":
    main()
