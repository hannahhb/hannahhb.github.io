#!/usr/bin/env python3
"""Build a technical AI-safety keyword vocabulary.

Three layers:
  1. a hand-written seed taxonomy of terms of art, by theme;
  2. mechanical variants of each seed - plurals, hyphenation, spacing,
     acronyms - because papers spell these a dozen ways;
  3. terms mined from the harvested corpus: n-grams that recur across
     known-safety titles and abstracts and are not generic ML vocabulary.

    python3 build_keywords.py [--min-count 3]   ->  data/keywords.json

The point is precision. "Transformer" and "benchmark" are deliberately absent:
they match everything. "Activation patching" and "crosscoder" are the kind of
term that only appears when someone is actually doing this work.
"""
import argparse, json, re
from collections import Counter, defaultdict
from common import load, save

SEEDS = {
  "interpretability_methods": [
    "mechanistic interpretability", "activation patching", "causal tracing",
    "path patching", "attribution patching", "activation steering", "steering vector",
    "conditional activation steering", "representation engineering", "activation addition",
    "logit lens", "tuned lens", "linear probe", "probing classifier", "sparse probing",
    "sparse autoencoder", "transcoder", "crosscoder", "matryoshka sparse autoencoder",
    "dictionary learning", "feature splitting", "feature absorption", "monosemanticity",
    "polysemanticity", "superposition hypothesis", "circuit discovery", "circuit analysis",
    "automated circuit discovery", "edge attribution patching", "ablation study",
    "causal scrubbing", "distributed alignment search", "interchange intervention",
    "activation difference", "model diffing", "representation similarity",
    "induction head", "attention head ablation", "residual stream", "logit attribution",
    "direct logit attribution", "neuron interpretability", "feature visualisation",
    "concept bottleneck", "concept activation vector", "sae feature", "latent direction",
    "weight-based interpretability", "developmental interpretability", "singular learning theory",
    "agentic interpretability", "relevance patching", "self-repair", "backup head",
    "grokking", "emergent capability", "linear representation hypothesis",
  ],
  "alignment_failures": [
    "deceptive alignment", "emergent misalignment", "narrow misalignment",
    "alignment faking", "reward hacking", "reward tampering", "reward misspecification",
    "specification gaming", "goal misgeneralisation", "inner misalignment",
    "mesa-optimisation", "mesa-optimiser", "deceptive behaviour", "scheming",
    "sandbagging", "sycophancy", "situational awareness", "evaluation awareness",
    "self-preservation", "shutdown resistance", "power-seeking", "instrumental convergence",
    "treacherous turn", "gradient hacking", "steganography", "collusion",
    "subliminal learning", "out-of-context reasoning", "task gaming",
  ],
  "oversight_and_control": [
    "scalable oversight", "ai control", "untrusted monitoring", "trusted monitoring",
    "control protocol", "control evaluation", "debate protocol", "recursive reward modelling",
    "iterated amplification", "weak-to-strong generalisation", "process supervision",
    "outcome supervision", "constitutional ai", "rlhf", "rlaif", "dpo",
    "reward model", "preference model", "red teaming", "automated red teaming",
    "jailbreak", "prompt injection", "adversarial suffix", "refusal direction",
    "unlearning", "concept ablation", "concept ablation fine-tuning", "machine unlearning",
    "safety fine-tuning", "harmlessness", "helpfulness", "deliberative alignment",
  ],
  "reasoning_and_cot": [
    "chain of thought", "chain-of-thought faithfulness", "cot monitorability",
    "cot monitoring", "reasoning trace", "thought anchor", "resampling",
    "latent reasoning", "implicit planning", "introspection", "verbalisation",
    "unfaithful reasoning", "hidden reasoning", "encoded reasoning", "obfuscated reasoning",
  ],
  "evaluation": [
    "dangerous capability evaluation", "capability elicitation", "model organism",
    "model organisms of misalignment", "benchmark saturation", "construct validity",
    "elicitation gap", "secret knowledge elicitation", "hallucination detection",
    "deception detection", "lie detection", "honesty evaluation", "eval gaming",
    "safety case", "frontier safety framework", "responsible scaling policy",
    "dangerous capabilities", "uplift study", "activation oracle",
  ],
  "governance": [
    "compute governance", "frontier model regulation", "model registration",
    "compute threshold", "structured access", "third-party audit", "external red teaming",
    "ai safety institute", "international governance", "verification regime",
    "export control", "chip smuggling", "incident reporting", "whistleblower protection",
  ],
  "welfare_and_philosophy": [
    "model welfare", "ai welfare", "digital sentience", "moral patienthood",
    "introspective report", "self-report", "persona vector", "assistant persona",
    "character training", "model character",
  ],
}

# Generic vocabulary that would match everything. Never a keyword on its own.
TOO_GENERIC = {
  "language model", "large language model", "neural network", "deep learning",
  "machine learning", "transformer", "benchmark", "dataset", "fine-tuning",
  "training data", "artificial intelligence", "evaluation", "performance",
  "accuracy", "state of the art", "experiments show", "we propose", "in this paper",
  "our method", "results show", "prior work", "future work", "related work",
  "open source", "case study", "empirical study", "recent work", "human feedback",
  "downstream task", "natural language", "computer vision", "reinforcement learning",
}


COMMON_WORDS = {
  "art", "cat", "dog", "map", "set", "act", "aim", "air", "all", "and", "any",
  "are", "arm", "bar", "bit", "box", "can", "car", "cost", "cut", "day", "end",
  "few", "fit", "for", "get", "had", "has", "her", "him", "his", "how", "its",
  "let", "lot", "low", "man", "may", "new", "not", "now", "off", "old", "one",
  "our", "out", "own", "per", "put", "run", "say", "see", "she", "sit", "six",
  "sum", "ten", "the", "top", "try", "two", "use", "via", "war", "was", "way",
  "who", "why", "win", "yes", "yet", "you", "raw", "red", "sad", "sat",
}


def variants(term):
    """plurals, hyphen/space swaps, British/American -ise/-ize, acronyms."""
    out = {term}
    out.add(term.replace("-", " "))
    out.add(term.replace(" ", "-"))
    if "isation" in term: out.add(term.replace("isation", "ization"))
    if "ization" in term: out.add(term.replace("ization", "isation"))
    if "ise" in term: out.add(term.replace("ise", "ize"))
    if "our" in term: out.add(term.replace("our", "or"))          # behaviour/behavior
    head = term.rsplit(" ", 1)
    if len(head) == 2 and not term.endswith("s"):
        out.add(term + "s")
    words = term.split()
    if len(words) >= 2 and all(w[0].isalpha() for w in words):
        acro = "".join(w[0] for w in words)
        # only keep an acronym that is not itself an ordinary English word:
        # "automated red teaming" -> "art" matched every paper about art
        if len(acro) >= 3 and acro not in COMMON_WORDS:
            out.add(acro)
    return {v.strip() for v in out if len(v) >= 3}


# Words so common in ML writing that an n-gram built only from them carries no
# signal. "language models" appears in 660 titles here; it selects nothing.
FILLER = {
  "language", "languages", "model", "models", "modeling", "modelling", "large",
  "small", "neural", "network", "networks", "deep", "machine", "learning",
  "artificial", "intelligence", "system", "systems", "data", "method", "methods",
  "approach", "approaches", "framework", "frameworks", "study", "studies", "new",
  "novel", "towards", "toward", "using", "via", "based", "analysis", "survey",
  "review", "understanding", "improving", "better", "more", "less", "human",
  "humans", "training", "trained", "test", "testing", "results", "case", "cases",
  "problem", "problems", "research", "work", "works", "paper", "papers", "post",
  "generative", "text", "multi", "self", "open", "general", "make", "making",
  "first", "second", "three", "some", "very", "high", "low", "long", "short",
}

# A gram containing any of these is grammar, not terminology: "at least",
# "rather than", "more than" were all matching as technical keywords.
FUNCTION_WORDS = {
  "at", "least", "most", "more", "than", "rather", "through", "different",
  "few", "many", "such", "been", "being", "other", "others", "only", "also",
  "both", "each", "into", "over", "under", "after", "before", "while", "when",
  "where", "which", "who", "whose", "there", "their", "them", "they", "will",
  "would", "should", "could", "may", "might", "must", "have", "has", "had",
  "not", "but", "or", "if", "so", "as", "by", "per", "up", "down", "out",
  "off", "about", "above", "across", "against", "among", "around", "between",
  "still", "yet", "even", "much", "well", "way", "ways", "lot", "really",
}


def mine(min_count, max_count=45):
    """n-grams that recur in safety titles and are not generic.

    Frequency alone is the wrong signal: the commonest n-grams are the emptiest.
    A term of art shows up often enough to matter and rarely enough to
    discriminate, so anything above max_count is dropped as boilerplate.
    """
    texts = []
    for w in load("openalex_works.json", []) or []:
        if w.get("title"):
            texts.append(w["title"].lower())
    for rec in (load("lesswrong_authors.json", {}) or {}).values():
        for p in rec.get("top_posts", []) + rec.get("recent_posts", []):
            if p.get("title"):
                texts.append(p["title"].lower())

    counts = Counter()
    for t in texts:
        toks = re.findall(r"[a-z][a-z-]+", t)
        for n in (2, 3):
            for i in range(len(toks) - n + 1):
                gram = " ".join(toks[i:i + n])
                if gram in TOO_GENERIC or len(gram) < 8:
                    continue
                toks_g = gram.split()
                if any(tok in ("the", "a", "an", "of", "for", "and", "to", "in", "on",
                               "with", "from", "that", "this", "is", "are", "we", "our",
                               "can", "do", "does", "how", "what", "why", "you", "it")
                       for tok in toks_g):
                    continue
                if all(tok in FILLER for tok in toks_g):
                    continue
                if any(tok in FUNCTION_WORDS for tok in toks_g):
                    continue
                counts[gram] += 1
    return {g: c for g, c in counts.items()
            if min_count <= c <= max_count}, len(texts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-count", type=int, default=3)
    args = ap.parse_args()

    vocab, by_theme = {}, defaultdict(set)
    for theme, terms in SEEDS.items():
        for t in terms:
            for v in variants(t):
                if v in TOO_GENERIC:
                    continue
                vocab[v] = {"term": v, "canonical": t, "theme": theme, "source": "seed"}
                by_theme[theme].add(v)

    mined, n_texts = mine(args.min_count)
    added = 0
    for gram, count in sorted(mined.items(), key=lambda kv: -kv[1]):
        if gram in vocab:
            continue
        vocab[gram] = {"term": gram, "canonical": gram, "theme": "mined",
                       "source": "corpus", "corpus_count": count}
        by_theme["mined"].add(gram)
        added += 1

    print(f"seed terms: {sum(len(v) for k, v in by_theme.items() if k != 'mined')} "
          f"(from {sum(len(t) for t in SEEDS.values())} canonical, expanded)")
    print(f"mined from {n_texts} titles at >={args.min_count} occurrences: {added}")
    print(f"total vocabulary: {len(vocab)}\n")
    for theme in list(SEEDS) + ["mined"]:
        print(f"  {len(by_theme[theme]):>5}  {theme}")
    print("\n  sample mined terms:")
    for g, c in sorted(mined.items(), key=lambda kv: -kv[1])[:14]:
        print(f"    {c:>4}x  {g}")

    save("keywords.json", {"themes": {k: sorted(v) for k, v in by_theme.items()},
                           "terms": vocab})


if __name__ == "__main__":
    main()
