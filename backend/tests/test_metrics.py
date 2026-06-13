"""Pin the metric math against hand-computed values.

These are the tests that matter most: if an eval tool's own metrics drift,
every number it shows the user is wrong.
"""
import math

from app.metrics.base import Scored
from app.metrics.classification import Accuracy, F1Macro, PrecisionMacro, RecallMacro
from app.metrics.exact_match import ExactMatch, normalize
from app.metrics.rouge import Rouge1, Rouge2, RougeL, ngram_f1, rouge_l_f1


def test_exact_match_normalizes():
    em = ExactMatch()
    assert em.score("Paris", "paris") == 1.0
    assert em.score("  Paris  ", "Paris") == 1.0
    assert em.score("Paris.", "Paris") == 0.0  # punctuation is significant
    assert em.score("Lyon", "Paris") == 0.0


def test_exact_match_requires_reference():
    assert ExactMatch().score("anything", None) == 0.0


def test_normalize_collapses_whitespace():
    assert normalize("  The   Quick\nFox ") == "the quick fox"


def test_rouge1_perfect_and_zero():
    assert ngram_f1("the cat sat", "the cat sat", 1) == 1.0
    assert ngram_f1("alpha beta", "gamma delta", 1) == 0.0


def test_rouge1_partial_overlap():
    # pred unigrams: {the, cat, ran}; ref unigrams: {the, dog, ran}
    # overlap = {the, ran} = 2.  precision = 2/3, recall = 2/3, F1 = 2/3.
    assert math.isclose(ngram_f1("the cat ran", "the dog ran", 1), 2 / 3, rel_tol=1e-9)


def test_rouge2_bigrams():
    # pred bigrams: (the,cat),(cat,sat); ref bigrams: (the,cat),(cat,ran)
    # overlap = (the,cat) = 1. precision = 1/2, recall = 1/2, F1 = 1/2.
    assert math.isclose(ngram_f1("the cat sat", "the cat ran", 2), 0.5, rel_tol=1e-9)


def test_rouge2_too_short_is_zero():
    # only one token -> no bigrams on one side
    assert ngram_f1("hello", "hello world", 2) == 0.0


def test_rouge_l_subsequence():
    # LCS of [a,b,c,d] and [a,c,d] is [a,c,d] = 3.
    # precision = 3/4, recall = 3/3=1, F1 = 2*0.75*1/(1.75) = 6/7.
    assert math.isclose(rouge_l_f1("a b c d", "a c d"), 6 / 7, rel_tol=1e-9)


def test_rouge_l_rewards_order_over_rouge2():
    # gapped-but-ordered overlap: ROUGE-L sees it, ROUGE-2 mostly doesn't.
    pred, ref = "the quick brown fox", "the slow brown fox"
    assert rouge_l_f1(pred, ref) > ngram_f1(pred, ref, 2)


def test_metric_classes_carry_info():
    for metric in (Rouge1(), Rouge2(), RougeL(), ExactMatch()):
        assert metric.info.id
        assert metric.info.requires_reference is True
        assert metric.info.range == [0.0, 1.0]


# --- classification (doc §3.3) ---------------------------------------------
# Worked example. true=[pos,pos,neg,neg], pred=[pos,neg,neg,neg]:
#   accuracy = 3/4 = 0.75
#   macro precision = mean(pos: 1/1, neg: 2/3)               = 0.8333
#   macro recall    = mean(pos: 1/2, neg: 2/2)               = 0.75
#   macro f1        = mean(pos: 0.6667, neg: 0.8)            = 0.7333
def _scored(true_labels, pred_labels):
    return [
        Scored(prediction=p, reference=t, context=None, value=None)
        for t, p in zip(true_labels, pred_labels)
    ]


def test_classification_aggregates():
    s = _scored(["pos", "pos", "neg", "neg"], ["pos", "neg", "neg", "neg"])
    assert Accuracy().aggregate(s) == 0.75
    assert math.isclose(PrecisionMacro().aggregate(s), 0.8333, abs_tol=1e-3)
    assert RecallMacro().aggregate(s) == 0.75
    assert math.isclose(F1Macro().aggregate(s), 0.7333, abs_tol=1e-3)


def test_classification_per_case_correctness_is_normalized():
    acc = Accuracy()
    assert acc.score("Pos", "pos") == 1.0
    assert acc.score("neg", "pos") == 0.0


def test_set_level_metrics_are_aggregate_only():
    assert PrecisionMacro().info.aggregate_only is True
    assert RecallMacro().info.aggregate_only is True
    assert F1Macro().info.aggregate_only is True
    assert Accuracy().info.aggregate_only is False


def test_classification_aggregate_ignores_cases_without_labels():
    s = _scored(["pos", "neg"], ["pos", "neg"])
    s.append(Scored(prediction="pos", reference=None, context=None, value=None))  # no label
    assert Accuracy().aggregate(s) == 1.0
