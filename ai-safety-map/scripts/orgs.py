"""Classify an employer into a sector, and a sector into a 'side'.

The split the dataset is built around: people inside frontier / capabilities
labs, versus people in the safety ecosystem (non-profits, government bodies,
safety-focused ventures), versus academia. An org's sector is about who signs
the cheque, not what the person's team works on - a safety researcher at a
frontier lab is still inside a frontier lab, which is the distinction that
makes the comparison interesting.
"""
import re

# ordered: the first pattern that matches wins, so put specifics above generics
SECTOR_PATTERNS = [
    ("frontier_lab", r"\bAnthropic\b|\bOpenAI\b|Google\s*DeepMind|\bDeepMind\b|"
                     r"Google (Research|Brain)|\bGoogle LLC\b|\bGoogle Inc\b|"
                     r"Meta (AI|Platforms)|\bFAIR\b|Facebook AI|"
                     r"Microsoft Research|\bMicrosoft\b|\bxAI\b|Mistral AI|\bCohere\b|"
                     r"\bNVIDIA\b|Amazon( Web Services|\.com)?|\bApple Inc\b|"
                     r"ByteDance|Alibaba|Baidu|Tencent|Huawei|Inflection AI|"
                     r"Character\.?AI|Scale AI|Stability AI|Reka AI|Moonshot AI|"
                     r"Zhipu|DeepSeek|Mila.*Google"),
    ("government",   r"AI Security Institute|AI Safety Institute|\bAISI\b|\bCAISI\b|"
                     r"National Institute of Standards|\bNIST\b|"
                     r"Lawrence Livermore|Sandia National|Los Alamos|Oak Ridge|Argonne|"
                     r"Pacific Northwest National|Brookhaven|Idaho National|"
                     r"European Commission|Joint Research Centre|\bEU AI Office\b|"
                     r"Department of (Energy|Defense|Homeland)|\bDARPA\b|\bIARPA\b|"
                     r"Alan Turing Institute|National Research Council|CSIRO|"
                     r"Ministry of|Government of|\bNASA\b|\bNSA\b"),
    ("policy_org",   r"Centre for the Governance of AI|\bGovAI\b|RAND Corporation|\bRAND\b|"
                     r"Center for Security and Emerging Technology|\bCSET\b|"
                     r"Institute for AI Policy|\bIAPS\b|Center for a New American Security|"
                     r"Brookings|Carnegie Endowment|Chatham House|Future of Life|\bFLI\b|"
                     r"Centre for Long-Term Resilience|Simon Institute|Rethink Priorities|"
                     r"Epoch AI|Forethought|Legal Priorities|Institute for Law"),
    ("safety_org",   r"Machine Intelligence Research|\bMIRI\b|Redwood Research|"
                     r"Alignment Research Center|\bARC\b|Apollo Research|\bMETR\b|"
                     r"Center for AI Safety|\bCAIS\b|\bFAR AI\b|Fund for Alignment Research|"
                     r"EleutherAI|Eleuther AI|Conjecture|Timaeus|Apart Research|"
                     r"Transluce|Goodfire|LawZero|Orthogonal|\bOught\b|\bElicit\b|"
                     r"AI Futures Project|Constellation|\bMATS\b|ML Alignment|"
                     r"LASR Labs|\bLISA\b|London Initiative for AI Safety|ERA Fellowship|"
                     r"Center for Human-Compatible|\bCHAI\b|Berkeley Existential Risk|"
                     r"Future of Humanity Institute|Leverhulme Centre|Centre for the Study of Existential|"
                     r"AE Studio|Palisade Research|SaferAI|AI Standards Lab|Aligned AI|"
                     r"Truthful AI|\bCORAL\b|Astera|Krueger AI Safety|Cadenza|Simplex"),
    ("academia",     r"University|Universit(y|e|at|ä|é)|\bUniv\b|College|Institute of Technology|"
                     r"\bMIT\b|\bETH\b|\bEPFL\b|Polytechni|School of|Academy of Sciences|"
                     r"\bCNRS\b|\bINRIA\b|Max Planck|Tsinghua|Peking|Stanford|Berkeley|"
                     r"Harvard|Princeton|Yale|Cornell|Carnegie Mellon|Caltech|Oxford|Cambridge|"
                     r"Imperial|\bUCL\b|Edinburgh|Toronto|Montreal|\bMila\b|Vector Institute|"
                     r"Hospital|Medical Center|Faculty of"),
]
SECTOR_RE = [(name, re.compile(pat, re.I)) for name, pat in SECTOR_PATTERNS]

SIDE = {
    "frontier_lab": "frontier_capabilities",
    "government":   "safety_ecosystem",
    "policy_org":   "safety_ecosystem",
    "safety_org":   "safety_ecosystem",
    "academia":     "academia",
    "unknown":      "other",
}

SECTOR_LABEL = {
    "frontier_lab": "Frontier / capabilities lab",
    "government":   "Government body or national lab",
    "policy_org":   "Policy institute or think tank",
    "safety_org":   "Safety non-profit or safety venture",
    "academia":     "Academia",
    "unknown":      "No affiliation on indexed works",
}


# ---- the org registry from the two field-census sheets, matched first ----
_REG = None


def _registry():
    """alias -> org record, from data/orgs.json (built by build_orgs.py)."""
    global _REG
    if _REG is None:
        from common import load
        _REG = {}
        for o in load("orgs.json", []) or []:
            for a in o.get("aliases", []):
                key = _fold(a)
                if key and key not in _REG:
                    _REG[key] = o
    return _REG


def _fold(s):
    return re.sub(r"[^a-z0-9 ]+", " ", str(s or "").lower()).strip()


def registry_hit(name):
    """Match an institution string against a census org, or None.

    Exact fold first. Containment only for aliases long enough not to collide -
    'ACS' or 'Tilde' inside a longer institution name is noise, not a match.
    """
    reg = _registry()
    key = _fold(name)
    if not key:
        return None
    if key in reg:
        return reg[key]
    for alias, org in reg.items():
        if len(alias) >= 8 and re.search(r"\b" + re.escape(alias) + r"\b", key):
            return org
    return None


def sector_of(name):
    hit = registry_hit(name)
    if hit:
        return hit["sector"]

    if not name:
        return "unknown"
    for sector, rx in SECTOR_RE:
        if rx.search(name):
            return sector
    return "unknown"


def classify(institutions):
    """Pick one sector for a person from their institution list.

    A frontier-lab affiliation dominates: if someone publishes from both a
    university and Anthropic, where they sit for this comparison is Anthropic.
    """
    seen = [(sector_of(i), i) for i in institutions if i]
    for want in ("frontier_lab", "safety_org", "government", "policy_org", "academia"):
        for sector, inst in seen:
            if sector == want:
                return sector, inst
    return "unknown", (institutions[0] if institutions else "")
