"""Degree-preserving null models and z-scores. (P2 / M2 -- stub.)

"More often than chance" in connectomics means: compare against the same graph
with its edges randomly rewired while every vertex keeps its in- and out-degree
(Maslov & Sneppen 2002). z-score = (observed - null mean) / null std over 5-10
samples.

This is the slow step. Mega-hub accounts make rewiring and the motif census
expensive, so every runner here is time-boxed; when the budget is exceeded the
caller falls back to a hub-capped subgraph (drop the top 0.1% of accounts by
degree) and **both** versions are reported (spec 8.3, risk table 14).
"""

from __future__ import annotations

import igraph as ig
import pandas as pd

#: Default number of rewired samples (spec 8.3).
N_SAMPLES = 10

#: Default wall-clock budget per null run, in seconds.
TIME_BUDGET_S = 30 * 60


def rewire(graph: ig.Graph, *, n_trials_per_edge: int = 10, seed: int | None = None) -> ig.Graph:
    """One degree-preserving rewired copy of ``graph`` (igraph ``rewire``)."""
    raise NotImplementedError("P2 / M2")


def hub_capped(graph: ig.Graph, *, top_fraction: float = 0.001) -> ig.Graph:
    """Drop the top ``top_fraction`` of vertices by total degree.

    The documented fallback when the full graph is too slow for nulls or motifs.
    """
    raise NotImplementedError("P2 / M2")


def null_distribution(
    graph: ig.Graph,
    statistic,
    *,
    n_samples: int = N_SAMPLES,
    time_budget_s: float = TIME_BUDGET_S,
    seed: int | None = None,
) -> pd.DataFrame:
    """Evaluate ``statistic(rewired_graph)`` over rewired samples.

    Returns one row per completed sample. Stops early when ``time_budget_s`` is
    exhausted, reporting how many samples actually ran -- a short but honest
    null beats a run that dies with the Kaggle session.
    """
    raise NotImplementedError("P2 / M2")


def z_scores(observed: dict[str, float], null: pd.DataFrame) -> pd.DataFrame:
    """z-score each observed statistic against its null distribution.

    Returns ``observed``, ``null_mean``, ``null_std``, ``z`` and ``n_samples``.
    """
    raise NotImplementedError("P2 / M2")
