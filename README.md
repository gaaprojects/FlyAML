# Money Connectome

Apply the network statistics neuroscientists used on the whole *Drosophila* brain —
reciprocity, rich club, integrator/broadcaster index, 3-node motifs — to the IBM
synthetic AML transaction graph (HI-Small: ~5.08M transactions, ~515k accounts,
~0.1% laundering), measure which laundering patterns they expose, and ask whether
money flows look more like a brain or like a random network.

| Brain concept | Money twin |
|---|---|
| Reciprocity (A→B and B→A) | Round-tripping |
| Integrator neuron (many in, few out) | Collector account (fan-in) |
| Broadcaster neuron (few in, many out) | Spreader account (fan-out) |
| Rich club | Big hubs trading mostly with each other |
| 3-node motifs | Loops and chains used for layering |

See [`4-money-connectome-spec.md`](./4-money-connectome-spec.md) for the *why* and
[`PLAN.md`](./PLAN.md) for what is done and what is next.

## How it runs

The package computes, Kaggle notebooks orchestrate. `moneyconn/` is pip-installable
and unit-tested on tiny toy graphs (3-cycle, star, reciprocal pair) that run fine on
an 8 GB laptop; the 5M-row dataset never leaves Kaggle, where each notebook starts
with

```python
%pip install "git+https://github.com/gaaprojects/FlyAML.git@v0.1.0"
```

attaches the dataset, and calls into the package. Parquet checkpoints pass state
between `kaggle_01_build_graph` → `02_metrics` → `03_detection`, so no single Kaggle
session repeats an expensive step.

## Layout

```
moneyconn/     load.py graph.py metrics.py nulls.py detect.py brain.py
notebooks/     kaggle_01_build_graph.ipynb (02, 03 to come)
tests/         toy-graph tests + a 10-row stand-in dataset
app/           Streamlit "Account X-ray" demo (M5)
reports/       figures
```

## Development

```powershell
.\.venv\Scripts\Activate.ps1          # activate (PowerShell)
.\.venv\Scripts\python.exe -m pytest  # run tests without activating
```

```bash
python -m pytest                                                  # all tests
python -m pytest tests/test_load.py::test_summarize_transactions  # one test
```

Tag a release whenever a notebook needs new package code.

## Status

Pre-implementation → **M0 scaffolding in place**: loader, patterns parser, toy
fixtures and the notebook 01 skeleton. `graph.py`, `metrics.py`, `nulls.py`,
`detect.py` and `brain.py` are documented stubs.

## Data and licensing

- Money: [IBM synthetic AML transactions](https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml)
  (Altman et al., 2023). Linked, never re-uploaded; only small derived aggregates are
  shared. Synthetic data — no conclusions about real people or institutions.
- Brain: FlyWire v783 connectivity, CC BY-NC 4.0 (Dorkenwald et al. 2024; Schlegel
  et al. 2024; Lin et al. 2024) — non-commercial portfolio use with attribution.
