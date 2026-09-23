---
layout: post
title: "A Terrain Map of AI Safety Research"
date: 2026-09-23
categories: [Research, AI Safety]
permalink: /blog/ai-safety-terrain/
---

[**→ Open the interactive map**](/ai-safety-map/terrain.html) · [data analysis](/ai-safety-map/figures/) · [SPAR Atlas](/spar-atlas/)

I made a terrain style visualisation of AI safety impact of around **2,769** works organised by citation count! The data was extracted from Arxiv and LessWrong posts based on a dictionary of **2,945 keywords** that appear in AI safety works. Additionally I think its important to see how the field has "evolved" over time so I added a time functionality to slide and see the hills forming.

* The map is based on how particular works overlap based on embedding space level clustering organised across **18** sub-fields. The height is based on the citation count for that particular area — log-compressed and summed across the neighbourhood, so a hill is tall because of volume *and* impact, not either alone.
* I have also added functionality to filter based on
   * citation count / upvote count
   * individual researcher (shows you their works on the map to understand what work they might be doing) — **2,936** researchers are in the underlying dataset

One thing to note on the data: the terrain itself is papers only, because Semantic Scholar doesn't index LessWrong. The forum side of the dataset feeds the researcher profiles rather than the hills. The time slider runs 2023Q1–2026Q3, but my harvest starts in 2024, so the first few quarters are thin by construction rather than because nothing was happening.

Some interesting high level observations: Alignment training and scalable oversight are very high citation presently — they have among the highest median citations per work in the set (12 and 9, against a corpus median of 6). The tallest hills, though, are adversarial robustness and Interpretability, because they have far more works (633 and 487, holding 24% and 18% of all citations here). So the two claims are about different things: one field is denser, the other lands harder per paper. Alignment training and scalable oversight also have the highest overlap based on the embedding model I used since they are very intertwined — **0.57 Jaccard, more than double the next closest pair** (AI control and safety cases, at 0.28).

Some drawbacks of this visualisation are: (1) citation count doesn't necessarily == impact and the research community may just cite each other in a feedback loop regardless of whether its actually contributing to "safety". It's a very skewed measure too — the top 1% of works hold 24% of all citations in the set, and the median work has 6. The full question is a lot more convoluted of course but I hope this visualisation helps give some insight atleast (2) in the modern scenario of the peer-reviewed venue ecosystem is under heavy strain; a lot of the safety community put out blogposts on LessWrong/ Effective Altruist / Alignment forum etc either as precursory to a publication or because they prefer it. This is hard to compare to citation count and the peer-reviewed venues. It's also a real split and not a small one: of the 2,936 researchers I collected, **only 67 write in both formats**. Around 1,971 publish papers only and 898 post only.

This work was inspired from my [SPAR Atlas](https://hannahhb.github.io/spar-atlas/) where I made a KG kind of structure to show how the different projects are related and EA posts talking about [where AI safety researchers go](https://forum.effectivealtruism.org/posts/SJBBgupFx7SXyBj2B/where-do-ai-safety-fellows-go-analyzing-a-dataset-of-600) and [AI Safety field growth analysis](https://forum.effectivealtruism.org/posts/7YDyziQxkWxbGmF3u/ai-safety-field-growth-analysis-2025). I used claude to do a lot of heavy lifting, such as making the scraper, writing the embeddings analysis etc but the key inspiration is about making a terain to understand the space a bit more interactively.

[More data analysis TBD]
