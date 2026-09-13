#!/usr/bin/env python3
"""Rebuild the SPAR Project Atlas dataset from sparai.org.

Pipeline
--------
1. Fetch the Fall 2026 project index (one plain-text entry per project).
2. Parse title / id / mentors / areas / hours / team size / involvement /
   summary / prerequisites.
3. Assign each project to one of 15 themes, scoring the curated area tags
   first and title/summary keywords second, with a hand-audited override
   table for the ~40 projects whose tags mislead.
4. Split each theme into sub-clusters of 3-5 with agglomerative clustering
   over TF-IDF vectors, rebalanced until every cluster lands in range.
5. Emit nodes + similarity edges as data/spar-f26-atlas.json.

Usage:  python3 build_atlas.py [--out ../data/spar-f26-atlas.json]
Requires: scikit-learn, numpy
"""
import argparse, json, math, os, re, sys, urllib.request
from collections import defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer

INDEX_URL = "https://sparai.org/projects/f26/index.txt"
HERE = os.path.dirname(os.path.abspath(__file__))

GROUP_NAMES = {
    "INTERP_CIRCUITS": "Interpretability — Circuits & Representations",
    "INTERP_PROBES":   "Interpretability — Probes & Deception Detection",
    "COT":             "Chain of Thought — Faithfulness & Monitorability",
    "PERSONA":         "Personas, Character & Self-Models",
    "ALIGN_TRAIN":     "Alignment — Training Dynamics & Generalization",
    "EVALS":           "Evaluation Science & Eval Awareness",
    "CONTROL":         "AI Control & Scalable Oversight",
    "MULTIAGENT":      "Multi-Agent Systems & Coordination",
    "SECURITY":        "AI Security, Misuse & Cyber",
    "BIO":             "Biosecurity & Bio-AI",
    "WELFARE":         "AI Welfare, Consciousness & Philosophy",
    "GOV_COMPUTE":     "Compute Governance & Geopolitics",
    "GOV_POLICY":      "Policy, Law & Institutions",
    "SOCIETAL":        "Societal, Economic & Epistemic Impacts",
    "FIELD":           "Field-building, Comms & Meta-Research",
}

# curated area tag -> theme weights
AREA_WEIGHTS = {
    "Mechanistic interpretability": {"INTERP_CIRCUITS": 3, "INTERP_PROBES": 3},
    "Developmental interpretability": {"INTERP_CIRCUITS": 6},
    "Chain of thought": {"COT": 7},
    "Alignment": {"ALIGN_TRAIN": 3},
    "Behavioral evaluation of LLMs": {"EVALS": 2, "PERSONA": 1.5},
    "Evaluations": {"EVALS": 3},
    "AI control": {"CONTROL": 3.5},
    "Scalable oversight": {"CONTROL": 3.5},
    "Multi-agent systems": {"MULTIAGENT": 5},
    "AI security": {"SECURITY": 5},
    "Cyber risks": {"SECURITY": 5},
    "Misuse risk": {"SECURITY": 3},
    "Biosecurity": {"BIO": 8},
    "AI welfare": {"WELFARE": 5},
    "Philosophy of AI": {"WELFARE": 3.5},
    "Compute governance": {"GOV_COMPUTE": 6},
    "US-China governance": {"GOV_COMPUTE": 6},
    "International governance": {"GOV_COMPUTE": 3, "GOV_POLICY": 3},
    "Technical governance": {"GOV_POLICY": 3},
    "National policy": {"GOV_POLICY": 5},
    "US policy": {"GOV_POLICY": 5},
    "EU policy": {"GOV_POLICY": 5},
    "Lab governance": {"GOV_POLICY": 4},
    "Societal impacts": {"SOCIETAL": 4},
    "Economics of AI": {"SOCIETAL": 6},
    "Generalist": {"FIELD": 5},
    "Communications": {"FIELD": 6},
    "AI strategy": {"GOV_POLICY": 1.5, "SOCIETAL": 1.0},
    "Other": {"FIELD": 1},
}

KEYWORDS = {
    "INTERP_CIRCUITS": r"circuit|attention head|feature geometr|representation|linear|superposition|SAE|sparse autoencoder|model diffing|binding|activation space|geometr|manifold|topolog|neuron",
    "INTERP_PROBES":   r"probe|monitor|detect|classifier|steer|lie detect|deception",
    "COT":             r"chain.of.thought|chain of thought|\bCoT\b|reasoning trace|verbaliz|introspect|faithful",
    "ALIGN_TRAIN":     r"generali[sz]|fine.?tun|RL\b|reinforcement|post.?train|mid.?train|reward|training|distill|emergent misalign|model organism|unlearn",
    "PERSONA":         r"persona|character|identity|self.aware|introspect|emotion|preference",
    "EVALS":           r"benchmark|eval|sandbag|evaluation aware|metagam",
    "CONTROL":         r"control protocol|oversight|debate|untrusted|auditing|sabotage|monitor",
    "MULTIAGENT":      r"multi.?agent|collusion|coordinat|negotiat|game theor|agents",
    "SECURITY":        r"jailbreak|prompt injection|attack|adversarial|vulnerab|cyber|malicious|red.?team|tamper",
    "BIO":             r"bio|protein|genom|pathogen|pandemic",
    "WELFARE":         r"welfare|consciousness|moral|sentien|suffering|animal",
    "GOV_COMPUTE":     r"compute|chip|GPU|semiconductor|export|China|Taiwan|datacenter|hardware",
    "GOV_POLICY":      r"polic|law|legal|regulat|congress|governance|treaty|standard|compliance|institut",
    "SOCIETAL":        r"econom|labor|inequal|epistemic|manipulat|persuas|autonomy|democra|public|societ",
    "FIELD":           r"fieldbuild|community|curricul|university|outreach|newsletter|wiki|textbook|career|hiring|networking|comms|communicat",
}


def load_json(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        return json.load(fh)


def fetch_index(cache):
    if cache and os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    req = urllib.request.Request(INDEX_URL, headers={"User-Agent": "spar-atlas-build/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        txt = r.read().decode("utf-8")
    if cache:
        open(cache, "w", encoding="utf-8").write(txt)
    return txt


def parse(txt):
    out = []
    for block in txt.split("\n## ")[1:]:
        lines = block.split("\n")
        body = "\n".join(lines[1:])
        p = {"title": lines[0].strip()}
        m = re.search(r"^id: (\S+)", body, re.M)
        p["id"] = m.group(1) if m else None
        m = re.search(r"^Mentors: (.+)$", body, re.M)
        parts = [x.strip() for x in (m.group(1) if m else "").split(" · ")]
        p["mentors"] = parts[0] if parts else ""
        p["areas"] = []
        for part in parts[1:]:
            if part.startswith("Areas:"):
                p["areas"] = [a.strip() for a in part[6:].split(",")]
            elif "hrs/week" in part:
                p["hours"] = part
            elif part.startswith("Team size"):
                p["team"] = part
            elif part.startswith("Mentor involvement: "):
                p["involvement"] = part[len("Mentor involvement: "):]
        m = re.search(r"^Summary: (.+?)(?=\nMust-have prerequisites:|\Z)", body, re.M | re.S)
        p["summary"] = m.group(1).strip() if m else ""
        m = re.search(r"^Must-have prerequisites: (.+)$", body, re.M | re.S)
        p["prereq"] = m.group(1).strip() if m else ""
        out.append(p)
    return out


def assign_theme(p, overrides):
    if p["id"] in overrides:
        return overrides[p["id"]]
    score = {g: 0.0 for g in GROUP_NAMES}
    for area in p["areas"]:
        for g, w in AREA_WEIGHTS.get(area, {}).items():
            score[g] += w
    blob = p["title"] + " " + p["summary"]
    for g, pat in KEYWORDS.items():
        score[g] += min(len(re.findall(pat, blob, re.I)), 4) * 0.55
    return max(score, key=score.get)


def vectors(projects):
    docs = [(p["title"] + " . ") * 3 + " ".join(p["areas"]) * 4 + " " + p["summary"] for p in projects]
    X = TfidfVectorizer(stop_words="english", max_features=6000,
                        ngram_range=(1, 2), sublinear_tf=True, min_df=2).fit_transform(docs).toarray()
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def balanced_subclusters(Xg, lo=3, hi=5):
    """Agglomerative split, then move members until every cluster is 3-5."""
    n = len(Xg)
    k = max(1, round(n / 4.0))
    while math.ceil(n / k) > hi:
        k += 1
    while n / k < lo and k > 1:
        k -= 1
    if k == 1:
        return [0] * n
    lab = AgglomerativeClustering(n_clusters=k, metric="cosine",
                                  linkage="average").fit(Xg).labels_.tolist()
    for _ in range(300):
        size = [lab.count(c) for c in range(k)]
        cen = np.array([Xg[[j for j in range(n) if lab[j] == c]].mean(0)
                        if size[c] else np.zeros(Xg.shape[1]) for c in range(k)])
        cen /= (np.linalg.norm(cen, axis=1, keepdims=True) + 1e-9)
        big = [c for c in range(k) if size[c] > hi]
        small = [c for c in range(k) if size[c] < lo]
        if not big and not small:
            break
        if big:
            c = big[0]
            members = [j for j in range(n) if lab[j] == c]
            targets = [t for t in range(k) if size[t] < hi and t != c]
            if not targets:
                break
            j, t, _ = min(((j, t, -float(Xg[j] @ cen[t])) for j in members for t in targets),
                          key=lambda z: z[2])
            lab[j] = t
        else:
            c = small[0]
            donors = [t for t in range(k) if size[t] > lo]
            if not donors:
                for j in range(n):
                    if lab[j] == c:
                        lab[j] = int(np.argmax([Xg[j] @ cen[t] if t != c else -9 for t in range(k)]))
                continue
            cands = [(j, -float(Xg[j] @ cen[c])) for j in range(n) if lab[j] in donors]
            lab[min(cands, key=lambda z: z[1])[0]] = c
    order = {v: i for i, v in enumerate(sorted(set(lab)))}
    return [order[v] for v in lab]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "spar-f26-atlas.json"))
    ap.add_argument("--cache", default=os.path.join(HERE, "index.txt"),
                    help="local copy of index.txt (downloaded on first run)")
    args = ap.parse_args()

    overrides = load_json("theme_overrides.json")
    sub_names = load_json("subcluster_names.json")

    projects = parse(fetch_index(args.cache))
    print(f"parsed {len(projects)} projects", file=sys.stderr)
    for p in projects:
        p["group"] = assign_theme(p, overrides)

    X = vectors(projects)
    by_group = defaultdict(list)
    for i, p in enumerate(projects):
        by_group[p["group"]].append(i)
    for g, idx in by_group.items():
        for slot, i in zip(balanced_subclusters(X[idx]), idx):
            projects[i]["sub"] = f"{g}_{slot}"

    # similarity edges: mutual top-6 above 0.10, plus every intra-subcluster pair
    S = X @ X.T
    np.fill_diagonal(S, 0)
    edges = {}
    for i in range(len(projects)):
        for j in np.argsort(-S[i])[:6]:
            if S[i][j] > 0.10:
                edges[(min(i, int(j)), max(i, int(j)))] = round(float(S[i][j]), 3)
    by_sub = defaultdict(list)
    for i, p in enumerate(projects):
        by_sub[p["sub"]].append(i)
    for members in by_sub.values():
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                key = (min(members[a], members[b]), max(members[a], members[b]))
                edges[key] = max(edges.get(key, 0), round(float(S[members[a]][members[b]]), 3), 0.12)

    for i, p in enumerate(projects):
        hrs = re.search(r"(\d+)", p.get("hours", ""))
        inv = p.get("involvement", "")
        team = re.findall(r"\d+", p.get("team", ""))
        p["i"] = i
        p["hrsN"] = int(hrs.group(1)) if hrs else 10
        p["gname"] = GROUP_NAMES[p["group"]]
        p["sname"] = sub_names[p["sub"]]
        p["url"] = f"https://sparai.org/projects/f26/{p['id']}/"
        p["inv"] = ("Co-working" if "Co-working" in inv else "Detailed" if "Detailed" in inv
                    else "Guidance" if "Guidance" in inv else "Limited")
        p["teamMax"] = max(map(int, team)) if team else 2
        p["teamShort"] = re.sub(r"^Team size:\s*", "", p.get("team", "")).replace(" mentees", "").replace(" mentee", "")
        p["hoursShort"] = p.get("hours", "").replace("/week", "")

    payload = {
        "groups": GROUP_NAMES,
        "subs": sub_names,
        "projects": projects,
        "edges": [{"s": a, "t": b, "w": w} for (a, b), w in edges.items()],
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    sizes = sorted({s: len(v) for s, v in by_sub.items()}.values())
    print(f"wrote {args.out}: {len(projects)} nodes, {len(edges)} edges, "
          f"{len(by_sub)} sub-clusters (sizes {sizes[0]}-{sizes[-1]})", file=sys.stderr)


if __name__ == "__main__":
    main()
