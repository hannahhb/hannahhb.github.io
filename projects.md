---
layout: landing
title: "Projects"
permalink: /projects/
long: true
---

# Projects & publications

## Publications

### Robustness of Neurosymbolic Reasoners on First-Order Logic Problems
{: #alta}
<p class="meta">ALTA 2025 · 🏅 Best Paper · <a href="https://aclanthology.org/2025.alta-main.1/">Paper</a></p>

Are neurosymbolic reasoners more robust to counterfactual perturbations than plain LLMs with naive or chain-of-thought prompting?

## Projects

### Fragile or Just Hard? Robustness Prediction from Reasoning Probes
{: #aimo-interp}
<p class="meta">AIMO Interp @ NeurIPS 2026 · <a href="https://github.com/hannahhb/aimo_interp_segprobe/blob/main/paper/AIMO_Interp_Seg_Probe_2026.pdf">Paper</a> · <a href="https://github.com/hannahhb/aimo_interp_segprobe">Code</a></p>

Reasoning models can solve a problem reliably and still fail once it is perturbed. We ask whether this can be predicted from hidden states, and propose **SegProbe**, a difference-of-means linear probe on a single greedy chain of thought (at most 4k tokens).

- **White-box features replace sampling at low budget.** SegProbe alone reaches 0.774 accuracy, matching a black-box baseline built from eight sampled 16k-token solutions (0.772).
- **The full stack does best.** Combining SegProbe with trajectory and attention features and the black-box features reaches 0.831 accuracy and 0.850 AUC (5-fold CV grouped by problem, 20 repeats).
- **Robustness is related to competence but not the same thing.** Hidden states also carry signals such as self-correction and latent-state variability.
- Gains are uneven across models: the stack beats the black-box baseline on five of seven model configurations.

### CURE-Bench
{: #curebench}
<p class="meta">CURE-Bench @ NeurIPS 2025 · 🏅 Open Science Award · <a href="https://curebench.ai/posters">Posters</a></p>

### Can Follow-Up Questions Help Weak-to-Strong Monitors for Swarms?
{: #hackathon}
<p class="meta">Apart Research · Swarm Alignment Hackathon · Nov 2026 · <a href="https://apartresearch.com/sprints/projects/can-followup-questions-help-weaktostrong-monitors-for-swarms-wpcsuqz0d4">Project page</a> · <a href="https://github.com/hannahhb/active_investigator">Code</a> · <a href="/demo.html">Live demo (ish)</a></p>

Can a weak, trusted monitor catch false progress claims in a multi-agent swarm as the swarm grows? Using 83 log-verifiable progress claims from 14 frontier agents in the AI Village, a passive weak monitor (Qwen 3.5 9B) falls from AUROC 0.75 to 0.65 as it has to search logs from 1 to 50 agents, while a strong monitor (GPT-5-mini) stays at 0.97. Turning the weak monitor into an active investigator, which asks one follow-up question and checks the answer against the logs, lifts it to 0.93 (small swarms) and 0.88 (large swarms), recovering 76–82% of the weak-to-strong gap. A peer's "verified" label raised the spread of a false claim from 19% to 41%, and agents that falsify their own tool outputs defeat both monitors.

### SPAR Fall 2026: Can Follow-up Questions Catch Missing Reasoning?
{: #spar}
<p class="meta">With Pierre-Luc St-Charles · <a href="https://sparai.org/projects/f26/recVHalQ4NlHvSbUC/">Project page</a></p>

Using PyINE, LawZero's framework for studying reasoning models with full execution-trace supervision, we look at a shortcut-prone model organism that sometimes exits early on misleading cues, so the steps that would expose a wrong answer never appear. We are building a small investigator that asks targeted follow-up questions, and testing whether it catches these failures more reliably and cheaply than passive judges or debate, under fixed interaction and token budgets.
