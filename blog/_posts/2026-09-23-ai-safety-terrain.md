---
layout: post
title: "A Terrain Map of AI Safety Research"
date: 2026-09-23
categories: [Research, AI Safety]
permalink: /blog/ai-safety-terrain/
---

[**→ Open the interactive map**](/ai-safety-map/terrain.html) · [data analysis](/ai-safety-map/figures/) · [SPAR Atlas](/spar-atlas/)

I made a terrain style visualisation of AI safety impact of around **3,385** works organised by citation count! The data was extracted from Arxiv and LessWrong posts based on a dictionary of **2,945 keywords** that appear in AI safety works. Additionally I think its important to see how the field has "evolved" over time so I added a time functionality to slide and see the hills forming.

* The map is based on how particular works overlap based on embedding space level clustering organised across **18** sub-fields. The height is based on the citation count for that particular area — log-compressed and summed across the neighbourhood, so a hill is tall because of volume *and* impact, not either alone.
* I have also added functionality to filter based on
   * citation count / upvote count
   * individual researcher (shows you their works on the map to understand what work they might be doing) — the search matches the **3,977** author names attached to papers on the map
   * clicking a work zooms into it and lists the ten works nearest it, so you can see what surrounds it
   * looking up a paper by name, which drops you onto it on the map
   * hiding method-only papers (see the drawbacks below)

One thing to note on the data: the terrain itself is papers only, because Semantic Scholar doesn't index LessWrong. The forum side of the dataset feeds the researcher profiles rather than the hills. The slider runs **2021Q1–2026Q3**, and 2021–22 really are that sparse — about 30 works a year clear the relevance filter, which is roughly what the field looked like before ChatGPT. Two different groups of people also get counted below, so worth separating them: **3,977** names are attached to papers on the map (only the first three authors of each paper are recorded), while the profile dataset I built separately covers **2,936** researchers. Only 1,253 are in both — the rest either write on the forums rather than publishing, or sit fourth-or-later on their papers.

Some interesting high level observations: Alignment training and scalable oversight are very high citation presently (followed by adversarial robustness and Interpretability) — **35,851 / 34,509 / 30,914 / 16,111** citations. Most of that sits in a handful of 2022–23 papers: InstructGPT (24,222), DPO (10,596), Anthropic's helpful-and-harmless RLHF paper (4,365) and Constitutional AI (3,709). Adversarial robustness and Interpretability actually have far more works (995 and 800, against 378 and 343), they just get cited less per paper. Alignment training and scalable oversight have the highest overlap based on the embedding model I used since they are very intertwined — **0.64 Jaccard, double the next closest pair**.

Some drawbacks of this visualisation are: (1) citation count doesn't necessarily == impact and the research community may just cite each other in a feedback loop regardless of whether its actually contributing to "safety". It's a very skewed measure too — the top 1% of works hold **40%** of all citations in the set, and the median work has 7 against a mean of 57. Worse, a lot of that mass sits in papers that are really about training methods rather than safety: InstructGPT is **53%** of scalable oversight on its own and DPO is **31%** of alignment training, and if you drop just the top paper from each area the ordering flips straight back to adversarial robustness first. I've added a filter to hide papers whose only claim on safety is preference-tuning machinery and no named harm — 188 works, carrying 13% of all the citations here. It doesn't catch InstructGPT, since that paper does measure toxicity, so this is a partial fix rather than a clean one. The full question is a lot more convoluted of course but I hope this visualisation helps give some insight atleast (2) in the modern scenario of the peer-reviewed venue ecosystem is under heavy strain; a lot of the safety community put out blogposts on LessWrong/ Effective Altruist / Alignment forum etc either as precursory to a publication or because they prefer it. This is hard to compare to citation count and the peer-reviewed venues. It's also a real split and not a small one: of the 2,936 researchers I have profiles for, **only 67 write in both**. 1,971 publish papers only and 898 post only.

This work was inspired from my [SPAR Atlas](https://hannahhb.github.io/spar-atlas/) where I made a KG kind of structure to show how the different projects are related and EA posts talking about [where AI safety researchers go](https://forum.effectivealtruism.org/posts/SJBBgupFx7SXyBj2B/where-do-ai-safety-fellows-go-analyzing-a-dataset-of-600) and [AI Safety field growth analysis](https://forum.effectivealtruism.org/posts/7YDyziQxkWxbGmF3u/ai-safety-field-growth-analysis-2025). I used claude to do a lot of heavy lifting, such as making the scraper, writing the embeddings analysis etc but the key inspiration is about making a terain to understand the space a bit more interactively.

[More data analysis TBD]
