#!/usr/bin/env python3
"""Assemble the impact view: works and people, placed by area, scaled by citations.

Citations are a single present-day snapshot, so the quarter axis is when a work
was PUBLISHED, not when its citations arrived. A 2023 paper therefore appears in
2023 already carrying its 2026 citation count. That is a real limitation and the
page says so; the alternative - reconstructing accrual from citing-paper dates -
is a multi-hour harvest.

Because older work has had longer to accumulate, every work also carries
cites_per_year, so recent work can be compared on rate rather than total.

    python3 build_impact.py   ->  data/impact.json
"""
import datetime, json, math
from collections import Counter, defaultdict
from common import load, save
from taxonomy import TAXONOMY

NOW = datetime.date.today()
NOW_Q = (NOW.year, (NOW.month - 1) // 3 + 1)
START = (2021, 1)


def quarters():
    out, y, q = [], START[0], START[1]
    while (y, q) <= NOW_Q:
        out.append(f"{y}Q{q}")
        q += 1
        if q > 4:
            q, y = 1, y + 1
    return out


def qkey(date_str, year):
    if date_str and len(date_str) >= 7:
        y, m = int(date_str[:4]), int(date_str[5:7])
    elif year:
        y, m = int(year), 1
    else:
        return None
    return f"{y}Q{(m-1)//3+1}"


def layout(areas, edges, iters=600):
    """Spring layout for the areas, from their overlap weights.

    Computed here rather than in the browser so the ground plane is identical
    every time the page loads - a map whose landmarks move between visits is
    much harder to learn.
    """
    import random
    random.seed(7)
    n = len(areas)
    pos = [[math.cos(2*math.pi*i/n)*300, math.sin(2*math.pi*i/n)*300] for i in range(n)]
    adj = [[0.0]*n for _ in range(n)]
    for e in edges:
        adj[e["s"]][e["t"]] = adj[e["t"]][e["s"]] = e["w"]
    for step in range(iters):
        k = 1 - step/iters
        fx = [0.0]*n; fy = [0.0]*n
        for i in range(n):
            for j in range(n):
                if i == j: continue
                dx, dy = pos[i][0]-pos[j][0], pos[i][1]-pos[j][1]
                d = math.hypot(dx, dy) or 1
                rep = 42000/(d*d)                       # keep areas apart
                fx[i] += dx/d*rep; fy[i] += dy/d*rep
                if adj[i][j]:                            # overlap pulls together
                    att = (d-190)*adj[i][j]*0.035
                    fx[i] -= dx/d*att; fy[i] -= dy/d*att
            fx[i] -= pos[i][0]*0.0022; fy[i] -= pos[i][1]*0.0022   # gentle centring
        for i in range(n):
            pos[i][0] += max(-18, min(18, fx[i]))*k
            pos[i][1] += max(-18, min(18, fy[i]))*k
    mx = max(max(abs(p[0]), abs(p[1])) for p in pos) or 1
    return [[round(p[0]/mx*420, 1), round(p[1]/mx*420, 1)] for p in pos]


def main():
    wa = load("work_areas.json", {}) or {}
    works_meta = wa.get("works", {})
    kw = (load("keyword_works.json", {}) or {}).get("people", {})
    m2 = load("map2.json", {}) or {}
    people_meta = {p["n"]: p for p in m2.get("people", [])}
    areas = [a["name"] for a in m2.get("areas", [])]

    # work -> authors, and the publication date we actually have
    authors, dates = defaultdict(list), {}
    for person, ws in kw.items():
        for w in ws:
            key = w.get("arxiv_id", "").split("v")[0].lower() or w.get("url")
            if not key:
                continue
            authors[key].append(person)
            if w.get("date"):
                dates[key] = w["date"]

    QS = quarters()
    qidx = {q: i for i, q in enumerate(QS)}

    out_works = []
    for key, rec in works_meta.items():
        q = qkey(dates.get(key), rec.get("year"))
        if q not in qidx:
            continue                       # before START, or undated
        cites = rec.get("cites")
        yrs = max(0.35, (NOW.year + NOW.month / 12) - (int(q[:4]) + (int(q[-1]) - 1) * 0.25))
        out_works.append({
            "t": rec["title"][:150], "u": rec.get("url"), "k": rec.get("kind"),
            "q": qidx[q], "c": cites if cites is not None else None,
            "cpy": round(cites / yrs, 1) if cites else None,
            "a": rec["areas"][:3],
            "au": authors.get(key, [])[:6],
        })
    out_works.sort(key=lambda w: -(w["c"] or 0))

    # people: impact totals and where their work sits
    out_people = []
    for name, p in people_meta.items():
        mine = [w for w in out_works if name in w["au"]]
        if not mine:
            continue
        tot = sum(w["c"] or 0 for w in mine)
        out_people.append({
            "n": name, "org": p.get("org", ""), "osrc": p.get("osrc", ""),
            "sec": p.get("sec", "unknown"), "h": p.get("h"),
            "c": tot, "nw": len(mine),
            "cpy": round(sum(w["cpy"] or 0 for w in mine), 1),
            "a": p.get("a", []),
            "q": min(w["q"] for w in mine),
            "top": [{"t": w["t"], "u": w["u"], "c": w["c"], "q": w["q"]}
                    for w in sorted(mine, key=lambda w: -(w["c"] or 0))[:5]],
        })
    out_people.sort(key=lambda p: -p["c"])

    # area totals per quarter (cumulative, since a work stays once published)
    per_area_q = {a: [0.0] * len(QS) for a in areas}
    cnt_area_q = {a: [0] * len(QS) for a in areas}
    for w in out_works:
        for m in w["a"]:
            if m["a"] in per_area_q:
                per_area_q[m["a"]][w["q"]] += (w["c"] or 0) * m["w"]
                cnt_area_q[m["a"]][w["q"]] += 1
    for a in areas:
        for i in range(1, len(QS)):
            per_area_q[a][i] += per_area_q[a][i - 1]
            cnt_area_q[a][i] += cnt_area_q[a][i - 1]

    print(f"{len(out_works)} works since 2023Q1 across {len(QS)} quarters")
    print(f"{len(out_people)} people with attributable work")
    cited = [w for w in out_works if w["c"]]
    print(f"works with citations: {len(cited)}  max {max(w['c'] for w in cited)}")
    print("\ncitation mass by area (to date):")
    for a in sorted(areas, key=lambda a: -per_area_q[a][-1])[:8]:
        print(f"  {per_area_q[a][-1]:>10,.0f}  {cnt_area_q[a][-1]:>5} works  {a}")

    pos = layout(areas, m2.get("edges", []))
    print("\narea layout computed")
    save("impact.json", {
        "quarters": QS,
        "areas": [{"name": a["name"], "blurb": a["blurb"],
                   "x": pos[i][0], "y": pos[i][1],
                   "mass": [round(v,1) for v in per_area_q[a["name"]]],
                   "count": cnt_area_q[a["name"]]}
                  for i, a in enumerate(m2.get("areas", []))],
        "edges": m2.get("edges", []),
        "works": out_works[:6000],
        "people": out_people,
    })


if __name__ == "__main__":
    main()
