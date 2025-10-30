---
layout: home
title: "Blog"
---

# 📰 Blog

Here I write about research updates, experiments, and reflections on AI reasoning, symbolic methods, and biomedical NLP.

---

{% for post in site.posts %}
- [{{ post.title }}]({{ post.url | relative_url }}) — {{ post.date | date: "%B %d, %Y" }}
{% endfor %}