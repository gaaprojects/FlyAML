"""The fly connectome, run through the same metrics. (P4 / M4 -- stub.)

Answers the closing question: is the money network more like a brain or like a
random graph? Same statistics, three graphs -- fly brain, money, and
degree-preserving nulls of each.

Data: ``Connectivity_783.parquet`` (FlyWire v783) fetched **by URL from inside
the Kaggle notebook** with internet on, never downloaded to the laptop.
Thresholded at >=5 synapses, the standard connectomics cut, which gives 134,181
neurons and 2,700,513 connections (checked 2026-09-11); reciprocity should come
out near 0.14 as a sanity check.

License: FlyWire data is CC BY-NC 4.0 -- non-commercial portfolio use with
attribution (Dorkenwald et al. 2024; Schlegel et al. 2024; Lin et al. 2024).
"""

from __future__ import annotations

from pathlib import Path

import igraph as ig
import pandas as pd

#: Source of the connectivity table (see the FlyVol spec).
CONNECTIVITY_URL = (
    "https://github.com/philshiu/Drosophila_brain_model/raw/main/data/Connectivity_783.parquet"
)

#: Standard connectomics threshold: keep connections of >= 5 synapses.
SYNAPSE_THRESHOLD = 5

#: Expected size after thresholding, as a sanity check.
EXPECTED_NEURONS = 134_181
EXPECTED_CONNECTIONS = 2_700_513

#: Expected reciprocity of the thresholded connectome.
EXPECTED_RECIPROCITY = 0.14


def fetch_connectivity(url: str = CONNECTIVITY_URL, *, cache_dir: str | Path | None = None):
    """Download the FlyWire connectivity parquet (Kaggle, internet on)."""
    raise NotImplementedError("P4 / M4")


def load_connectome(
    path: str | Path, *, synapse_threshold: int = SYNAPSE_THRESHOLD
) -> pd.DataFrame:
    """Read the connectivity table and keep connections above the threshold.

    Returns a ``src``/``dst``/``weight`` edge list in the same shape as the
    money edge list, so the metric functions take either without special-casing.
    """
    raise NotImplementedError("P4 / M4")


def build_connectome_graph(edges: pd.DataFrame) -> ig.Graph:
    """Directed igraph graph of the thresholded connectome."""
    raise NotImplementedError("P4 / M4")


def compare_networks(summaries: dict[str, dict[str, float]]) -> pd.DataFrame:
    """Assemble the brain / money / nulls comparison table.

    ``summaries`` maps a network name to its :func:`moneyconn.metrics.graph_summary`
    output; the result is the table behind the M4 figure.
    """
    raise NotImplementedError("P4 / M4")
