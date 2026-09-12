# Money Connectome — Implementation Plan

> The defined, followable plan for the project specified in
> [`4-money-connectome-spec.md`](./4-money-connectome-spec.md).
> This file is the source of truth for **what to do next**. Update the checkboxes as work lands.

**Owner:** Gaspar Astorga · **Plan created:** 2026-09-12 · **Status:** P0 not started

---

## 0. Confirmed decisions (locked 2026-09-12)

| Decision | Choice | Consequence |
|---|---|---|
| Dev workflow | **Local package + Kaggle notebooks** | `moneyconn/` is pip-installable, unit-tested locally on toy graphs; Kaggle notebooks `pip install` it from GitHub and run the 5M-row jobs. |
| First-pass scope | **Structure-only first** | Edge weight = transaction count. Currency→USD conversion is a deferred add-on for M2/M3, not a blocker. |
| Kaggle account | **Ready + phone-verified (internet ON)** | Dataset can be attached; FlyWire parquet can be fetched by URL, so brain-vs-money (G4) is available when we reach M4. |

Non-blocking spec open questions resolved: 15.1 → structure-only first. 15.2 (public notebook timing) → **publish at the end** unless changed. 15.3 (dataset license) → **confirm on the Kaggle page before publishing any derived data**.

---

## 1. How the pieces fit

- **`moneyconn/`** is a proper pip-installable package (`pyproject.toml`). All logic lives here and is unit-tested on **tiny toy graphs** (3-cycle, star, reciprocal pair) that run fine on the 8 GB laptop. The 5M-row data never touches the laptop.
- **Kaggle notebooks orchestrate, the package computes.** Each notebook starts with
  `pip install "git+https://github.com/gaaprojects/FlyAML.git@<tag>"`, attaches the AML dataset, and calls `moneyconn`.
- **Parquet checkpoints** pass data between the three notebooks so no single Kaggle session (≈9–12 h limit) repeats expensive steps.
- **Structure-only first:** directed edge weight = count of transactions; USD weighting added later without reworking the pipeline.

---

## 2. Repo layout (target — spec §11)

```
money-connectome/            # (this repo root)
├── README.md
├── 4-money-connectome-spec.md
├── PLAN.md                  # this file
├── pyproject.toml           # makes moneyconn pip-installable from GitHub
├── requirements.txt
├── .gitignore
├── moneyconn/               # load.py, graph.py, metrics.py, nulls.py, detect.py, brain.py
├── notebooks/               # kaggle_01_build_graph, kaggle_02_metrics, kaggle_03_detection
├── app/                     # streamlit_app.py + small precomputed data
├── tests/                   # toy-graph tests (pytest)
└── reports/figures/
```

### Package module responsibilities

| Module | Responsibility |
|---|---|
| `load.py` | Read `HI-Small_Trans.csv` with compact dtypes (`category`/`int32`/`float32`); build `account = f"{bank}_{account}"` (2nd account col loads as `Account.1`); parse `HI-Small_Patterns.txt`; log peak RAM. |
| `graph.py` | Aggregate repeated payments → one directed weighted edge per pair (count, total, first/last ts) → parquet; build `python-igraph` graph; keep raw timestamped edge list for time-respecting cycles. |
| `metrics.py` | In/out degree & strength; reciprocity + round-trip value; integrator–broadcaster index; rich club; 3-node motifs; (P1) time-respecting short cycles. |
| `nulls.py` | Degree-preserving rewiring (igraph `rewire`, 5–10 samples); z-scores; time-box + hub-capped fallback. |
| `detect.py` | Account labels; unsupervised rankings + combined z-score; heuristic baseline; per-pattern heatmap; PR-AUC, recall@k, lift. |
| `brain.py` | Fetch FlyWire `Connectivity_783.parquet` by URL; threshold ≥5 synapses; run the same metrics for the brain-vs-money comparison. |

---

## 3. Phase-by-phase plan

Legend: `[ ]` todo · `[~]` in progress · `[x]` done.

### P0 · Setup (M0) — local + Kaggle
- [ ] Scaffold repo: structure above, `pyproject.toml`, `requirements.txt`, `.gitignore`, pytest config.
- [ ] Module stubs with docstrings for all six `moneyconn/` files.
- [ ] `load.py`: compact-dtype loader + patterns-file parser.
- [ ] Toy fixtures + first tests wired so `pytest` runs green locally.
- [ ] `kaggle_01_build_graph.ipynb` skeleton with the AML dataset attached; `pip install` the package from GitHub.
- **AC:** loader reads ~5.08M rows; laundering share ≈ 0.1%; peak RAM logged; degree distributions plotted.

### P1 · Graph (M1) — local logic, Kaggle run
- [ ] `graph.py`: aggregate to directed weighted edges → parquet checkpoint; build igraph; keep raw timestamped edge list.
- [ ] Toy-graph tests for graph build.
- **AC:** ~515k accounts; **Σ edge counts == #transactions**; parquet saved; graph-build tests green. (Structure-only; no FX yet.)

### P2 · Metrics (M2) — local logic, Kaggle run
- [ ] `metrics.py`: in/out degree & strength, reciprocity (+ round-trip value), integrator–broadcaster index, rich club, 3-node motifs.
- [ ] `nulls.py`: degree-preserving rewiring + z-scores; time-box; hub-capped fallback (drop top 0.1% by degree) reported alongside the full graph.
- [ ] Toy tests green: **3-cycle, star, reciprocal pair** with known answers.
- **AC:** ≥5 metrics computed on the full graph with degree-preserving nulls, or a documented fallback.

### P3 · Detection (M3) — local logic, Kaggle run
- [ ] `detect.py`: account labels (1 if account sends/receives any laundering tx); unsupervised rankings per metric + combined z-score; heuristic baseline (total amount, #counterparties, #payment formats); per-pattern heatmap (8 patterns × metrics, assigned patterns only); PR-AUC, recall@k (k=100/1k/10k), lift.
- [ ] **Headline figure:** patterns × metrics heatmap → `reports/figures/`.
- [ ] Write the first verdict.
- **AC (success):** ≥1 metric shows ≥5× top-1% lift on ≥2 pattern types **and** beats the heuristic baseline on ≥1; blind spots documented.

### P4 · Brain vs money (M4) — Kaggle (internet on)
- [ ] `brain.py`: fetch FlyWire parquet, threshold ≥5 synapses (sanity: reciprocity ≈ 0.14), run the same metrics.
- [ ] Comparison figure + table: brain / money / degree-preserving nulls.
- [ ] *(P1)* Time-respecting short cycles (2–4 hops).
- [ ] *(P1)* LightGBM supervised lift: time-based split (first ~70% of tx for training), graph features built from the **training window only** (no leakage); basic vs basic+connectome features, bootstrap CIs.
- **AC:** one figure answering "is money more like a brain or a random network?"

### P5 · Publish (M5) — local + free clouds
- [ ] Streamlit "Account X-ray" demo: pick a flagged account → 2-hop network, its metrics vs population, true pattern if any. Precomputed top-500 neighborhoods, <50 MB / <1 GB RAM.
- [ ] README with the headline heatmap.
- [ ] Make the Kaggle notebook public; confirm dataset license first.
- [ ] Project page on gaaprojects.github.io + one LinkedIn post.

---

## 4. Baked-in decisions & gotchas (don't rediscover)

- Account ID = `f"{bank}_{account}"`; second `Account` column loads as `Account.1`.
- Use **`python-igraph`** (C-backed), not networkx, for the 5M-edge scale.
- Per-pattern analysis uses **only pattern-assigned** laundering rows; overall metrics use all labels.
- Nulls/motifs: **time-box**, then fall back to a hub-capped subgraph and report **both** versions.
- Supervised step builds graph features from the **training window only** (label-leakage guard).
- Link to the Kaggle dataset rather than re-uploading it; share only small derived aggregates.
- Brain data (FlyWire v783) is **CC BY-NC 4.0** — non-commercial portfolio use with attribution.

---

## 5. Success metrics (spec §9)

- Account-level PR-AUC, recall@k (100/1k/10k), lift over random.
- Per-pattern detection heatmap.
- Runtime and peak RAM per step (G1: full HI-Small on Kaggle CPU ≤ 60 min, peak RAM ≤ 20 GB).
- **Stretch:** conclusions hold on LI-Small (harder, lower illicit ratio).

---

## 6. Immediate next step

**P0 scaffolding**, all local and safe on the laptop:
1. Create repo structure + `pyproject.toml` / `requirements.txt` / `.gitignore` / pytest config.
2. Module stubs with docstrings.
3. Implement `load.py` + toy fixtures + first passing test.
4. Draft `kaggle_01_build_graph.ipynb` skeleton.

Then point `kaggle_01` at the real dataset and confirm the P0 acceptance criteria.
