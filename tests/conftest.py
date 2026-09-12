"""Toy fixtures: tiny graphs with known answers, plus the miniature CSV.

Correctness is proven here, on graphs small enough to check by hand; scale is
proven only on Kaggle. Nothing in this suite may require the real 5M-row
dataset.

Known answers (used by the metric tests from P2 on):

=================  ============  ===========  ==========================
Graph              reciprocity   3-cycles     integrator/broadcaster
=================  ============  ===========  ==========================
3-cycle            0.0           1            0 for every vertex
out-star (hub->5)  0.0           0            -1 hub, +1 leaves
in-star (5->hub)   0.0           0            +1 hub, -1 leaves
reciprocal pair    1.0           0            0 for both
=================  ============  ===========  ==========================
"""

from __future__ import annotations

from pathlib import Path

import igraph as ig
import pytest

from moneyconn import load

DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def toy_trans_path() -> Path:
    """Miniature stand-in for ``HI-Small_Trans.csv`` (10 rows, 5 accounts)."""
    return DATA_DIR / "toy_trans.csv"


@pytest.fixture(scope="session")
def toy_patterns_path() -> Path:
    """Miniature stand-in for ``HI-Small_Patterns.txt`` (2 attempts, 5 rows)."""
    return DATA_DIR / "toy_patterns.txt"


@pytest.fixture
def toy_transactions(toy_trans_path: Path):
    return load.load_transactions(toy_trans_path)


@pytest.fixture
def toy_patterns(toy_patterns_path: Path):
    return load.parse_patterns(toy_patterns_path)


# --------------------------------------------------------------------------- #
# Toy graphs
# --------------------------------------------------------------------------- #
@pytest.fixture
def three_cycle() -> ig.Graph:
    """A -> B -> C -> A. One 3-cycle, no reciprocal edge."""
    graph = ig.Graph(directed=True)
    graph.add_vertices(["A", "B", "C"])
    graph.add_edges([("A", "B"), ("B", "C"), ("C", "A")])
    graph.es["count"] = [1, 1, 1]
    return graph


@pytest.fixture
def out_star() -> ig.Graph:
    """Hub -> five leaves. The pure spreader / broadcaster."""
    leaves = [f"L{i}" for i in range(5)]
    graph = ig.Graph(directed=True)
    graph.add_vertices(["H", *leaves])
    graph.add_edges([("H", leaf) for leaf in leaves])
    graph.es["count"] = [1] * len(leaves)
    return graph


@pytest.fixture
def in_star() -> ig.Graph:
    """Five leaves -> hub. The pure collector / integrator."""
    leaves = [f"L{i}" for i in range(5)]
    graph = ig.Graph(directed=True)
    graph.add_vertices(["H", *leaves])
    graph.add_edges([(leaf, "H") for leaf in leaves])
    graph.es["count"] = [1] * len(leaves)
    return graph


@pytest.fixture
def reciprocal_pair() -> ig.Graph:
    """A <-> B, with different weights each way (round-tripping)."""
    graph = ig.Graph(directed=True)
    graph.add_vertices(["A", "B"])
    graph.add_edges([("A", "B"), ("B", "A")])
    graph.es["count"] = [3, 1]
    return graph
