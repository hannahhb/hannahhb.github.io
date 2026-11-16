---
layout: page
title: "Publications"
---

# Publications & Projects

### 🐝 Can Follow-Up Questions Help Weak-to-Strong Monitors for Swarms?
*Apart Research · Swarm Alignment Hackathon · November 2026*  
*[Project page](https://apartresearch.com/sprints/projects/can-followup-questions-help-weaktostrong-monitors-for-swarms-wpcsuqz0d4) · [Code](https://github.com/hannahhb/active_investigator) · [Live demo (ish)](/demo.html)*

Can a weak, trusted monitor catch false progress claims in a multi-agent swarm as the swarm grows? Using 83 log-verifiable progress claims from 14 frontier agents in the AI Village, a passive weak monitor (Qwen 3.5 9B) falls from AUROC 0.75 to 0.65 as it has to search logs from 1 to 50 agents, while a strong monitor (GPT-5-mini) stays at 0.97. Turning the weak monitor into an active investigator, which asks one follow-up question and checks the answer against the logs, lifts it to 0.93 (small swarms) and 0.88 (large swarms), recovering 76–82% of the weak-to-strong gap. A peer's "verified" label raised the spread of a false claim from 19% to 41%, and agents that falsify their own tool outputs defeat both monitors.

---

### 🔬 Fragile or Just Hard? Robustness Prediction from Reasoning Probes
{: #aimo-interp}
*AIMO Interpretability Challenge @ NeurIPS 2026 · [Code](https://github.com/hannahhb/aimo_interp_segprobe)*

Reasoning models can solve a problem reliably and still fail once it is perturbed. We ask whether this can be predicted from hidden states, and propose **SegProbe**, a difference-of-means linear probe on a single greedy chain of thought (at most 4k tokens).

- **White-box features replace sampling at low budget.** SegProbe alone reaches 0.774 accuracy, matching a black-box baseline built from eight sampled 16k-token solutions (0.772).
- **The full stack does best.** Combining SegProbe with trajectory and attention features and the black-box features reaches 0.831 accuracy and 0.850 AUC (5-fold CV grouped by problem, 20 repeats).
- **Robustness is related to competence but not the same thing.** Hidden states also carry signals such as self-correction and latent-state variability.
- Gains are uneven across models: the stack beats the black-box baseline on five of seven model configurations.

---

### 🌱 SPAR Fall 2026: Can Follow-up Questions Catch Missing Reasoning?
*Mentored by Pierre-Luc St-Charles · [Project page](https://sparai.org/projects/f26/recVHalQ4NlHvSbUC/)*

Using PyINE, LawZero's framework for studying reasoning models with full execution-trace supervision, we look at a shortcut-prone model organism that sometimes exits early on misleading cues, so the steps that would expose a wrong answer never appear. We are building a small investigator that asks targeted follow-up questions, and testing whether it catches these failures more reliably and cheaply than passive judges or debate, under fixed interaction and token budgets.

---

### 🧠 Robustness of Neurosymbolic Reasoners on First-Order Logic Problems
*🌟 Best paper at the Annual Workshop of the Australasian Language Technology Association*  
*[Paper link](https://arxiv.org/pdf/2509.17377)*

In this paper we explore whether neurosymbolic reasoners are more robust to counterfactual pertubations when compared to pure LLMs such as naive and chain of thought prompting. 
[Read Blog →](/blog/neurosymbolic2025) TBD

---

### 🩺 CURE-Bench @ NeurIPS 2025
*🌟 Open Science Award · [Posters](https://curebench.ai/posters)*

<!-- ---

### 🧬 Tool-Augmented Medical LLMs
*CSIRO Health & Biosecurity – 2025*  
Developing an evaluation framework for clinical reasoning models using fact-based decomposition and hallucination detection.

---

### 📘 Multi-Agent Debate for Logical Decision-Making
*University of Melbourne, 2024*  
A framework using multi-agent LLMs for cooperative reasoning tasks under uncertainty. -->


{% include visit-prompt.html %}
