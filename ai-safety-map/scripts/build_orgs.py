#!/usr/bin/env python3
"""Build the org registry from the two published AI-safety org spreadsheets.

Rather than hand-maintaining patterns, the registry is the field's own census:
the technical-org sheet and the governance-org sheet from the 2025 field-growth
analysis. Each org gets a sector; a handful of overrides cover the cases the
sheets cannot know (frontier labs, government bodies, university groups).

    python3 build_orgs.py   ->  data/orgs.json
"""
import csv, io, re
from common import get, save

SHEETS = {
    "technical":  "1mshx9kgOC-DKEGridtyc81iI8omu2TCmMCHmN2VVeug",
    "governance": "1KAVuMlHabNqwe-F_9NSKmuCRB26mrFAQ_2A6LPYBP_A",
}
CSV = "https://docs.google.com/spreadsheets/d/{}/gviz/tq?tqx=out:csv&gid=0"

# Orgs whose sector the sheets cannot tell us, because being an AI-safety org
# in the census says nothing about who employs the people doing the work.
FRONTIER = (r"^(Anthropic|OpenAI|Google ?DeepMind|DeepMind|Meta|xAI|Microsoft|Mistral|"
            r"Cohere|NVIDIA|Amazon|Apple|ByteDance|Alibaba|Baidu|Tencent|Huawei)\b")
GOVERNMENT = (r"AI Security Institute|AI Safety Institute|European AI Office|"
              r"Beijing Institute of AI Safety|China AI Safety|ARIA")
# Sheet rows that are a researcher or a university lab, not an organisation
ACADEMIC = (r"research group|Group$|\((University|Cambridge|MIT|Oxford|Stanford|Berkeley|"
            r"Peking|NYU|University of [^)]+)\)|^(Dawn Song|Roman Yampolskiy|Vincent Conitzer|"
            r"Stephen Byrnes|Sharon Li|Yaodong Yang|David Krueger|Jacob Steinhardt|"
            r"David Bau|Tegmark|Scott Niekum)")
ADVOCACY_CATS = {"governance", "advocacy", "watchdog", "whistleblower support", "forecasting"}


def sector_for(name, category, source):
    if re.search(FRONTIER, name, re.I):
        return "frontier_lab"
    if re.search(GOVERNMENT, name, re.I):
        return "government"
    if re.search(ACADEMIC, name, re.I):
        return "academia"
    if source == "governance" and (category or "").strip().lower() in ADVOCACY_CATS:
        return "policy_org"
    return "safety_org"


def aliases(name):
    """Name plus anything in brackets, so 'CSET' matches as well as the full title."""
    out = {name.strip()}
    for m in re.findall(r"\(([^)]+)\)", name):
        m = m.strip()
        if 2 <= len(m) <= 40 and not m.lower().startswith(("university of",)):
            out.add(m)
    bare = re.sub(r"\s*\([^)]*\)", "", name).strip()
    if bare:
        out.add(bare)
    return sorted(a for a in out if len(a) >= 3)


def main():
    orgs, seen = [], set()
    for source, sid in SHEETS.items():
        body = get(CSV.format(sid), cache=False)
        rows = list(csv.DictReader(io.StringIO(body)))
        kept = 0
        for r in rows:
            name = (r.get("Name") or "").strip()
            if not name or name.isdigit():          # the sheets' total rows
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                ftes = int(re.sub(r"\D", "", r.get("FTEs") or "") or 0)
            except ValueError:
                ftes = 0
            orgs.append({
                "name": name,
                "aliases": aliases(name),
                "source_sheet": source,
                "category": (r.get("Category") or "").strip(),
                "founded": (r.get("Founded") or "").strip(),
                "closed": (r.get("Year of Closure") or "").strip(),
                "ftes": ftes,
                "link": (r.get("Link") or "").strip(),
                "sector": sector_for(name, r.get("Category"), source),
            })
            kept += 1
        print(f"  {source:<12} {len(rows):>4} rows -> {kept:>4} orgs")

    from collections import Counter
    print(f"\n{len(orgs)} orgs total")
    for k, v in Counter(o["sector"] for o in orgs).most_common():
        print(f"  {v:>4}  {k}")
    print(f"  {sum(o['ftes'] for o in orgs):>4}  FTEs counted across the field")
    save("orgs.json", orgs)


if __name__ == "__main__":
    main()
