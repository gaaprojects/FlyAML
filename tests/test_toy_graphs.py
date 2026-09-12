"""Pin down the toy graphs' known answers with igraph directly.

These are the same three shapes the P2 metric tests will use (3-cycle, star,
reciprocal pair). Checking them against igraph now means that when
``moneyconn.metrics`` disagrees with the table in ``conftest.py``, the metric is
wrong rather than the fixture.
"""

from __future__ import annotations

import pytest


def test_three_cycle_shape(three_cycle):
    assert three_cycle.is_directed()
    assert three_cycle.vcount() == 3
    assert three_cycle.ecount() == 3
    assert three_cycle.reciprocity() == pytest.approx(0.0)
    assert three_cycle.indegree() == [1, 1, 1]
    assert three_cycle.outdegree() == [1, 1, 1]


def test_three_cycle_has_exactly_one_directed_cycle(three_cycle):
    # Motif class 3-cycle: every vertex has in=out=1 and the graph is strongly connected.
    assert three_cycle.is_connected(mode="strong")


def test_out_star_is_a_pure_broadcaster(out_star):
    hub = out_star.vs.find(name="H").index
    assert out_star.outdegree(hub) == 5
    assert out_star.indegree(hub) == 0
    assert out_star.reciprocity() == pytest.approx(0.0)
    leaves = [v.index for v in out_star.vs if v["name"] != "H"]
    assert all(out_star.indegree(v) == 1 and out_star.outdegree(v) == 0 for v in leaves)


def test_in_star_is_a_pure_collector(in_star):
    hub = in_star.vs.find(name="H").index
    assert in_star.indegree(hub) == 5
    assert in_star.outdegree(hub) == 0
    assert in_star.reciprocity() == pytest.approx(0.0)


def test_reciprocal_pair(reciprocal_pair):
    assert reciprocal_pair.reciprocity() == pytest.approx(1.0)
    assert reciprocal_pair.ecount() == 2
    # Round-trip value is min(3, 1) = 1 once metrics.account_reciprocity lands.
    assert sorted(reciprocal_pair.es["count"]) == [1, 3]
