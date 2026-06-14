// The teaching content behind the Metrics guide (route /guide) and the info
// tooltips in the metric picker / dataset editor. Kept on the frontend (not in
// the backend MetricInfo) because it's prose: long explanations, worked
// examples, glossary terms, and external reading. The guide view merges this
// static content with the live MetricInfo from GET /api/metrics so it always
// reflects what's actually installed/available.

export interface GuideLink {
  label: string
  url: string
}

export interface MetricGuideEntry {
  /** Anchor id + the backend metric id (when one exists). */
  id: string
  name: string
  family: string
  /** Human-readable score range, e.g. "0 – 1 (binary)". */
  range: string
  /** One plain-language sentence — shown in the hover tooltip. */
  tooltip: string
  /** The long explanation, one entry per paragraph. */
  explanation: string[]
  /** How the number is computed, in words. */
  formula?: string
  /** A short worked example. */
  example?: string
  /** When to reach for it — and when not to. */
  whenToUse?: string
  /** Glossary slugs this metric leans on. */
  related?: string[]
  /** External reading. */
  links?: GuideLink[]
  /** True for guide-only concepts that aren't in the metric picker. */
  guideOnly?: boolean
}

export interface MetricGroup {
  family: string
  label: string
  blurb: string
  metrics: MetricGuideEntry[]
}

export interface GlossaryTerm {
  slug: string
  term: string
  definition: string
}

// --- the metric groups, in the same order the picker lists them -------------

export const METRIC_GROUPS: MetricGroup[] = [
  {
    family: 'lexical',
    label: 'Lexical',
    blurb:
      'Compare the surface words and characters of the output against a reference. Fast, ' +
      'transparent, and free — but blind to meaning, so a correct paraphrase can score low.',
    metrics: [
      {
        id: 'exact_match',
        name: 'Exact Match',
        family: 'lexical',
        range: '0 or 1 (binary)',
        tooltip:
          'Scores 1.0 only if the output equals the reference exactly, after lowercasing and trimming whitespace; otherwise 0.0.',
        explanation: [
          'Exact Match (EM) is the strictest reference-based metric. It asks a single yes/no question: after light normalization, does the output equal the gold reference?',
          "Because it's all-or-nothing, EM is perfect for closed-form tasks with one canonical answer — a capital city, a numeric result, a yes/no label — and useless for anything open-ended, where one extra word turns a correct answer into a 0.",
        ],
        formula:
          'score = 1.0 if normalize(prediction) == normalize(reference) else 0.0, where normalize() lowercases and collapses runs of whitespace. Punctuation is deliberately kept.',
        example:
          'prediction "Paris" vs reference "paris" → 1.0.  prediction "The capital is Paris." vs reference "Paris" → 0.0 (the extra words break the match).',
        whenToUse:
          'Use for short, closed answers and slot/label extraction. Avoid for summaries, explanations, or any free-form text — pair those with ROUGE, a semantic metric, or an LLM judge instead.',
        related: ['reference', 'normalization', 'lexical-metric'],
        links: [
          {
            label: 'SQuAD — where EM and token-F1 are the standard pair',
            url: 'https://rajpurkar.github.io/SQuAD-explorer/',
          },
        ],
      },
      {
        id: 'rouge1',
        name: 'ROUGE-1',
        family: 'lexical',
        range: '0 – 1',
        tooltip:
          'F1 of single-word (unigram) overlap between the output and the reference — how much vocabulary they share.',
        explanation: [
          'ROUGE is a family of recall-oriented overlap metrics first designed for evaluating summaries. ROUGE-1 counts how many individual words (unigrams) the output and the reference have in common.',
          'We report the F1 (harmonic mean of precision and recall), which is what most tooling shows: precision asks "how much of the output is in the reference?" and recall asks "how much of the reference did the output cover?"',
        ],
        formula:
          'Count clipped unigram overlap. precision = overlap / output-unigrams, recall = overlap / reference-unigrams, then F1 = 2·p·r / (p + r). "Clipped" means a repeated word only counts as often as it appears in the reference.',
        example:
          'output "the cat sat" vs reference "the cat sat down": 3 of 3 output words overlap (precision 1.0), 3 of 4 reference words covered (recall 0.75) → F1 ≈ 0.86.',
        whenToUse:
          'A cheap first signal for summaries and longer answers. Treat it as "did the right vocabulary show up?", not "is this correct?".',
        related: ['ngram', 'precision', 'recall', 'f1', 'lexical-metric'],
        links: [
          {
            label: 'Lin (2004) — the original ROUGE paper',
            url: 'https://aclanthology.org/W04-1013/',
          },
        ],
      },
      {
        id: 'rouge2',
        name: 'ROUGE-2',
        family: 'lexical',
        range: '0 – 1',
        tooltip:
          'F1 of word-pair (bigram) overlap — like ROUGE-1 but it also rewards getting consecutive words in the right order.',
        explanation: [
          'ROUGE-2 is ROUGE-1 over bigrams (adjacent word pairs) instead of single words. Because a bigram only matches when two words appear together in the same order, it is sensitive to phrasing, not just vocabulary.',
          'It is consistently stricter than ROUGE-1 and drops quickly on valid rewordings, so it is most useful as a complement: a high ROUGE-1 with a low ROUGE-2 suggests the right words in a different arrangement.',
        ],
        formula:
          'Identical to ROUGE-1 but counting bigrams (pairs of adjacent tokens) instead of unigrams.',
        example:
          'output "cat sat down" vs reference "the cat sat": bigrams {cat-sat, sat-down} vs {the-cat, cat-sat} share only "cat-sat" → modest F1.',
        whenToUse:
          'Read it alongside ROUGE-1 when word order and fluency matter. Expect near-zero scores on short or reordered text.',
        related: ['ngram', 'precision', 'recall', 'f1', 'lexical-metric'],
        links: [
          {
            label: 'Lin (2004) — the original ROUGE paper',
            url: 'https://aclanthology.org/W04-1013/',
          },
        ],
      },
      {
        id: 'rougeL',
        name: 'ROUGE-L',
        family: 'lexical',
        range: '0 – 1',
        tooltip:
          'F1 based on the longest common subsequence — rewards in-order overlap without requiring the words to be adjacent.',
        explanation: [
          'ROUGE-L is based on the longest common subsequence (LCS): the longest run of words appearing in both texts in the same order, but not necessarily next to each other.',
          'This captures sentence-level structure more flexibly than bigrams — inserting a word between two matched words does not break the match the way it does for ROUGE-2.',
        ],
        formula:
          'Let L be the LCS length of the output and reference token sequences. precision = L / output-length, recall = L / reference-length, F1 = 2·p·r / (p + r).',
        example:
          'output "the quick fox" vs reference "the slow quick brown fox": LCS = "the quick fox" (length 3) → high recall-leaning F1 even though words sit between the matches.',
        whenToUse:
          'A good single lexical number for longer text. Still lexical, so synonyms hurt it and high recall is not the same as conciseness.',
        related: ['ngram', 'lcs', 'precision', 'recall', 'f1', 'lexical-metric'],
        links: [
          {
            label: 'Lin (2004) — the original ROUGE paper',
            url: 'https://aclanthology.org/W04-1013/',
          },
        ],
      },
    ],
  },
  {
    family: 'classification',
    label: 'Classification',
    blurb:
      'When the task is really classification (sentiment, intent, yes/no, category), score it like one. ' +
      'Accuracy is per-case; precision, recall, and F1 are set-level summaries computed over all labels at once.',
    metrics: [
      {
        id: 'accuracy',
        name: 'Accuracy',
        family: 'classification',
        range: '0 – 1',
        tooltip: 'The fraction of cases whose predicted label exactly matches the true label.',
        explanation: [
          'Accuracy is the headline "how often is it right?" number: the share of cases where the predicted label matches the reference label.',
          'It is intuitive but can be badly misleading on imbalanced data — if 95% of cases are one class, a model that always guesses that class scores 95% while learning nothing. That is why precision, recall, and F1 sit next to it.',
        ],
        formula: 'accuracy = correct predictions / total cases.',
        example:
          'On 100 labelled cases where 90 predictions match the reference label → accuracy = 0.90.',
        whenToUse:
          'Fine as a quick read on balanced datasets. On skewed data, trust the macro precision/recall/F1 and the confusion matrix instead.',
        related: ['classification', 'reference', 'confusion-matrix'],
        links: [
          {
            label: 'scikit-learn — classification metrics',
            url: 'https://scikit-learn.org/stable/modules/model_evaluation.html#classification-metrics',
          },
        ],
      },
      {
        id: 'precision',
        name: 'Precision (macro)',
        family: 'classification',
        range: '0 – 1',
        tooltip:
          'Of the cases the model assigned to a class, how many were actually that class — averaged over classes. Penalizes false alarms.',
        explanation: [
          'Precision answers: of everything the model labelled as class X, what fraction really was class X? It penalizes false positives (false alarms).',
          'Macro precision computes precision separately for each class and then averages those numbers with equal weight, so a rare class counts as much as a common one. It is a set-level metric — there is no meaningful per-case precision, so it appears as a summary card, not a results-table column.',
        ],
        formula:
          'Per class: precision = TP / (TP + FP). Macro: the unweighted mean of the per-class precisions.',
        example:
          'The model labels 10 cases "spam"; 8 truly are → precision for "spam" = 0.80. Average that with the other classes for the macro value.',
        whenToUse:
          'Watch precision when a wrong positive is expensive (flagging a good email as spam, a false fraud alert).',
        related: ['precision', 'recall', 'f1', 'macro-average', 'confusion-matrix'],
        links: [
          {
            label: 'Wikipedia — precision and recall',
            url: 'https://en.wikipedia.org/wiki/Precision_and_recall',
          },
        ],
      },
      {
        id: 'recall',
        name: 'Recall (macro)',
        family: 'classification',
        range: '0 – 1',
        tooltip:
          'Of the cases that truly belong to a class, how many the model caught — averaged over classes. Penalizes misses.',
        explanation: [
          'Recall answers: of all the cases that really are class X, what fraction did the model catch? It penalizes false negatives (misses).',
          'Precision and recall trade off against each other: a model can look very precise by only flagging the cases it is sure about, at the cost of missing many (low recall). Macro recall averages the per-class recalls equally.',
        ],
        formula:
          'Per class: recall = TP / (TP + FN). Macro: the unweighted mean of the per-class recalls.',
        example:
          'There are 20 true "fraud" cases; the model catches 15 → recall for "fraud" = 0.75.',
        whenToUse:
          'Watch recall when a miss is expensive (a missed disease diagnosis, undetected fraud).',
        related: ['precision', 'recall', 'f1', 'macro-average', 'confusion-matrix'],
        links: [
          {
            label: 'Wikipedia — precision and recall',
            url: 'https://en.wikipedia.org/wiki/Precision_and_recall',
          },
        ],
      },
      {
        id: 'f1',
        name: 'F1 (macro)',
        family: 'classification',
        range: '0 – 1',
        tooltip:
          'The harmonic mean of precision and recall — a single number that is only high when both are high.',
        explanation: [
          'F1 is the harmonic mean of precision and recall. Unlike a plain average, the harmonic mean is dragged down by the smaller of the two, so F1 is only high when precision and recall are both high.',
          'Macro F1 averages the per-class F1 scores equally, making it the go-to single number for imbalanced multi-class problems.',
        ],
        formula: 'F1 = 2 · precision · recall / (precision + recall), then averaged over classes (macro).',
        example:
          'precision 0.8, recall 0.5 → F1 = 2·0.8·0.5 / (0.8 + 0.5) ≈ 0.62 (closer to the worse number, 0.5, than a plain average would be).',
        whenToUse:
          'The default summary number when you care about precision and recall together and the classes are uneven.',
        related: ['f1', 'precision', 'recall', 'macro-average', 'confusion-matrix'],
        links: [
          {
            label: 'scikit-learn — precision, recall and F-measures',
            url: 'https://scikit-learn.org/stable/modules/model_evaluation.html#precision-recall-f-measure-metrics',
          },
        ],
      },
    ],
  },
  {
    family: 'semantic',
    label: 'Semantic',
    blurb:
      'Compare meaning rather than words by turning text into embedding vectors. A correct paraphrase ' +
      'scores high even with no shared words — at the cost of heavier ML libraries and the risk of rewarding fluent-but-wrong text.',
    metrics: [
      {
        id: 'cosine',
        name: 'Cosine similarity',
        family: 'semantic',
        range: '0 – 1',
        tooltip:
          'Embeds both texts as sentence vectors and measures the cosine of the angle between them — high means similar overall meaning.',
        explanation: [
          'Cosine similarity turns the output and the reference into single sentence-embedding vectors (here via the all-MiniLM-L6-v2 model) and measures the cosine of the angle between them. Because it compares direction, not exact words, it rewards correct paraphrases that share little vocabulary.',
          'It is a coarse, whole-sentence signal — quick and cheap, but it cannot tell you which part diverged, and fluent text on the right topic can sit close even when it is factually wrong.',
        ],
        formula:
          'cosine = (a · b) / (‖a‖ · ‖b‖) for embedding vectors a and b. With normalized embeddings this is just the dot product; the result is clamped to [0, 1].',
        example:
          '"The film was fantastic." vs "I really enjoyed the movie." share almost no words but score high, because their embeddings point in nearly the same direction.',
        whenToUse:
          'A fast "are these two answers about the same thing?" check. For a sharper, token-level view use BERTScore.',
        related: ['embedding', 'cosine-similarity', 'semantic-metric', 'reference'],
        links: [
          { label: 'Sentence-Transformers (SBERT) documentation', url: 'https://www.sbert.net/' },
        ],
      },
      {
        id: 'bertscore',
        name: 'BERTScore',
        family: 'semantic',
        range: '0 – 1 (rescaled)',
        tooltip:
          'Matches each output token to its most similar reference token using contextual embeddings, then reports an F1.',
        explanation: [
          'BERTScore compares texts at the token level using contextual embeddings (from BERT): each token is matched to its most similar token on the other side, and precision/recall/F1 are computed from those soft matches. We report the F1.',
          'Because the embeddings are contextual, the same word in different sentences gets different vectors, so BERTScore is finer-grained than whole-sentence cosine. The scores are rescaled against a baseline so they spread into a readable range instead of clustering near 1.',
        ],
        formula:
          'Greedily match each output token to the most cosine-similar reference token (and vice versa) → precision and recall → F1, then rescale with an empirical baseline.',
        example:
          'A correct paraphrase with zero exact word overlap can still score highly, because each token finds a close contextual match on the other side.',
        whenToUse:
          'When you want partial credit for paraphrases at a finer grain than cosine. Remember: semantic closeness is not correctness — fluent, on-topic, but factually wrong text can still score high.',
        related: ['embedding', 'contextual-embedding', 'f1', 'semantic-metric', 'reference'],
        links: [
          { label: 'Zhang et al. (2020) — BERTScore', url: 'https://arxiv.org/abs/1904.09675' },
        ],
      },
    ],
  },
  {
    family: 'model_judge',
    label: 'LLM judge',
    blurb:
      'Have a strong model grade each output against a rubric and explain itself. The most practical ' +
      'approach for open-ended generation — and the closest to human judgment — but it carries its own biases. ' +
      'Pick the judge model (Claude, GPT, or Gemini) on the Run page; it needs an API key for that provider.',
    metrics: [
      {
        id: 'llm_judge',
        name: 'LLM-as-a-judge',
        family: 'model_judge',
        range: '0 – 1 (from a 1–5 grade)',
        tooltip:
          'A strong model (Claude, GPT, or Gemini) grades the answer 1–5 against your rubric and writes a short rationale; the grade is normalized to 0–1.',
        explanation: [
          'LLM-as-a-judge asks a strong model to grade each output against a rubric you write, returning a 1–5 score plus a one- or two-sentence rationale. The score is normalized to 0–1 for display, and the rationale is shown per case so you can see why.',
          'It is the most practical metric for open-ended generation and the closest automated proxy for human judgment — but it inherits model biases: it can favor longer answers (verbosity bias), a particular option order (position bias), or its own style (self-preference). Spot-check it against human labels before trusting it at scale.',
        ],
        formula:
          'The judge returns {"score": 1–5, "rationale": "..."}; the displayed value is (score − 1) / 4, mapping 1→0.0 and 5→1.0.',
        example:
          'Rubric "Rate correctness, relevance, and clarity." A complete, correct, well-written answer earns a 5 → 1.0; a partly-correct answer might earn a 3 → 0.5, with a rationale explaining the gap.',
        whenToUse:
          'Reach for it when there is no single gold answer — summaries, explanations, open Q&A, tone. Always read the rationale, and calibrate against human judgments on a sample.',
        related: ['llm-as-judge', 'rubric', 'rationale', 'self-preference-bias'],
        links: [
          {
            label: 'Zheng et al. (2023) — Judging LLM-as-a-Judge (MT-Bench)',
            url: 'https://arxiv.org/abs/2306.05685',
          },
        ],
      },
    ],
  },
  {
    family: 'rag',
    label: 'RAG',
    blurb:
      'For retrieval-augmented generation, separate the failure modes. The "RAG triad" — context relevancy, ' +
      'faithfulness, and answer relevancy — tells you whether a problem is in retrieval or in generation. ' +
      'All call the judge model you pick on the Run page and need that provider\'s API key.',
    metrics: [
      {
        id: 'faithfulness',
        name: 'Faithfulness',
        family: 'rag',
        range: '0 – 1',
        tooltip:
          'Checks whether every claim in the answer is supported by the retrieved context — i.e. did the model hallucinate?',
        explanation: [
          'Faithfulness measures grounding: is every claim in the answer actually supported by the retrieved context? A judge model reads the context and the answer and penalizes anything stated that the context does not back up.',
          'It is a generation-quality signal — low faithfulness means the model is hallucinating, inventing details the sources never provided. A faithful answer can still be unhelpful, so always read it next to answer relevancy.',
        ],
        formula:
          'A judge grades how well the answer is grounded in the context (1–5), normalized to 0–1. Requires a Context field on the case.',
        example:
          'Context says "The store opens at 9am." Answer "It opens at 9am and closes at 6pm." → penalized: the 6pm closing time is unsupported (a hallucination).',
        whenToUse:
          'The first thing to check in a RAG pipeline when answers look plausible but may be invented. Pair with answer relevancy and context relevancy.',
        related: ['rag', 'rag-triad', 'hallucination', 'grounding', 'context'],
        links: [{ label: 'Ragas — RAG evaluation framework', url: 'https://docs.ragas.io/' }],
      },
      {
        id: 'answer_relevancy',
        name: 'Answer relevancy',
        family: 'rag',
        range: '0 – 1',
        tooltip: 'Checks whether the answer actually addresses the question that was asked.',
        explanation: [
          'Answer relevancy measures whether the answer directly and completely addresses the question. A judge penalizes evasive, partial, or off-topic responses.',
          'It is independent of correctness and grounding: an answer can be on-topic but wrong, or faithful to the context but unhelpful. Reading it next to faithfulness separates "is it grounded?" from "does it answer the question?"',
        ],
        formula: 'A judge grades how well the answer addresses the question (1–5), normalized to 0–1.',
        example:
          'Question "What time does the store open?" Answer "Our stores have great hours!" → low relevancy: on-topic but it never gives the time.',
        whenToUse: 'Use whenever answers must actually satisfy the user\'s question, RAG or not.',
        related: ['rag', 'rag-triad', 'input'],
        links: [{ label: 'Ragas — RAG evaluation framework', url: 'https://docs.ragas.io/' }],
      },
      {
        id: 'context_relevancy',
        name: 'Context relevancy',
        family: 'rag',
        range: '0 – 1',
        tooltip:
          'Checks whether the retriever fetched context that is actually relevant to the question — a retrieval-quality signal.',
        explanation: [
          'Context relevancy grades the retriever, not the answer: does the retrieved context contain the information needed to answer the question? A judge penalizes off-topic context or context missing the key facts.',
          'This is what localizes a RAG failure. If context relevancy is low, the problem is retrieval — the generator never had the facts. If context relevancy is high but faithfulness or answer relevancy is low, the problem is generation.',
        ],
        formula:
          'A judge grades how relevant the retrieved context is to the question (1–5), normalized to 0–1. Requires a Context field on the case.',
        example:
          'Question about store hours, but the retrieved context is the return policy → low context relevancy, pointing at the retriever.',
        whenToUse:
          'Run it with faithfulness and answer relevancy (the RAG triad) to tell retrieval problems apart from generation problems.',
        related: ['rag', 'rag-triad', 'context', 'input'],
        links: [{ label: 'Ragas — RAG evaluation framework', url: 'https://docs.ragas.io/' }],
      },
    ],
  },
  {
    family: 'operational',
    label: 'Operational',
    blurb:
      'Quality is only half the picture. These are recorded automatically when you generate predictions ' +
      'live, and shown on the results page — because an answer that is too slow or too expensive is not a good answer.',
    metrics: [
      {
        id: 'providers',
        name: 'Providers & API keys',
        family: 'operational',
        range: 'Anthropic · OpenAI · Gemini',
        guideOnly: true,
        tooltip:
          'Generation and the judge each pick a provider+model (Claude, GPT, or Gemini). Add that provider\'s key on the Settings page; keys live in your browser and never persist on the server.',
        explanation: [
          'The app talks to three providers — Anthropic (Claude), OpenAI (GPT), and Google (Gemini). The model id tells the backend which provider to call, so you choose a provider just by choosing a model.',
          'Two roles pick a model independently: live generation (the Model panel on the Run page) and the LLM-judge / RAG metrics (the "Judge model" picker that appears when you select one). You can generate with one provider and grade with another — e.g. generate with GPT, judge with Claude.',
          'Keys come from two places. The backend reads them from its own .env as a default; the Settings page lets you paste a key per provider, stored in your browser and sent with each run. A browser key wins over the env key and unlocks that provider without restarting the backend. Because the keys live in localStorage, this is meant for local use, not a shared machine.',
          'A model whose provider has no key is greyed out in the pickers with a "needs key" note. Pricing differs by provider and model, and the cost estimate uses the selected judge model\'s rates.',
        ],
        whenToUse:
          'Set a key once on the Settings page, then mix and match models per run. Cheaper models (e.g. GPT-4o mini, Gemini Flash, Claude Haiku) are good for quick passes; reserve the strongest models for the final judge.',
        related: ['llm-as-judge', 'tokens', 'cost'],
      },
      {
        id: 'cost-estimate',
        name: 'What costs money',
        family: 'operational',
        range: 'US dollars · projected before a run',
        guideOnly: true,
        tooltip:
          'Only LLM-judge and RAG metrics cost money — they call the judge model once per case. Lexical, classification, and semantic metrics run locally and are free.',
        explanation: [
          'In the cost estimate, "cost" means money paid to the model provider for tokens — and only metrics that actually call a provider API spend tokens. Everything else runs on the backend itself, so it is $0 in API terms (it still uses your CPU, and embedding metrics download a model once).',
          'Metrics that cost money ask a model to grade each case, one API request per case: LLM-as-a-judge, and the RAG triad — Faithfulness, Answer relevancy, and Context relevancy. These are the metrics marked "needs key to run", and the estimator counts all four.',
          'Metrics that are free compute locally with no API call: the lexical metrics (Exact Match, ROUGE-1/2/L) compare surface words; the classification metrics (Accuracy, Precision, Recall, F1) run in scikit-learn; and the semantic metrics (Cosine similarity, BERTScore) run a local embedding model. That is why the estimate reads "this run is free" until you select a judge or RAG metric.',
          'Two separate actions in the app are billable. Scoring with judge metrics is what the cost estimate projects (it assumes predictions already exist). Live generation — producing predictions from a model with the generate button in the Model panel — also calls the provider and costs tokens, but it is a separate step the estimator does not cover.',
          'Rule of thumb: if a step asks a model to produce or grade text, it costs tokens; if it just compares strings or numbers you already have, it is free.',
        ],
        whenToUse:
          'Read it before you run: reach for judge/RAG metrics when the task is open-ended enough to need them, and lean on the free lexical/classification/semantic metrics when a reference or label is enough. The estimate shows an expected cost and a worst-case ceiling so a run never surprises you.',
        related: ['cost', 'tokens', 'operational', 'llm-as-judge', 'rag-triad'],
      },
      {
        id: 'latency',
        name: 'Latency',
        family: 'operational',
        range: 'milliseconds (lower is better)',
        guideOnly: true,
        tooltip: 'How long the model took to produce an output, in milliseconds.',
        explanation: [
          'Latency is wall-clock time per generation. The results page reports p50 (median) and p95 latency: p50 is the typical experience, while p95 captures the slow tail that users actually notice.',
          'Watch the gap between them — a low p50 with a high p95 means most calls are fast but some stall, which can matter more than the average.',
        ],
        whenToUse:
          'Track it whenever responsiveness matters. Compare p95 across models or prompts, not just the average.',
        related: ['operational'],
      },
      {
        id: 'tokens',
        name: 'Tokens',
        family: 'operational',
        range: 'count (lower is cheaper)',
        guideOnly: true,
        tooltip:
          'The number of input and output tokens — the units models read and write, and the basis for cost.',
        explanation: [
          'Tokens are the chunks of text a model processes — roughly ¾ of a word in English. Inputs (your prompt + context) and outputs (the generated answer) are counted separately, and together they drive both latency and cost.',
          'Long contexts and verbose answers inflate token counts quickly, so they are worth watching alongside quality.',
        ],
        whenToUse: 'Use token counts to understand and control cost and latency, especially with long RAG contexts.',
        related: ['operational'],
      },
      {
        id: 'cost',
        name: 'Cost',
        family: 'operational',
        range: 'US dollars (lower is better)',
        guideOnly: true,
        tooltip: 'The estimated dollar cost of a run, derived from input and output token counts.',
        explanation: [
          'Cost is estimated from token usage and the model\'s per-token pricing (input and output tokens are usually priced differently). It lets you weigh a quality gain against what it costs to get.',
          'A small quality improvement that doubles cost may not be worth it — and a cheaper model that is nearly as good often wins in production.',
        ],
        whenToUse: 'Read cost next to your quality metrics to find the best quality-per-dollar trade-off.',
        related: ['operational', 'tokens'],
      },
    ],
  },
  {
    family: 'dimred',
    label: 'Dimensionality reduction',
    blurb:
      'Embeddings live in hundreds of dimensions — too many to plot. Dimensionality reduction ' +
      'squashes them to 2-D so structure becomes visible. Each algorithm trades off differently; ' +
      'the Explorer lets you run several on the same data and compare. (Used by the Explorer, not the metric picker.)',
    metrics: [
      {
        id: 'pca',
        name: 'PCA',
        family: 'dimred',
        range: 'projects to 2-D · linear',
        guideOnly: true,
        tooltip:
          'Rotates the data onto its directions of greatest variance and keeps the top two — a fast, deterministic linear projection.',
        explanation: [
          'Principal Component Analysis finds the orthogonal directions along which the data varies most (the principal components) and projects onto the top two. It is linear, deterministic, and fast — the same data always yields the same picture.',
          'Because the axes are real directions of variance, distances and global layout are meaningful, and the "variance explained" tells you how faithful the 2-D view is. The trade-off: a single flat projection can blur clusters that are separated only along curved, nonlinear directions.',
        ],
        formula:
          'Center the data, take the eigenvectors of its covariance matrix (the components), and project onto the top two. Variance explained = the share of total spread those two axes capture.',
        example:
          'On the 64-D digits dataset, PCA\'s first two components pull some digits apart but leave others overlapping — linear axes can only do so much.',
        whenToUse:
          'A fast, reproducible first look, and the only one whose axes and distances you can read literally. Reach for t-SNE/UMAP when clusters overlap.',
        related: ['dimensionality-reduction', 'variance-explained', 'embedding'],
        links: [
          {
            label: 'scikit-learn — decomposition (PCA)',
            url: 'https://scikit-learn.org/stable/modules/decomposition.html#pca',
          },
        ],
      },
      {
        id: 'tsne',
        name: 't-SNE',
        family: 'dimred',
        range: 'projects to 2-D · nonlinear',
        guideOnly: true,
        tooltip:
          'Places similar points near each other so clusters pop out — but cluster sizes and the distances between clusters are not meaningful.',
        explanation: [
          't-distributed Stochastic Neighbor Embedding is nonlinear: it models how likely each point is to be a neighbor of each other in high-D, then arranges points in 2-D to match those neighbor probabilities. The result is tight, well-separated clusters of similar items.',
          'The catch — and the thing most people misread — is that only local neighborhoods are faithful. Cluster sizes, the empty space between clusters, and global distances are artifacts of the optimization, not signal. It is also stochastic and slower, so we fix a seed for reproducibility.',
        ],
        formula:
          'Minimize the KL divergence between neighbor-probability distributions in high-D and in 2-D. Perplexity sets the effective neighborhood size and must stay below the number of points.',
        example:
          'On digits, t-SNE forms ten clean blobs — great for seeing the clusters, but the gap between the "3" and "8" blobs does not measure how different those digits are.',
        whenToUse:
          'When you want clusters to jump out. Try a few perplexities; never interpret inter-cluster distance or cluster size.',
        related: ['dimensionality-reduction', 'perplexity', 'manifold', 'embedding'],
        links: [
          { label: 'Distill — How to Use t-SNE Effectively', url: 'https://distill.pub/2016/misread-tsne/' },
          {
            label: 'scikit-learn — manifold learning (t-SNE)',
            url: 'https://scikit-learn.org/stable/modules/manifold.html#t-sne',
          },
        ],
      },
      {
        id: 'umap',
        name: 'UMAP',
        family: 'dimred',
        range: 'projects to 2-D · nonlinear',
        guideOnly: true,
        tooltip:
          'Like t-SNE, but balances local and global structure and runs faster; tune n_neighbors and min_dist.',
        explanation: [
          'Uniform Manifold Approximation and Projection builds a fuzzy nearest-neighbor graph of the data and then optimizes a 2-D layout that preserves it. Compared with t-SNE it usually keeps more of the global structure (relative cluster positions are a bit more trustworthy) and runs faster.',
          'Two knobs shape it: n_neighbors trades local detail (low) against global structure (high), and min_dist controls how tightly points may pack. Like t-SNE it is nonlinear and seed-dependent, so we fix the seed.',
        ],
        formula:
          'Build a weighted k-nearest-neighbor graph (size set by n_neighbors), then optimize a low-D embedding to match it; min_dist sets the minimum spacing between points in 2-D.',
        example:
          'On digits, UMAP separates the ten classes like t-SNE but tends to place related digits nearer each other, hinting at global relationships t-SNE discards.',
        whenToUse:
          'A strong default for exploring embeddings — fast, and friendlier to global structure than t-SNE. Still treat fine distances with caution.',
        related: ['dimensionality-reduction', 'n-neighbors', 'min-dist', 'manifold', 'embedding'],
        links: [{ label: 'UMAP documentation', url: 'https://umap-learn.readthedocs.io/' }],
      },
    ],
  },
]

// --- glossary ---------------------------------------------------------------

export const GLOSSARY: GlossaryTerm[] = [
  {
    slug: 'input',
    term: 'Input (prompt)',
    definition: 'The question or instruction given to the model for a case.',
  },
  {
    slug: 'prediction',
    term: 'Prediction',
    definition:
      "The model's actual output for a case. Required to score anything — cases without one are skipped.",
  },
  {
    slug: 'reference',
    term: 'Reference (gold answer)',
    definition:
      'The known-correct answer for a case. Optional, but required by reference-based metrics (Exact Match, ROUGE, the classification metrics, cosine, BERTScore). Without it, only reference-free metrics (LLM-judge, RAG) can run.',
  },
  {
    slug: 'context',
    term: 'Context',
    definition:
      'Retrieved documents or passages supplied to the model in a RAG setup. Required by the faithfulness and context-relevancy metrics.',
  },
  {
    slug: 'normalization',
    term: 'Normalization',
    definition:
      "Light cleanup before comparing two strings — here, lowercasing and collapsing whitespace — so trivial differences don't count as errors.",
  },
  {
    slug: 'lexical-metric',
    term: 'Lexical metric',
    definition:
      'A metric that compares surface words or characters (Exact Match, ROUGE). Fast and transparent but blind to synonyms and paraphrase.',
  },
  {
    slug: 'semantic-metric',
    term: 'Semantic metric',
    definition:
      'A metric that compares meaning via embeddings (cosine, BERTScore), so it rewards correct paraphrases instead of demanding identical wording.',
  },
  {
    slug: 'ngram',
    term: 'N-gram',
    definition:
      'A run of N consecutive tokens. A unigram is one word, a bigram is a pair of adjacent words. ROUGE-1 uses unigrams; ROUGE-2 uses bigrams.',
  },
  {
    slug: 'lcs',
    term: 'Longest common subsequence (LCS)',
    definition:
      'The longest sequence of tokens that appears in both texts in the same order, but not necessarily adjacent. The basis of ROUGE-L.',
  },
  {
    slug: 'precision',
    term: 'Precision',
    definition:
      'Of the items flagged as positive, the fraction that truly were positive. Penalizes false alarms (false positives).',
  },
  {
    slug: 'recall',
    term: 'Recall',
    definition:
      'Of the items that truly were positive, the fraction that were caught. Penalizes misses (false negatives).',
  },
  {
    slug: 'f1',
    term: 'F1 score',
    definition:
      'The harmonic mean of precision and recall. Only high when both are high; dragged toward the smaller of the two.',
  },
  {
    slug: 'macro-average',
    term: 'Macro-average',
    definition:
      'Compute a metric separately for each class, then average the classes with equal weight — so rare classes count as much as common ones.',
  },
  {
    slug: 'confusion-matrix',
    term: 'Confusion matrix',
    definition:
      'A table of true labels (rows) against predicted labels (columns). The diagonal is correct predictions; off-diagonal cells show exactly what gets confused with what.',
  },
  {
    slug: 'classification',
    term: 'Classification',
    definition:
      'A task whose output is one of a fixed set of labels (e.g. sentiment, intent, yes/no). Scored with accuracy, precision, recall, and F1.',
  },
  {
    slug: 'embedding',
    term: 'Embedding',
    definition:
      'A numeric vector that represents a piece of text so that similar meanings sit close together in vector space.',
  },
  {
    slug: 'contextual-embedding',
    term: 'Contextual embedding',
    definition:
      "A word vector that depends on the surrounding sentence, so \"bank\" gets a different vector in \"river bank\" than in \"savings bank\". Used by BERTScore.",
  },
  {
    slug: 'cosine-similarity',
    term: 'Cosine similarity',
    definition:
      'The cosine of the angle between two vectors: 1 means they point the same way (similar), 0 means unrelated. Used to compare embeddings.',
  },
  {
    slug: 'llm-as-judge',
    term: 'LLM-as-a-judge',
    definition:
      'Using a strong model to grade outputs against a rubric, optionally with a reference. Flexible for open-ended tasks, but it carries biases.',
  },
  {
    slug: 'rubric',
    term: 'Rubric',
    definition:
      "The grading criteria handed to a judge model — e.g. \"rate correctness, relevance, and clarity from 1 to 5\".",
  },
  {
    slug: 'rationale',
    term: 'Rationale',
    definition: "The judge's written explanation for the score it assigned, shown per case in the results.",
  },
  {
    slug: 'self-preference-bias',
    term: 'Judge biases',
    definition:
      'Known tendencies of judge models to favor longer answers (verbosity bias), a particular option order (position bias), or their own style (self-preference). Reasons to spot-check against humans.',
  },
  {
    slug: 'rag',
    term: 'RAG (retrieval-augmented generation)',
    definition:
      'A pattern where relevant documents are retrieved first, then the model answers using them. Evaluated with the RAG triad.',
  },
  {
    slug: 'rag-triad',
    term: 'RAG triad',
    definition:
      'Three metrics that localize RAG failures: context relevancy (retrieval), faithfulness (grounding), and answer relevancy (helpfulness).',
  },
  {
    slug: 'hallucination',
    term: 'Hallucination',
    definition: 'A confident claim that is not supported by the provided context (or by fact).',
  },
  {
    slug: 'grounding',
    term: 'Grounding',
    definition: 'Tying every claim in an answer back to the source context. Measured by faithfulness.',
  },
  {
    slug: 'operational',
    term: 'Operational metrics',
    definition:
      'Latency, token counts, and cost — the production realities. A high-quality answer that is too slow or too expensive still fails.',
  },
  {
    slug: 'dimensionality-reduction',
    term: 'Dimensionality reduction',
    definition:
      'Squashing high-dimensional vectors down to a few dimensions (here 2-D) so they can be plotted, while trying to keep the structure. Linear (PCA) or nonlinear (t-SNE, UMAP).',
  },
  {
    slug: 'pca',
    term: 'PCA',
    definition:
      'Principal Component Analysis — a linear method that projects data onto the orthogonal directions of greatest variance. Fast, deterministic, and its distances are meaningful.',
  },
  {
    slug: 'tsne',
    term: 't-SNE',
    definition:
      'A nonlinear method that preserves local neighborhoods, producing tight clusters. Cluster sizes and the distances between clusters are not meaningful.',
  },
  {
    slug: 'umap',
    term: 'UMAP',
    definition:
      'A nonlinear method that preserves local and some global structure, usually faster than t-SNE. Tuned with n_neighbors and min_dist.',
  },
  {
    slug: 'perplexity',
    term: 'Perplexity (t-SNE)',
    definition:
      "t-SNE's main knob — roughly how many neighbors each point balances. Lower makes more, tighter local clusters; it must stay below the number of points.",
  },
  {
    slug: 'n-neighbors',
    term: 'n_neighbors (UMAP)',
    definition:
      "UMAP's local-vs-global knob. Small values capture fine local detail; large values emphasize the overall global shape.",
  },
  {
    slug: 'min-dist',
    term: 'min_dist (UMAP)',
    definition:
      "UMAP's packing knob — the minimum spacing allowed between points in 2-D. Low clumps points tightly; high spreads them more evenly.",
  },
  {
    slug: 'variance-explained',
    term: 'Variance explained',
    definition:
      'The fraction of the data\'s total spread captured by a PCA component. High values for the first two components mean the 2-D PCA view is faithful.',
  },
  {
    slug: 'manifold',
    term: 'Manifold',
    definition:
      "The idea that high-dimensional data often lies on a lower-dimensional curved surface; nonlinear methods (t-SNE, UMAP) try to 'unroll' it onto the plane.",
  },
]

// --- external reading -------------------------------------------------------

export const FURTHER_READING: GuideLink[] = [
  { label: 'Lin (2004) — ROUGE: A Package for Automatic Evaluation of Summaries', url: 'https://aclanthology.org/W04-1013/' },
  { label: 'Zhang et al. (2020) — BERTScore: Evaluating Text Generation with BERT', url: 'https://arxiv.org/abs/1904.09675' },
  { label: 'Zheng et al. (2023) — Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena', url: 'https://arxiv.org/abs/2306.05685' },
  { label: 'Ragas — Evaluation framework for RAG pipelines', url: 'https://docs.ragas.io/' },
  { label: 'Sentence-Transformers (SBERT) — sentence & text embeddings', url: 'https://www.sbert.net/' },
  { label: 'scikit-learn — model evaluation & classification metrics', url: 'https://scikit-learn.org/stable/modules/model_evaluation.html' },
  { label: 'SQuAD — reading-comprehension benchmark (Exact Match & token-F1)', url: 'https://rajpurkar.github.io/SQuAD-explorer/' },
  { label: 'Distill — How to Use t-SNE Effectively', url: 'https://distill.pub/2016/misread-tsne/' },
  { label: 'UMAP — documentation & how it works', url: 'https://umap-learn.readthedocs.io/' },
  { label: 'scikit-learn — manifold learning & decomposition (t-SNE, PCA)', url: 'https://scikit-learn.org/stable/modules/manifold.html' },
]

// --- lookup helpers ---------------------------------------------------------

const ENTRY_BY_ID: Record<string, MetricGuideEntry> = Object.fromEntries(
  METRIC_GROUPS.flatMap((g) => g.metrics).map((m) => [m.id, m]),
)

/** The short hover-tooltip sentence for a metric, with a fallback. */
export function metricTooltip(id: string, fallback = ''): string {
  return ENTRY_BY_ID[id]?.tooltip ?? fallback
}

/** Anchor target on the guide page for a metric id. */
export function metricAnchor(id: string): string {
  return `metric-${id}`
}

/** Anchor target on the guide page for a glossary slug. */
export function termAnchor(slug: string): string {
  return `term-${slug}`
}

export function glossaryTerm(slug: string): GlossaryTerm | undefined {
  return GLOSSARY.find((t) => t.slug === slug)
}
