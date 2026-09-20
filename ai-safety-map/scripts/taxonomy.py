"""A two-level taxonomy of AI-safety research.

Hand-authored rather than clustered. Unsupervised clustering over this corpus
kept producing incoherent groups ("Medicine, Real-World") because OpenAlex's
topic labels are too coarse and paper titles too varied; a curated taxonomy is
auditable, stable across rebuilds, and says what it means.

Eighteen areas, each holding 2-4 sub-areas. Twenty-five areas were too many to
read as separable clusters on a map, so closely-related ones are merged. A sub-area is a regex over a work's title and
its matched keywords. Works can belong to several sub-areas - a paper on
steering an evaluation-aware model is genuinely both - so assignment is
multi-label, and a person's area is where the weight of their work falls.
"""

TAXONOMY = {
 "Interpretability": {
   "blurb": "Reading and reverse-engineering what happens inside models",
   "subs": {
     "Circuits & attribution": r"circuit|activation patching|attribution patching|path patching|causal (trac|scrub)|logit attribution|induction head|attention head|edge attribution|relevance patching",
     "Sparse autoencoders & features": r"sparse autoencoder|\bSAE\b|dictionary learning|transcoder|crosscoder|feature (absorption|splitting|geometry)|monosemantic|polysemantic|superposition|matryoshka|linear representation|residual stream|logit lens|tuned lens",
     "Probing & representation reading": r"\bprob(e|es|ing)\b|linear probe|probing classifier|sparse probing|diagnostic probe|representation (similarity|convergence)|concept (vector|direction)",
     "Steering & model editing": r"activation steering|steering vector|activation addition|representation engineering|concept ablation|model diffing|activation difference|narrow finetuning|developmental interpretab|singular learning|grokking",
   }},
 "Chain of Thought & Reasoning": {
   "blurb": "Whether stated reasoning reflects actual computation",
   "subs": {
     "CoT faithfulness": r"chain.of.thought|\bCoT\b|faithful|unfaithful|reasoning trace|thought anchor|self-explanation",
     "CoT monitorability": r"monitorab|legib|obfuscat|encoded reasoning|steganograph|hidden reasoning|latent reasoning",
     "Introspection & verbalisation": r"introspect|verbaliz|verbalis|self-report|self-knowledge|out-of-context reasoning",
   }},
 "AI Control": {
   "blurb": "Getting useful work from models assumed to be scheming",
   "subs": {
     "Control protocols": r"control protocol|untrusted (monitor|model)|trusted (monitor|editing)|control evaluation|deferral|resampling protocol",
     "Sabotage & collusion": r"sabotage|collusion|coordinat(e|ion) (attack|failure)|SCHEME|covert",
     "Monitoring & escalation": r"monitor(ing)?|trace-based|escalation|human intervention|incident",
   }},
 "Scalable Oversight": {
   "blurb": "Supervising systems more capable than their supervisors",
   "subs": {
     "Debate & decomposition": r"\bdebate\b|factored cognition|decomposition|iterated amplification|recursive reward",
     "Weak-to-strong generalisation": r"weak.to.strong|amplification|easy.to.hard|generaliz\w* from weak",
     "Process supervision & judging": r"process supervision|outcome supervision|reward model|preference model|\bjudge\b|LLM-as-a-judge|annotat",
   }},
 "Evaluations": {
   "blurb": "Measuring what models can do, and whether the measurement holds",
   "subs": {
     "Dangerous capability evals": r"dangerous capab|capability evaluation|uplift|bioweapon|cyber(security)? eval|offensive capab|autonomy eval",
     "Capability elicitation": r"elicit|password.lock|sandbag|underelicit|best-of-n|scaffold",
     "Benchmark validity": r"benchmark|construct validity|contamination|saturat|measurement|psychometric|item response",
     "Evaluation awareness": r"evaluation.aware|eval.aware|test.aware|knows it is being|situational awareness|eval gaming|metagam|deployment gap",
   }},
 "Deception & Scheming": {
   "blurb": "Models pursuing goals they conceal",
   "subs": {
     "Deceptive alignment": r"deceptive alignment|scheming|treacherous|alignment faking|strategic deception|sleeper agent",
     "Lie & deception detection": r"lie detect|deception detect|honest|dishonest|truthful|hallucination detect",
     "Secret knowledge elicitation": r"secret knowledge|hidden knowledge|latent knowledge|\bELK\b|elicit.{0,12}knowledge",
   }},
 "Misalignment & Reward Hacking": {
   "blurb": "Misalignment arising from ordinary training",
   "subs": {
     "Reward hacking & specification gaming": r"reward hack|reward tamper|reward misspecif|specification gaming|goodhart|task gaming",
     "Goal misgeneralisation": r"goal misgeneral|inner (align|misalign)|mesa.optimi|objective misgeneral|out-of-distribution generaliz",
     "Emergent misalignment": r"emergent misalign|narrow misalign|convergent.{0,12}misalign|persona.{0,12}misalign",
     "Model organisms & data transmission": r"model organism|toy model of|synthetic misalign|subliminal|distillation.{0,15}(bias|transfer)|phantom transfer|data poisoning|backdoor",
   }},
 "Alignment Training": {
   "blurb": "Shaping behaviour and character through training",
   "subs": {
     "RLHF & preference optimisation": r"\bRLHF\b|\bRLAIF\b|\bDPO\b|reinforcement learning from human|preference optimi|policy optimi",
     "Sycophancy & reward model failure": r"sycophan|flatter|agreeab|reward model (error|failure|hack)|overoptimi",
     "Constitutional AI & harmlessness": r"constitutional|harmless|helpful.{0,12}harmless|principle-based|deliberative alignment",
     "Personas & model character": r"persona|character training|model character|assistant persona|identity",
   }},
 "Adversarial Robustness & Security": {
   "blurb": "Attacks on models and on the systems around them",
   "subs": {
     "Jailbreaks & red teaming": r"jailbreak|adversarial suffix|\bGCG\b|red.?team|attack success rate|harmful (prompt|request)",
     "Refusal & safety training": r"refusal|safety (training|fine.?tuning)|guardrail|safety filter|alignment tax|adversarial (robust|training|example)|certified|defen[cs]e",
     "Prompt injection & agent security": r"prompt injection|indirect injection|tool (poison|abuse)|instruction hierarchy|malicious fine.?tun|tamper|model stealing",
     "Attribution & provenance": r"attribution|provenance|watermark|agent identity|audit trail",
   }},
 "Unlearning & Capability Removal": {
   "blurb": "Removing knowledge or abilities after training",
   "subs": {
     "Machine unlearning": r"unlearn|forget(ting)?|knowledge removal|data deletion",
     "Filtering & data curation": r"data filter|pretraining filter|curat|deduplicat|differential data",
   }},
 "Multi-Agent Safety": {
   "blurb": "Risks that only appear between agents",
   "subs": {
     "Cooperation & commitment": r"cooperat|commitment|bargain|negotiat|game theor|schelling|joint",
     "Multi-agent failure modes": r"multi.?agent|collusion|delegation|constraint drift|emergent (behavior|behaviour).{0,12}agent",
   }},
 "AI Welfare & Moral Status": {
   "blurb": "Whether and how models matter morally",
   "subs": {
     "Model welfare & self-reports": r"model welfare|AI welfare|welfare (classifier|signal)|self-report|introspective report",
     "Consciousness & moral patienthood": r"consciousn|sentien|moral (status|patient|consideration)|digital mind|phenomenal",
   }},
 "Agent Foundations": {
   "blurb": "Formal accounts of agency and decision-making",
   "subs": {
     "Decision theory & embedded agency": r"decision theory|embedded agency|logical induct|newcomb|acausal|functional decision",
     "Corrigibility & shutdown": r"corrigib|shutdown|off.switch|interruptib|deferen",
     "Power-seeking & instrumental goals": r"power.seeking|instrumental convergence|resource acquisition|self-preservation|survival drive",
   }},
 "Forecasting & Timelines": {
   "blurb": "When capabilities arrive and how fast",
   "subs": {
     "Capability forecasting": r"forecast|timeline|scaling law|extrapolat|trend|prediction market",
     "Takeoff & R&D automation": r"takeoff|recursive self.improv|automat\w+ (AI )?R&D|intelligence explosion|AI research automation",
   }},
 "Governance & Policy": {
   "blurb": "Rules, institutions and the physical inputs to frontier AI",
   "subs": {
     "Compute governance": r"compute (governance|threshold|tracking|verification)|\bFLOP|datacenter|chip|hardware.enabled|export control|supply chain|semiconductor|smuggl",
     "International coordination": r"treaty|verification regime|inspection|arms control|non-proliferation|red line|international agreement|geopolit|US.China|deterrence",
     "Regulation & liability": r"regulat|liability|legislat|statut|\bEU AI Act\b|code of practice|compliance",
     "Institutions & state capacity": r"safety institute|\bAISI\b|agency|oversight body|congressional|public sector|procurement",
   }},
 "Safety Cases & Assurance": {
   "blurb": "Arguing a system is safe enough to deploy",
   "subs": {
     "Safety cases & frameworks": r"safety case|responsible scaling|preparedness framework|frontier safety|assurance|risk management framework",
     "Auditing & third-party access": r"audit|third.party|structured access|external (review|red team)|disclosure|incident report",
   }},
 "Societal Impact & Epistemics": {
   "blurb": "Effects on people, institutions and knowledge",
   "subs": {
     "Persuasion & manipulation": r"persuas|manipulat|influence operation|misinformation|propaganda",
     "Epistemics & human autonomy": r"epistemic|autonomy|dependence|deskilling|human agency|decision support",
     "Labour & economic effects": r"econom|labour|labor market|automation of work|productivity|inequality",
   }},
 "Existential Risk & Threat Models": {
   "blurb": "Whole-system arguments about catastrophe",
   "subs": {
     "Threat models & risk analysis": r"existential|catastroph|\bx-risk\b|extinction|loss of control|takeover|threat model",
     "Strategy & prioritisation": r"strategy|prioritis|prioritiz|theory of victory|research agenda|roadmap",
   }},
}


def flat():
    """(area, sub, pattern) triples."""
    for area, spec in TAXONOMY.items():
        for sub, pat in spec["subs"].items():
            yield area, sub, pat


def stats():
    subs = sum(len(v["subs"]) for v in TAXONOMY.values())
    return len(TAXONOMY), subs
