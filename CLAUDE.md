# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

The repo is **pre-implementation**: only `4-money-connectome-spec.md` (the spec), `PLAN.md` (the plan) and this file exist.
No `moneyconn/` package, `pyproject.toml`, `requirements.txt` or tests have been written yet.

- **`PLAN.md` is the source of truth for what to do next.** Read it before starting work and tick its checkboxes as phases land.
- `4-money-connectome-spec.md` holds the *why* — goals, acceptance criteria, references.
- Anything below describing `moneyconn/` or the notebooks is the **target design**, not existing code.

## What this project is

Apply connectomics network statistics (reciprocity, rich club, integrator/broadcaster index, 3-node motifs) — the ones used on the whole *Drosophila* brain — to the IBM synthetic AML transaction graph (HI-Small: ~5.08M transactions, ~515k accounts, ~0.1% laundering), measure which laundering patterns they expose, and compare money-flow structure against the fly connectome and against degree-preserving nulls.

## The two-tier execution model (most important thing to understand)

The local machine is an 8 GB laptop; the 5M-row dataset **never touches it**.

- **`moneyconn/` computes, Kaggle notebooks orchestrate.** All logic lives in a pip-installable package, unit-tested locally on *tiny toy graphs* (3-cycle, star, reciprocal pair) with known answers.
- Each Kaggle notebook starts with `pip install "git+https://github.com/gaaprojects/FlyAML.git@<tag>"`, attaches the AML dataset, and calls into `moneyconn`. Heavy runs happen there (~30 GB RAM, internet on).
- **Parquet checkpoints** pass state between the three notebooks (`kaggle_01_build_graph` → `02_metrics` → `03_detection`) so no single Kaggle session (≈9–12 h limit) repeats expensive steps.

Practical consequence: when writing code here, correctness is proven by toy-graph tests locally; scale is proven only on Kaggle. Never add a test or script that expects the real dataset to be present locally.

### Target module responsibilities

| Module | Responsibility |
|---|---|
| `load.py` | Read `HI-Small_Trans.csv` with compact dtypes; build account IDs; parse `HI-Small_Patterns.txt`; log peak RAM |
| `graph.py` | Aggregate repeated payments → one directed weighted edge per pair → parquet; build the igraph graph; keep the raw timestamped edge list |
| `metrics.py` | Degree/strength, reciprocity + round-trip value, integrator–broadcaster index, rich club, 3-node motifs |
| `nulls.py` | Degree-preserving rewiring + z-scores, with time-box and hub-capped fallback |
| `detect.py` | Account labels, unsupervised rankings, heuristic baseline, per-pattern heatmap, PR-AUC / recall@k / lift |
| `brain.py` | Fetch FlyWire `Connectivity_783.parquet` by URL, threshold ≥5 synapses, run the same metrics |

## Commands

A local `.venv` (Python 3.12) exists with pandas, numpy, pyarrow, python-igraph, scikit-learn, matplotlib and pytest installed.

```powershell
.\.venv\Scripts\Activate.ps1          # activate (PowerShell)
.\.venv\Scripts\python.exe -m pytest  # run tests without activating
```

```bash
python -m pytest tests/ -v            # all tests
python -m pytest tests/test_metrics.py::test_reciprocal_pair -v   # a single test
```

There is no build step; the package is consumed by Kaggle via `pip install git+...@<tag>`, so **tag a release when a notebook needs new package code**.

## Domain gotchas (decided — don't re-litigate)

- **Account ID = `f"{bank}_{account}"`.** The CSV has two columns named `Account`; pandas loads the second as `Account.1`.
- **Use `python-igraph`, not networkx** — the C backend is what makes 5M edges feasible.
- **Structure-only first:** edge weight = transaction count. USD/FX conversion is a deferred add-on, not a blocker.
- **Per-pattern analysis uses only pattern-assigned laundering rows** (most laundering transactions have no pattern label); overall metrics use all labels.
- **Nulls and motifs are the slow step.** Time-box them, then fall back to a hub-capped subgraph (drop the top 0.1% of accounts by degree) and report *both* versions.
- **Label-leakage guard:** the supervised (P1) experiment uses a time-based split and builds graph features from the **training window only**.
- **Data handling:** link to the Kaggle dataset, never re-upload it; share only small derived aggregates. FlyWire data is CC BY-NC 4.0 (attribution, non-commercial). Confirm the AML dataset license on its Kaggle page before publishing any derived data.
- The Kaggle notebook stays private until the end of the project.

## Git workflow

Default branch is **`Master`** (capital M); `Develop` and `Feature` also exist on the remote, and work reaches `Master` through pull requests. Day-to-day work goes on `Develop`.
