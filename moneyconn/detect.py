"""Do the connectome metrics actually surface laundering? (P3 / M3 -- stub.)

The evaluation, all account-level:

* **Label:** 1 if the account sends or receives any laundering transaction.
* **Unsupervised rankings:** rank accounts by each metric and by a combined
  z-score. Labels are used for scoring only, never for fitting.
* **Heuristic baseline:** old-school rules (total amount, number of
  counterparties, number of payment formats). This is the bar the connectome
  metrics have to clear.
* **Per-pattern heatmap:** for each of the 8 patterns, the share of involved
  accounts landing in the top 1% of each metric -- the headline figure. Uses
  only pattern-assigned rows, since most laundering transactions have no
  pattern label.
* **Scores:** PR-AUC, recall@k (k = 100 / 1k / 10k), lift over random.

Success (spec 9): at least one metric with >=5x lift in the top 1% on >=2
pattern types, beating the baseline on >=1, with the blind spots written down.
"""

from __future__ import annotations

import pandas as pd

#: Recall cutoffs reported for every ranking.
RECALL_K = (100, 1_000, 10_000)

#: Quantile used for the per-pattern heatmap.
TOP_QUANTILE = 0.01


def account_labels(transactions: pd.DataFrame) -> pd.Series:
    """1 if the account sends or receives any laundering transaction, else 0.

    Indexed by account id over the full account universe.
    """
    raise NotImplementedError("P3 / M3")


def account_patterns(patterns: pd.DataFrame) -> pd.DataFrame:
    """Map accounts to the pattern types they take part in.

    From the patterns file only (pattern-assigned rows). An account can appear
    in several attempts, so this is long-form: one row per (account, pattern).
    """
    raise NotImplementedError("P3 / M3")


def heuristic_baseline(transactions: pd.DataFrame) -> pd.DataFrame:
    """Per-account rule-style features: total amount, counterparties, formats."""
    raise NotImplementedError("P3 / M3")


def rank_accounts(features: pd.DataFrame, *, ascending: bool = False) -> pd.DataFrame:
    """Rank accounts by each feature column (1 = most suspicious)."""
    raise NotImplementedError("P3 / M3")


def combined_z_score(features: pd.DataFrame, *, columns: list[str] | None = None) -> pd.Series:
    """A single suspicion score: mean of the per-feature z-scores."""
    raise NotImplementedError("P3 / M3")


def score_ranking(scores: pd.Series, labels: pd.Series, *, k_values=RECALL_K) -> dict[str, float]:
    """PR-AUC, recall@k and lift over random for one ranking."""
    raise NotImplementedError("P3 / M3")


def evaluate_features(features: pd.DataFrame, labels: pd.Series) -> pd.DataFrame:
    """Run :func:`score_ranking` over every feature column. One row per feature."""
    raise NotImplementedError("P3 / M3")


def pattern_metric_heatmap(
    features: pd.DataFrame,
    account_patterns: pd.DataFrame,
    *,
    quantile: float = TOP_QUANTILE,
) -> pd.DataFrame:
    """Patterns x metrics: share of a pattern's accounts in the top ``quantile``.

    The headline figure of the project. Rows are the 8 pattern types, columns
    the metrics; ``1 / quantile`` times the cell value is the lift.
    """
    raise NotImplementedError("P3 / M3")


def supervised_lift(
    transactions: pd.DataFrame,
    features: pd.DataFrame,
    labels: pd.Series,
    *,
    train_fraction: float = 0.7,
) -> pd.DataFrame:
    """LightGBM with and without connectome features. (P1 extra, spec 8.4.)

    Time-based split: the first ``train_fraction`` of transactions trains, and
    graph features must be built from that window only -- building them on the
    full graph leaks the future into the training set.
    """
    raise NotImplementedError("P1 extra")
