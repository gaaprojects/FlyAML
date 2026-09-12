"""Aggregate transactions into a directed weighted graph. (P1 / M1 -- stub.)

Plan: one directed edge per ordered account pair, carrying ``count``,
``total_paid``, ``first_ts`` and ``last_ts``. Structure-only first: the graph
weight used by the metrics is ``count`` (spec 15.1), with USD totals kept on the
edge so the weighted variant can be added later without reworking anything.

The aggregated edge list is the parquet checkpoint that
``kaggle_01_build_graph`` writes and ``kaggle_02_metrics`` reads, so no Kaggle
session repeats the 5M-row aggregation. The raw timestamped edge list is kept
separately for the time-respecting cycle search (P1).

Acceptance criteria for M1: ~515k vertices and ``edges["count"].sum() ==
len(transactions)``.
"""

from __future__ import annotations

from pathlib import Path

import igraph as ig
import pandas as pd

#: Columns of the aggregated edge list.
EDGE_COLUMNS: tuple[str, ...] = ("src", "dst", "count", "total_paid", "first_ts", "last_ts")


def aggregate_edges(transactions: pd.DataFrame, *, drop_self_loops: bool = False) -> pd.DataFrame:
    """Collapse repeated payments into one directed weighted edge per pair.

    Parameters
    ----------
    transactions:
        Output of :func:`moneyconn.load.load_transactions` (needs ``src``/``dst``).
    drop_self_loops:
        Whether to drop ``src == dst`` rows (accounts paying themselves, e.g.
        ``Reinvestment``). Kept by default so edge counts still sum to the
        transaction count.

    Returns
    -------
    DataFrame with :data:`EDGE_COLUMNS`.
    """
    raise NotImplementedError("P1 / M1")


def write_edges(edges: pd.DataFrame, path: str | Path) -> Path:
    """Write the aggregated edge list to parquet (the inter-notebook checkpoint)."""
    raise NotImplementedError("P1 / M1")


def read_edges(path: str | Path) -> pd.DataFrame:
    """Read an aggregated edge list back from parquet."""
    raise NotImplementedError("P1 / M1")


def build_graph(edges: pd.DataFrame, *, weight: str = "count") -> ig.Graph:
    """Build the directed igraph graph from an aggregated edge list.

    igraph rather than networkx: the C backend is what makes ~5M edges feasible
    (spec 8.1). Vertex names are account ids; ``weight`` names the edge
    attribute the metrics should use.
    """
    raise NotImplementedError("P1 / M1")


def raw_edge_list(transactions: pd.DataFrame) -> pd.DataFrame:
    """The raw timestamped edge list (``src``, ``dst``, ``timestamp``, amount).

    Kept for time-respecting cycle checks, where money must move forward in
    time and aggregation would lose the ordering.
    """
    raise NotImplementedError("P1 / M1")
