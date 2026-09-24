#!/usr/bin/env python3
"""Flag works whose only claim on AI safety is preference-tuning machinery.

The relevance gate reads vocabulary, and "using RLHF to reduce harm" and
"making RLHF cheaper" are written in the same words. So a pure optimisation
paper - DPO, SimPO, Diffusion-DPO - clears the gate on terms of art alone and
then, because such papers are heavily cited by the whole field, ends up
holding up a hill it has no safety content to justify.

A work is method-only when it speaks the alignment-method vocabulary and never
names a harm, a failure or a threat. That is a deliberately narrow test: a
paper that measures toxicity or refusal is doing safety work even if its
contribution is an optimiser, and it stays.
"""
import re

METHOD = re.compile(
    r"\b(rlhf|dpo|ppo|grpo|kto|orpo|simpo|ipo|rloo|rrhf|best.of.n)\b|"
    r"preference (optimi\w+|learning|tuning|alignment|data)|"
    r"reward (model|modelling|modeling|function|shaping)\b|"
    r"human (feedback|preferences)|pairwise preference|"
    r"(instruction|preference|alignment|policy) (tun\w+|fine.?tun\w+)|"
    r"bradley.terry|reference (policy|model)|kl (penalty|regularis|regulariz)",
    re.I)

# Naming any of these means the paper is about something going wrong, which is
# the thing that makes it safety work rather than post-training work.
OUTCOME = re.compile(
    r"harm\w*|jailbreak\w*|toxic\w*|unsafe|safety|misalign\w*|decepti\w*|"
    r"scheming|sycophan\w*|manipulat\w*|adversarial|attack\w*|red.?team\w*|"
    r"danger\w*|catastroph\w*|existential|refus\w*|guardrail|backdoor|poison\w*|"
    r"abuse|misuse|malicious|bias\w*|privacy|hallucinat\w*|honest\w*|"
    r"deceive|lie\b|lying|overconfiden\w*|reward (hacking|tampering)|"
    r"specification gaming|goal misgeneral\w*|power.seeking|corrigib\w*|"
    r"oversight|monitor\w*|censor\w*|robustness|vulnerab\w*|risk\w*|threat\w*",
    re.I)


def method_only(title, abstract):
    """True when the work reads as preference-tuning machinery and nothing else."""
    text = (title or "") + ". " + (abstract or "")
    if not METHOD.search(text):
        return False
    return not OUTCOME.search(text)
