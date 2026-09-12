"""Money Connectome: connectomics network statistics for an AML transaction graph.

The package computes, the Kaggle notebooks orchestrate. Every module here is
unit-tested locally on tiny toy graphs; the 5M-row HI-Small dataset is only
ever touched from Kaggle, where the notebooks install this package with::

    pip install "git+https://github.com/gaaprojects/FlyAML.git@<tag>"

Modules
-------
:mod:`moneyconn.load`
    Read ``HI-Small_Trans.csv`` with compact dtypes; parse the patterns file.
:mod:`moneyconn.graph`
    Aggregate transactions into a directed weighted graph (parquet checkpoint).
:mod:`moneyconn.metrics`
    Degree/strength, reciprocity, integrator-broadcaster index, rich club, motifs.
:mod:`moneyconn.nulls`
    Degree-preserving rewiring and z-scores.
:mod:`moneyconn.detect`
    Account labels, unsupervised rankings, baseline, per-pattern heatmap, metrics.
:mod:`moneyconn.brain`
    The same metrics on the FlyWire v783 connectome, for the comparison figure.
"""

from __future__ import annotations

__version__ = "0.1.0"

from moneyconn import load  # noqa: F401  (convenience: `from moneyconn import load`)

__all__ = ["load", "__version__"]
