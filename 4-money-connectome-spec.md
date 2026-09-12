# Money Connectome — brain-network analytics for anti-money laundering

**Series:** Fly-Finance portfolio · #2 FlyLedger · #3 FlyVol · **#4 Money Connectome** (build order 2 → 3 → 4)
**Owner:** Gaspar Astorga · **Status:** Draft v1 · **Last updated:** 2026-09-11
**Budget:** €0 (free cloud tiers only) · **Local machine:** 8 GB laptop, used only for editing and browsing; all data stays on Kaggle

> **One-liner:** Apply the network statistics neuroscientists used on the whole fly brain (reciprocity, rich club, motifs, integrators vs broadcasters) to a 5-million-transaction synthetic banking network, measure which laundering patterns they expose, and ask how "brain-like" money flows are.

---

## 1. Problem statement

Money laundering hides in the *structure* of payments more than in single transactions: money collected from many accounts, scattered to many, or sent round in loops. Banks use rules and, increasingly, graph machine learning, which is powerful but hard to explain to investigators. Connectomics has a mature, interpretable toolkit built for exactly this kind of huge directed graph. This project tests whether that toolkit surfaces laundering structure, and documents what it misses.

## 2. How it works, in plain words

The FlyWire team described the whole fly brain with a handful of network statistics (Lin et al., 2024). Each one has a money-world twin:

| Brain concept | Money twin |
|---|---|
| Reciprocity (A→B and B→A) | Round-tripping |
| Integrator neurons (many inputs, few outputs) | Collector accounts (fan-in) |
| Broadcaster neurons (few inputs, many outputs) | Spreader accounts (fan-out) |
| Rich club (hubs densely wired to each other) | Big hubs trading mostly with each other |
| Motifs (small wiring patterns that appear more often than chance) | Loops and chains used for layering |

- "More often than chance" is judged against a **null model**: the same graph with its connections randomly rewired while every node keeps its number of links. This is standard practice in connectomics.
- Synthetic data is a feature here: every laundering transaction is labeled, which never happens with real bank data.

## 3. Goals

| # | Goal | Measured by |
|---|---|---|
| G1 | Runs on free cloud | Full HI-Small pipeline on a Kaggle CPU notebook with the data attached (no download), ≤ 60 min, peak RAM ≤ 20 GB |
| G2 | Connectome metrics with nulls | ≥ 5 metrics at graph and account level, each compared with degree-preserving nulls |
| G3 | Detection value | Account-level PR-AUC and recall@k for unsupervised rankings, plus a heatmap of 8 patterns × metrics |
| G4 | Brain vs money | One figure comparing the same metrics on the fly connectome, the money network and their nulls |
| G5 | Portfolio-ready | Public Kaggle notebook + repo, demo, write-up |

## 4. Non-goals

- **Real bank data.** Privacy; synthetic data only.
- **Beating graph-neural-network state of the art.** Heavy and GPU-bound; P2 at most.
- **The Medium/Large variants** (31M–180M transactions). HI-Small answers the question.
- **Real-time monitoring.**
- **Conclusions about real people or institutions.** The data is simulated.

## 5. User stories

- As an **AML analyst**, I want each flagged account shown with its local network and the pattern it resembles (collector, spreader, loop) so that I can triage it quickly.
- As a **reviewer**, I want one table that maps laundering patterns to the metrics that catch them.
- As **the builder**, I want all heavy work on Kaggle, where the dataset already lives, so that nothing large touches my laptop.
- As a **reader**, I want to know whether a laundering network looks more like a brain or like a random graph.

## 6. Data

### 6.1 Money network: IBM synthetic AML transactions (Altman et al., 2023)

| Item | Detail |
|---|---|
| Kaggle dataset | `ealtman2019/ibm-transactions-for-anti-money-laundering-aml` |
| Variant to use | **HI-Small**: ~5.08M transactions between ~515k accounts over ~10 simulated days; ~0.1% of transactions are laundering |
| Files | `HI-Small_Trans.csv` (transactions) and `HI-Small_Patterns.txt` (laundering attempts grouped by pattern) |
| Columns | `Timestamp`, `From Bank`, `Account`, `To Bank`, `Account` (pandas renames the second one `Account.1`), `Amount Received`, `Receiving Currency`, `Amount Paid`, `Payment Currency`, `Payment Format`, `Is Laundering` |
| Patterns | Fan-out, fan-in, gather-scatter, scatter-gather, simple cycle, random, bipartite, stack |
| Caveat | Most laundering transactions are not assigned to a specific pattern. Use only assigned ones for the per-pattern analysis, and all labels for the overall metrics. |
| License | Check the license on the Kaggle page. Link to the data rather than re-uploading it, and share only small derived aggregates. |

### 6.2 Brain network: FlyWire v783 (for the comparison)

- `Connectivity_783.parquet` from `philshiu/Drosophila_brain_model` (see the FlyVol spec), fetched by URL inside the Kaggle notebook.
- Threshold at ≥ 5 synapses (common in connectomics): **134,181 neurons and 2,700,513 connections** (checked 2026-09-11). Quick check: reciprocity ≈ 0.14.
- License: CC BY-NC 4.0. Non-commercial portfolio use with attribution.

## 7. Compute and cost plan

| Step | Where it runs | Cost |
|---|---|---|
| Load + aggregate 5M transactions | **Kaggle CPU notebook** with the dataset attached (~30 GB RAM) | €0 |
| Graph metrics + nulls | Same notebook, `python-igraph` (C-backed, fast) | €0 |
| Long runs (nulls, motifs) | "Save & Run All" background runs; save parquet checkpoints between steps | €0 |
| Fly-brain metrics | Same notebook; turn on internet (needs a phone-verified Kaggle account) to fetch the parquet | €0 |
| Supervised model (P1) | LightGBM on Kaggle CPU | €0 |
| Derived tables | Notebook output saved as a versioned Kaggle dataset | €0 |
| Demo | Streamlit Community Cloud with a small precomputed file (< 50 MB); ~1 GB RAM limit | €0 |
| Optional SQL path (P2) | BigQuery sandbox (free: 10 GB storage, 1 TB of queries per month; tables expire after 60 days) | €0 |

Colab also works (download through the Kaggle API), but its ~12 GB RAM is tight for 5M rows plus graphs, so Kaggle is the default.

## 8. Method

### 8.1 Build the graph

- Account ID = `f"{bank}_{account}"`.
- Load only the columns you need, with compact types (`category`, `int32`, `float32`), or use polars.
- Currency: derive exchange rates from cross-currency rows (median `Amount Paid / Amount Received` per currency pair) and convert everything to USD. If this slows you down, start with transaction counts only.
- Aggregate repeated payments into one directed, weighted edge per account pair: count, total USD, first and last timestamp. Save it as parquet.
- Keep the raw, time-stamped edge list for cycle checks (money must move forward in time).

### 8.2 Metrics (graph level and per account)

| Metric | Per-account feature | Implementation |
|---|---|---|
| In/out degree and strength | Counterparties and USD in/out | numpy `bincount` |
| Reciprocity | Share of partners with payments both ways; round-trip value = Σ min(flow A→B, flow B→A) | igraph `reciprocity()` + pandas self-merge |
| Integrator–broadcaster index | (in − out) / (in + out), by degree and by USD | numpy |
| Rich club | Member of the top-degree club; rich-club coefficient normalized by the null | pandas on the edge list |
| 3-node motifs | Per-account triangle / 3-cycle counts; graph-level motif z-scores | igraph `motifs_randesu(size=3)`, with `cut_prob` sampling if slow |
| Short cycles (2–4 hops, time-respecting) | Cycle count per account | Restricted search on a candidate subgraph (P1) |

### 8.3 Null model

- Degree-preserving rewiring (igraph `rewire`), 5–10 samples. z-score = (observed − null mean) / null std.
- Hub accounts make motifs and rewiring slow. Time-box it, then fall back to a hub-capped subgraph (drop the top 0.1% of accounts by degree) and report both versions.

### 8.4 Detection experiments

- **Account label:** 1 if the account sends or receives any laundering transaction.
- **Unsupervised:** rank accounts by each metric and by a simple combined z-score. Labels are used only for scoring.
- **Per-pattern heatmap:** for each of the 8 patterns, the share of involved accounts that land in the top 1% of each metric.
- **Heuristic baseline:** "old-school rules" such as total amount, number of counterparties and number of payment formats. This is the bar the connectome metrics must clear.
- **Supervised lift (P1):** LightGBM with a time-based split (first ~70% of transactions for training, with graph features built only from the training window), comparing basic tabular features vs basic + connectome features.

### 8.5 Brain vs money

One table and one figure with the same metrics for the fly brain, the money network, and degree-preserving nulls of each.

## 9. Evaluation and success metrics

- Account-level PR-AUC, recall@k (k = 100; 1,000; 10,000) and lift over a random ranking.
- Per-pattern detection heatmap (patterns × metrics).
- P1: supervised PR-AUC and recall@k with and without connectome features, with bootstrap confidence intervals.
- Runtime and peak RAM per step.
- **Success:** at least one connectome metric shows ≥ 5× lift in the top 1% for at least 2 pattern types, beats the heuristic baseline on at least one of them, and the blind spots are documented.
- **Stretch:** the conclusions hold on LI-Small (lower illicit ratio, harder).

## 10. Requirements

### P0: must have

1. **Loader** with compact dtypes. *AC:* ~5.08M rows; laundering share ≈ 0.1%; peak RAM logged.
2. **Edge aggregation** to parquet. *AC:* ~515k accounts; the summed counts equal the number of transactions.
3. **Metrics module** tested on toy graphs with known answers (a 3-cycle, a star, a reciprocal pair).
4. **Degree-preserving nulls** and z-scores for the graph-level metrics.
5. **Unsupervised rankings, heuristic baseline and per-pattern heatmap.**
6. **Public Kaggle notebook** + README with the headline heatmap.

### P1: nice to have

1. Time-respecting short cycles.
2. Supervised lift experiment.
3. Brain-vs-money figure.
4. **Streamlit "Account X-ray" demo:** pick a flagged account and see its 2-hop network, its metrics vs the population, and its true pattern if any. *AC:* < 1 GB RAM (precomputed top-500 neighborhoods).

### P2: later

1. LI-Small robustness check.
2. BigQuery SQL version of the aggregation and reciprocity steps.
3. GNN baseline on a Kaggle GPU.
4. Community detection (Leiden/Infomap) and laundering concentration per community.

## 11. Repo layout

```
money-connectome/
├── README.md
├── spec.md
├── requirements.txt
├── moneyconn/        # load.py, graph.py, metrics.py, nulls.py, detect.py, brain.py
├── notebooks/        # kaggle_01_build_graph.ipynb, kaggle_02_metrics.ipynb, kaggle_03_detection.ipynb
├── app/              # streamlit_app.py + small precomputed data
├── tests/            # toy-graph tests
└── reports/figures/
```

## 12. Milestones (sessions of ~2–3 h)

| Milestone | Sessions | Done when |
|---|---|---|
| M0 Setup | 1 | Kaggle notebook with the data attached; loader; degree distributions |
| M1 Graph | 2 | Edge aggregation, currency conversion, toy-graph tests green |
| M2 Metrics | 2 | All P0 metrics + nulls on the full graph (or a documented fallback) |
| M3 Detection | 2 | Rankings, heuristic baseline, per-pattern heatmap, first verdict |
| M4 Brain vs money | 2 | Comparison figure; supervised lift if time allows |
| M5 Publish | 2 | Demo, README, project page, LinkedIn post |

## 13. Portfolio deliverables

- Public Kaggle notebook (extra visibility on your Kaggle profile) + GitHub repo
- Headline figure: the patterns × metrics heatmap. Second figure: "Is money more like a brain or a random network?"
- Streamlit "Account X-ray" demo
- Project page on gaaprojects.github.io and one LinkedIn post
- Skills shown: graph analytics at scale, AML domain knowledge, interpretable detection, and (optionally) SQL on BigQuery

## 14. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Mega-hub accounts dominate metrics and slow nulls and motifs | Log scales; hub-capped variant; report both |
| Label leakage in the supervised split | Build graph features from the training window only |
| Most laundering transactions have no pattern label | Per-pattern analysis on assigned ones only |
| Kaggle session limits (~9–12 h) | Parquet checkpoints; split the work into three notebooks |
| Motif census too slow | `cut_prob` sampling; time-box |
| Synthetic ≠ real | Say so clearly; the conclusions are about methods |

## 15. Open questions

- **(You, non-blocking)** Structure-only metrics first, or USD-weighted from the start?
- **(You, non-blocking)** Make the Kaggle notebook public from day one, or at the end?
- **(Data/legal, blocking only for publishing derived data)** Confirm the dataset license on the Kaggle page.

## 16. References

- Altman et al. (2023). Realistic synthetic financial transactions for anti-money laundering models. NeurIPS Datasets & Benchmarks. arXiv:2306.16424
- Lin et al. (2024). Network statistics of the whole-brain connectome of Drosophila. *Nature* 634:153–165. Code: github.com/murthylab/flywire-network-analysis
- Dorkenwald et al. (2024) and Schlegel et al. (2024). FlyWire papers, *Nature* 634.
- Milo et al. (2002). Network motifs: simple building blocks of complex networks. *Science* 298:824–827.
- Colizza, Flammini, Serrano & Vespignani (2006). Detecting rich-club ordering in complex networks. *Nature Physics* 2:110–115.
- Maslov & Sneppen (2002). Specificity and stability in topology of protein networks. *Science* 296:910–913.
- Csárdi & Nepusz (2006). The igraph software package for complex network research. *InterJournal Complex Systems* 1695.
