"""Judge whether a work is actually about AI safety, from its title and abstract.

The failure mode this exists to stop: a capabilities paper that mentions
alignment once in its related work, or lists "AI safety" among motivations, and
so trips a keyword filter. Where a term appears matters more than whether it
appears - a paper's own contribution is stated in its title and the opening
sentences of its abstract, not in its literature review.
"""
import re

# Terms that only appear when someone is doing this work, not citing it.
CORE = re.compile(
    r"\bAI safety\b|\bAGI safety\b|\bAI alignment\b|\bmisalign\w*|alignment faking|"
    r"mechanistic interpretab|sparse autoencoder|activation (patching|steering|addition)|"
    r"circuit discovery|logit lens|crosscoder|transcoder|probing classifier|"
    r"\bRLHF\b|reward (hacking|tampering|misspecification)|specification gaming|"
    r"goal misgeneral\w*|scalable oversight|weak.to.strong|deceptive alignment|"
    r"\bscheming\b|sandbagging|situational awareness|evaluation.aware\w*|"
    r"dangerous capabilit\w*|capability elicitation|red.?teaming|jailbreak\w*|"
    r"prompt injection|sycophan\w*|chain.of.thought (faithful|monitor)\w*|"
    r"corrigib\w*|power.seeking|instrumental convergence|\bAI control\b|"
    # Order-insensitive: "Measuring Faithfulness in Chain-of-Thought Reasoning"
    # states the same contribution as "chain-of-thought faithfulness", and the
    # strict-adjacency pattern above only caught the second phrasing - which
    # admitted a dozen follow-up papers while rejecting the one they all cite.
    r"(un)?faithful\w*[^.]{0,40}(chain.of.thought|\bCoT\b|reasoning|explanation)|"
    r"(chain.of.thought|\bCoT\b|reasoning trace)[^.]{0,40}(un)?faithful\w*|"
    r"untrusted monitor\w*|machine unlearning|constitutional AI|harmlessness|"
    r"model welfare|existential risk|catastrophic risk|frontier (model|AI) (safety|risk)|"
    r"compute governance|AI governance|safety case\w*|model organism|"
    r"refusal (direction|behaviou?r|mechanism)|\brefusal\b|safety (fine.?tun|train)\w*|"
    r"monosemantic\w*|polysemantic\w*|superposition|feature (ablation|steering|direction)|"
    r"deception detect\w*|lie detect\w*|hallucination detect\w*|honest\w*|"
    r"interpretability of (language models|neural networks|transformers)|"
    # Interpretability aimed at model internals or at a reasoning trace. The
    # literal phrases above miss any paper that coins its own vocabulary, which
    # is exactly what the influential ones do - "Thought Anchors" never says
    # "mechanistic interpretability" anywhere in its abstract.
    r"(interpretab\w*|attribut\w*|causal (influence|importance)|circuit\w*)[^.]{0,60}"
    r"(reasoning (step|trace|chain|process)|chain.of.thought|\bCoT\b|"
    r"(language |frontier )?model'?s? (internal|computation|behaviou?r))|"
    r"(reasoning (step|trace|chain)|chain.of.thought|\bCoT\b)[^.]{0,60}"
    r"(interpretab\w*|attribut\w*|which .{0,20}matter|causal (influence|importance))|"
    r"latent knowledge|steering vector|residual stream|induction head|"
    r"emergent misalign\w*|subliminal learning|backdoor\w*|data poisoning|"
    r"value alignment|human feedback|preference (learning|optimi\w+)|"
    r"unlearn\w*|toxicity mitigation|harmful (content|behaviou?r|output)",
    re.I)

# Softer signals: real but not decisive on their own.
SUPPORT = re.compile(
    r"\balign\w+|\bsafety\b|\bsafe\b|interpretab\w*|robustness|adversarial|"
    r"trustworth\w*|reliab\w*|deception|faithful\w*|"
    r"harmful|toxicity|refusal|guardrail|oversight|evaluation|risk",
    re.I)

# If the abstract frames the work as something else, it probably is.
OFF_FRAME = re.compile(
    r"we (present|propose|introduce) a (new |novel )?(dataset|benchmark) for "
    r"(image|speech|translation|recommendation)|drug discovery|protein (folding|design)|"
    r"clinical|radiolog|medical imaging|autonomous driving|recommender system|"
    r"time series forecasting|weather|materials discovery",
    re.I)


def score(title, abstract):
    """0-10ish. Higher means the work is more plainly about AI safety."""
    title = title or ""
    abstract = (abstract or "").strip()
    head = abstract[:420]          # where a paper states its own contribution
    tail = abstract[420:]

    s = 0.0
    if CORE.search(title):
        s += 4.0
    s += 1.6 * len(set(m.group(0).lower() for m in CORE.finditer(head)))
    s += 0.25 * len(set(m.group(0).lower() for m in CORE.finditer(tail)))
    if SUPPORT.search(title):
        s += 0.8
    s += 0.2 * min(4, len(set(m.group(0).lower() for m in SUPPORT.finditer(head))))
    if OFF_FRAME.search(abstract):
        s -= 3.5
    return round(s, 2)


def relevant(title, abstract, threshold=3.0):
    return score(title, abstract) >= threshold
