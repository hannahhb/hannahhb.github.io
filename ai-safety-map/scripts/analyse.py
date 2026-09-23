#!/usr/bin/env python3
"""Descriptive analysis of the AI-safety corpus, as figures.

    python3 analyse.py   ->  ../figures/*.png  and  ../figures/index.html

Every figure answers a question the maps cannot: the maps show where work sits,
these show how it is distributed.
"""
import json, math, os, re
from collections import Counter, defaultdict

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from common import DATA, load

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
os.makedirs(OUT, exist_ok=True)

INK, GRID, BG = "#1a1a1a", "#d8d5cf", "#ffffff"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG,
    "axes.edgecolor": "#b9b5ad", "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK, "grid.color": GRID,
    "font.family": "sans-serif", "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "600", "figure.dpi": 130,
})
FIGS = []


def save(fig, name, title, caption):
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    FIGS.append((name, title, caption))
    print(f"  {name}")


def hue(i, n, l=0.62, c=0.16):
    import colorsys
    return colorsys.hls_to_rgb((i / n) % 1.0, l, c * 3.4)


def main():
    wa = load("work_areas.json", {}) or {}
    works, areas = wa.get("works", {}), wa.get("areas", [])
    ov = load("overlap.json", {}) or {}
    imp = load("impact.json", {}) or {}
    QS = imp.get("quarters", [])
    spec = load("specter.json", {}) or {}
    ab = load("abstracts.json", {}) or {}
    print(f"{len(works)} works, {len(areas)} areas")

    cites = np.array([w.get("cites") or 0 for w in works.values()], dtype=float)
    prim = {k: (w["areas"][0]["a"] if w.get("areas") else None) for k, w in works.items()}
    colors = {a: hue(i, len(areas)) for i, a in enumerate(areas)}

    # ---- 1. citation distribution ----------------------------------------
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    pos = cites[cites > 0]
    bins = np.logspace(0, math.log10(max(pos.max(), 10)), 42)
    ax.hist(pos, bins=bins, color="#2f6f6a", edgecolor="white", linewidth=.5)
    ax.set_xscale("log")
    ax.set_xlabel("citations (log scale)"); ax.set_ylabel("works")
    med, p90, p99 = np.percentile(pos, [50, 90, 99])
    for v, lab in ((med, "median"), (p90, "90th"), (p99, "99th")):
        ax.axvline(v, color="#c2562f", lw=1.1, ls="--")
        ax.annotate(f"{lab}\n{v:.0f}", (v, ax.get_ylim()[1] * .82),
                    ha="center", fontsize=8.5, color="#c2562f")
    ax.set_title("Most AI-safety work is barely cited; a thin tail carries the field")
    ax.grid(axis="y", alpha=.4)
    zero = int((cites == 0).sum())
    save(fig, "01_citation_distribution.png", "Citation distribution",
         f"{len(pos):,} works with at least one citation ({zero:,} with none). "
         f"Median {med:.0f}, 90th percentile {p90:.0f}, 99th {p99:.0f} — "
         f"the top 1% of works hold {100*pos[pos>=p99].sum()/pos.sum():.0f}% of all citations.")

    # ---- 2. by area ------------------------------------------------------
    order = sorted({a for a in prim.values() if a},
                   key=lambda a: -np.median([works[k].get("cites") or 0
                                             for k in works if prim[k] == a] or [0]))
    data = [[max(0.6, works[k].get("cites") or 0.6) for k in works if prim[k] == a] for a in order]
    fig, ax = plt.subplots(figsize=(8.2, 6.4))
    bp = ax.boxplot(data, vert=False, patch_artist=True, widths=.62, showfliers=False)
    for patch, a in zip(bp["boxes"], order):
        patch.set_facecolor(colors[a]); patch.set_alpha(.72); patch.set_edgecolor("#5b5b5b")
    for m in bp["medians"]: m.set_color("#1a1a1a"); m.set_linewidth(1.5)
    ax.set_yticklabels([f"{a}  ({len(d)})" for a, d in zip(order, data)], fontsize=9)
    ax.set_xscale("log"); ax.set_xlabel("citations (log scale)")
    ax.set_title("Citation distribution by research area")
    ax.grid(axis="x", alpha=.4)
    save(fig, "02_citations_by_area.png", "Citations by area",
         "Box shows the interquartile range, line the median, count in brackets. "
         "Areas differ far more in volume than in typical per-work impact.")

    # ---- 3. distinctive vocabulary per area ------------------------------
    STOP = set("""the a an and or of to in for on with by from as at is are be this that we our
    can it its their they which use used using show shows results paper study model models based
    new approach method methods propose proposed present performance data set also more most such
    when what how than then these those has have had been was were will would may might not only
    but if into over under between during each both all any some other others one two three""".split())
    txt_by_area = defaultdict(list)
    for k, w in works.items():
        a = prim.get(k)
        if not a:
            continue
        t = (w.get("title") or "") + " " + ((ab.get(k) or {}).get("abstract") or "")
        txt_by_area[a].append(t.lower())
    tot = Counter()
    per = {}
    for a, texts in txt_by_area.items():
        c = Counter()
        for t in texts:
            for tok in set(re.findall(r"[a-z][a-z-]{3,}", t)):
                if tok not in STOP:
                    c[tok] += 1
        per[a] = c; tot.update(c)
    N = sum(len(v) for v in txt_by_area.values())
    top = sorted(per, key=lambda a: -len(txt_by_area[a]))[:9]
    fig, axes = plt.subplots(3, 3, figsize=(12.4, 9))
    for ax, a in zip(axes.ravel(), top):
        n = len(txt_by_area[a])
        # log-odds against the rest of the corpus: words that mark this area out
        sc = []
        for w_, c in per[a].items():
            if c < max(3, n * .04):
                continue
            p_in = c / n
            p_out = max(1e-9, (tot[w_] - c) / max(1, N - n))
            sc.append((math.log(p_in / p_out), w_, c))
        sc.sort(reverse=True)
        sc = sc[:11][::-1]
        ax.barh([s[1] for s in sc], [s[0] for s in sc], color=colors[a], alpha=.85)
        ax.set_title(f"{a}  ({n})", fontsize=10)
        ax.tick_params(labelsize=8.5); ax.grid(axis="x", alpha=.3)
        ax.set_xlabel("log-odds vs rest of corpus", fontsize=7.6)
    for ax in axes.ravel()[len(top):]:
        ax.axis("off")
    fig.suptitle("What each area talks about that the others do not", y=1.005, fontsize=13)
    save(fig, "03_area_vocabulary.png", "Distinctive vocabulary",
         "Log-odds of each word appearing in this area versus the rest of the corpus. "
         "High bars are terms of art; their absence would mean an area is not distinctive.")

    # ---- 4. growth ------------------------------------------------------
    qcount = defaultdict(lambda: np.zeros(len(QS)))
    for w in imp.get("works", []):
        if w.get("q") is None or not w.get("a"):
            continue
        qcount[w["a"][0]["a"]][w["q"]] += 1
    keys = sorted(qcount, key=lambda a: -qcount[a].sum())[:9]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.stackplot(range(len(QS)), [qcount[a] for a in keys],
                 labels=keys, colors=[colors[a] for a in keys], alpha=.9)
    ax.set_xticks(range(0, len(QS), 2)); ax.set_xticklabels(QS[::2], rotation=45, ha="right", fontsize=8.5)
    ax.set_ylabel("works published"); ax.legend(fontsize=7.6, loc="upper left", ncol=2, framealpha=.9)
    ax.set_title("Output per quarter, by area")
    ax.grid(axis="y", alpha=.35)
    save(fig, "04_growth.png", "Growth over time",
         "Counted by publication quarter. The dip in the most recent quarters is indexing lag, "
         "not a decline — very recent work has not all been picked up yet.")

    # ---- 5. concentration ------------------------------------------------
    fig, ax = plt.subplots(figsize=(5.6, 5.4))
    s = np.sort(cites)[::-1]
    cum = np.cumsum(s) / s.sum()
    x = np.arange(1, len(s) + 1) / len(s)
    ax.plot(x * 100, cum * 100, color="#2f6f6a", lw=2)
    ax.plot([0, 100], [0, 100], color="#b9b5ad", ls="--", lw=1)
    for frac in (.01, .05, .10):
        i = max(0, int(len(s) * frac) - 1)
        ax.annotate(f"top {frac*100:.0f}% of works\n{cum[i]*100:.0f}% of citations",
                    (frac * 100, cum[i] * 100), xytext=(frac * 100 + 14, cum[i] * 100 - 12),
                    fontsize=8.4, color="#c2562f",
                    arrowprops=dict(arrowstyle="->", color="#c2562f", lw=.9))
    ax.set_xlabel("share of works (%)"); ax.set_ylabel("share of citations (%)")
    ax.set_title("How concentrated impact is"); ax.grid(alpha=.35)
    asc = np.sort(cites); n = len(asc)
    gini = (2 * np.sum((np.arange(1, n + 1)) * asc) / (n * asc.sum())) - (n + 1) / n
    save(fig, "05_concentration.png", "Impact concentration",
         f"Lorenz curve of citations. Gini {gini:.2f} — a value near 1 means a handful of works "
         "account for almost everything, which is the normal shape for citation data.")

    # ---- 6. area overlap --------------------------------------------------
    J = np.array(ov.get("jaccard", []))
    if J.size:
        names = ov["areas"]
        idx = np.argsort([-np.array(ov["volume"])[i] for i in range(len(names))])
        Js = J[np.ix_(idx, idx)]
        ns = [names[i] for i in idx]
        fig, ax = plt.subplots(figsize=(8.6, 7.4))
        np.fill_diagonal(Js, np.nan)
        im = ax.imshow(Js, cmap="BuPu", vmin=0)
        ax.set_xticks(range(len(ns))); ax.set_xticklabels(ns, rotation=52, ha="right", fontsize=8)
        ax.set_yticks(range(len(ns))); ax.set_yticklabels(ns, fontsize=8)
        fig.colorbar(im, ax=ax, shrink=.8, label="share of work sitting in both")
        ax.set_title("Which areas share their work")
        save(fig, "06_overlap_matrix.png", "Area overlap",
             "Jaccard overlap on the soft area assignments. Ordered by size; the diagonal is blanked.")

    # ---- 7. impact rate by age -------------------------------------------
    rows = []
    for w in imp.get("works", []):
        if w.get("q") is None or w.get("c") is None:
            continue
        rows.append((w["q"], w["c"]))
    if rows:
        byq = defaultdict(list)
        for q, c in rows:
            byq[q].append(c)
        qs = sorted(byq)
        med = [np.median(byq[q]) for q in qs]
        p90 = [np.percentile(byq[q], 90) for q in qs]
        fig, ax = plt.subplots(figsize=(9, 4.4))
        ax.plot([QS[q] for q in qs], med, "o-", color="#2f6f6a", label="median")
        ax.plot([QS[q] for q in qs], p90, "s--", color="#c2562f", label="90th percentile")
        ax.set_ylabel("citations so far"); ax.legend(fontsize=9)
        ax.tick_params(axis="x", rotation=45, labelsize=8.5)
        ax.set_title("Citations accrued, by when the work was published")
        ax.grid(alpha=.35)
        save(fig, "07_citations_by_age.png", "Citations by publication quarter",
             "Older work has had longer to accumulate, so the downward slope is age, not quality. "
             "This is the curve that any 'most cited' ranking is quietly fighting.")

    # ---- 8. venue mix per area -------------------------------------------
    TOPV = [v for v, _ in Counter(w["venue"] for w in works.values()
                                  if w.get("venue")).most_common(7)]
    SHORT = {"arXiv.org": "arXiv (preprint only)",
             "Annual Meeting of the Association for Computational Linguistics": "ACL",
             "Neural Information Processing Systems": "NeurIPS",
             "International Conference on Learning Representations": "ICLR",
             "Conference on Empirical Methods in Natural Language Processing": "EMNLP",
             "International Conference on Machine Learning": "ICML",
             "AAAI Conference on Artificial Intelligence": "AAAI"}
    lab = [SHORT.get(v, v) for v in TOPV] + ["other venue", "no venue recorded"]
    M = np.zeros((len(order), len(lab)))
    for k, w in works.items():
        a = prim.get(k)
        if a is None:
            continue
        v = w.get("venue")
        j = TOPV.index(v) if v in TOPV else (len(TOPV) if v else len(TOPV) + 1)
        M[order.index(a), j] += 1
    Mp = M / np.maximum(1, M.sum(axis=1, keepdims=True)) * 100
    pal = ["#8e8a82", "#2f6f6a", "#c2562f", "#4a6fa5", "#7d5ba6", "#b08a3e", "#4f8f5b",
           "#cfcabf", "#edeae3"]
    fig, ax = plt.subplots(figsize=(9.4, 6.2))
    left = np.zeros(len(order))
    for j, name in enumerate(lab):
        ax.barh(range(len(order)), Mp[:, j], left=left, color=pal[j],
                label=name, edgecolor="white", linewidth=.5)
        left += Mp[:, j]
    ax.set_yticks(range(len(order))); ax.set_yticklabels(order, fontsize=9)
    ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("share of the area's works (%)")
    ax.legend(fontsize=7.6, ncol=3, loc="upper center", bbox_to_anchor=(.5, -.115), framealpha=.95)
    ax.set_title("Where each area publishes")
    save(fig, "08_venue_mix.png", "Venue mix by area",
         "Areas are in the same order as the previous chart. The grey bar on the left is work "
         "that exists only as an arXiv preprint; areas dominated by it are moving faster than "
         "peer review, or are not aimed at it.")

    # ---- 9-11. people ------------------------------------------------------
    people = (load("people.json", {}) or {}).get("people", [])
    SECT = {"frontier_lab": ("Frontier lab", "#c2562f"),
            "safety_org": ("Safety non-profit / venture", "#2f6f6a"),
            "academia": ("Academia", "#4a6fa5"),
            "government": ("Government", "#7d5ba6"),
            "policy_org": ("Policy organisation", "#b08a3e"),
            "unknown": ("Affiliation unknown", "#c9c6c0")}

    # 9. output vs impact
    fig, ax = plt.subplots(figsize=(8.4, 6))
    for sec in ["unknown", "academia", "safety_org", "policy_org", "government", "frontier_lab"]:
        pts = [(p["works_total"], (p.get("citations") or 0) + (p.get("post_score") or 0))
               for p in people if p.get("sector") == sec and p.get("works_total")]
        if not pts:
            continue
        xs = np.array([a for a, b in pts], float)
        ys = np.array([max(b, .5) for a, b in pts], float)
        ax.scatter(xs, ys, s=15, alpha=.55 if sec == "unknown" else .85,
                   color=SECT[sec][1], label=f"{SECT[sec][0]} ({len(pts)})",
                   linewidth=0, zorder=1 if sec == "unknown" else 2)
    ax.set_xscale("log"); ax.set_yscale("log")
    reach = lambda p: (p.get("citations") or 0) + (p.get("post_score") or 0)
    ranked = sorted([p for p in people if p.get("works_total")], key=lambda p: -reach(p))[:10]
    ranked.sort(key=lambda p: p["works_total"])
    ax.set_ylim(top=max(reach(p) for p in ranked) * 9)
    for i, p in enumerate(ranked):
        # stagger upward in a staircase so the names never sit on top of each other
        ax.annotate(p["name"], (p["works_total"], max(reach(p), .5)),
                    xytext=(0, 18 + 13 * ((i * 3) % 7)), textcoords="offset points",
                    fontsize=7.6, color="#3a3a3a", ha="center",
                    arrowprops=dict(arrowstyle="-", color="#bdb9b1", lw=.7, shrinkB=3))
    ax.set_xlabel("works in the corpus"); ax.set_ylabel("citations + LessWrong karma")
    ax.legend(fontsize=8, loc="lower right", framealpha=.95)
    ax.set_title("Output against reach, per researcher", pad=54); ax.grid(alpha=.3)
    save(fig, "09_people_output_impact.png", "Researchers: output vs reach",
         "Both axes are logarithmic. Citations and karma are summed only to place people on one "
         "chart — they are not comparable units. Affiliation is missing for most people, so the "
         "grey cloud is not a finding about independents.")

    # 10. entry cohorts
    yrs = [p["first_year"] for p in people if p.get("first_year") and 2005 <= p["first_year"] <= 2026]
    cy = Counter(yrs); ys_ = sorted(cy)
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    ax.bar(ys_, [cy[y] for y in ys_], color="#2f6f6a", edgecolor="white")
    cum = np.cumsum([cy[y] for y in ys_])
    ax2 = ax.twinx()
    ax2.plot(ys_, cum / cum[-1] * 100, color="#c2562f", lw=1.6)
    ax2.set_ylabel("cumulative share of people (%)", color="#c2562f")
    ax2.tick_params(axis="y", colors="#c2562f"); ax2.set_ylim(0, 102)
    ax.set_ylabel("people entering"); ax.set_xlabel("year of their first AI-safety work")
    ax.set_title("When today's AI-safety researchers started publishing")
    ax.grid(axis="y", alpha=.3)
    half = next(y for y, c in zip(ys_, cum) if c >= cum[-1] * .5)
    save(fig, "10_entry_cohorts.png", "Entry cohorts",
         f"Half of the {len(yrs):,} people in this dataset published their first AI-safety work "
         f"in {half} or later — it measures entry into safety, not the start of a research career. "
         "2026 is not a full year and 2025 dips against its neighbours; treat the last three bars "
         "as one plateau rather than reading a trend into them.")

    # 11. the two literatures
    fig, ax = plt.subplots(figsize=(7.6, 6))
    rng = np.random.default_rng(7)
    npap = np.array([p.get("papers") or 0 for p in people], float)
    npos = np.array([p.get("posts") or 0 for p in people], float)
    both = int(((npap > 0) & (npos > 0)).sum())
    quad = {"papers only": int(((npap > 0) & (npos == 0)).sum()),
            "posts only": int(((npap == 0) & (npos > 0)).sum()),
            "both": both}
    # jitter, because counts are integers and hundreds of people share each cell
    jx = lambda v: np.maximum(v, .38) * np.exp(rng.normal(0, .055, len(v)))
    ax.scatter(jx(npap), jx(npos), s=12, alpha=.42, color="#4a6fa5", linewidth=0)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(.3, max(npap.max(), 10) * 1.7); ax.set_ylim(.3, max(npos.max(), 10) * 2.6)
    ax.axhline(.62, color="#b9b5ad", lw=1); ax.axvline(.62, color="#b9b5ad", lw=1)
    ax.set_xlabel("peer-reviewed / arXiv papers"); ax.set_ylabel("LessWrong & Alignment Forum posts")
    ax.set_title("Two literatures, barely overlapping")
    for fx, fy, ha, key in ((.04, .96, "left", "posts only"), (.97, .96, "right", "both"),
                            (.97, .06, "right", "papers only")):
        ax.annotate(f"{key}\n{quad[key]:,} people", (fx, fy), xycoords="axes fraction",
                    fontsize=9, color="#6e6a62", ha=ha, va="top" if fy > .5 else "bottom")
    ax.grid(alpha=.25)
    save(fig, "11_two_literatures.png", "Papers vs forum posts",
         f"Each dot is one person; the axis floor is 'none'. Only {both:,} of {len(people):,} "
         "people write in both registers. The terrain map is built from papers alone, because "
         "Semantic Scholar does not index forum posts — this chart is the size of what that omits.")

    # ---- index -----------------------------------------------------------
    html = ["<title>AI Safety Corpus — Analysis</title>",
            "<style>body{font:15px/1.65 -apple-system,system-ui,sans-serif;max-width:940px;"
            "margin:40px auto;padding:0 20px;color:#1a1a1a}h1{font-size:26px;letter-spacing:-.02em}"
            "figure{margin:38px 0}img{width:100%;border:1px solid #e3e0da;border-radius:8px}"
            "figcaption{color:#5c5850;font-size:13.5px;margin-top:9px}h2{font-size:17px;margin-bottom:4px}"
            "a{color:#2f6f6a}</style>",
            "<h1>AI Safety Corpus — descriptive analysis</h1>",
            f"<p>{len(works):,} works across {len(areas)} research areas, classified by SPECTER2 "
            "embeddings. Citations are a present-day snapshot from Semantic Scholar. "
            "<a href='../terrain.html'>Back to the terrain</a>.</p>"]
    for name, title, cap in FIGS:
        html.append(f"<figure><h2>{title}</h2><img src='{name}' alt='{title}'>"
                    f"<figcaption>{cap}</figcaption></figure>")
    open(os.path.join(OUT, "index.html"), "w").write("\n".join(html))
    print(f"\n{len(FIGS)} figures -> figures/index.html")


if __name__ == "__main__":
    main()
