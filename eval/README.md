# Ranking evaluation

Blind, labelled weekly snapshots for choosing how the digest ranks papers.

## Files

| File | What it is |
|---|---|
| `candidates-<date>.json` | Frozen candidate set: full records plus each paper's rank under the pipeline scorer at build time. Never edit. |
| `labels-<date>.csv` | Labeller's judgement per paper: `must`, `maybe` or `skip`, made from a shuffled sheet with no scores shown. |
| `build_label_set.py` | Fetches a window of candidates and writes the two files above. |
| `evaluate.py` | Scores the pre-registered methods against a labelled set. |

`evaluate.py` needs `sentence-transformers` (installed in the local `xray-digest` conda env).
It is not in `requirements.txt` because the weekly workflow does not use it.

```powershell
conda activate xray-digest
python -m eval.build_label_set --since 2026-11-04 --until 2026-11-10 --exclude eval/candidates-2026-11-03.json
python -m eval.evaluate --train 2026-11-03 --test 2026-11-10
```

## Week 1 (2026-11-03): exploratory

38 candidates, window 2026-10-20 to 2026-11-03; must 20, maybe 10, skip 8; 12 without abstract.
The label-based method was scored leave-one-out.

| Method | P@4 | P@10 | skip@10 | NDCG |
|---|---|---|---|---|
| M0 current keyword scorer | 0.75 | 0.60 | 4 | 0.887 |
| M1 MiniLM centroid | 0.75 | 0.80 | 1 | 0.944 |
| M2 MiniLM scope text | 1.00 | 0.80 | 1 | 0.939 |
| M3 SPECTER scope text | 0.75 | 0.80 | 1 | 0.933 |
| M4 MiniLM centroid + scope | 0.75 | 0.70 | 2 | 0.938 |
| random order (mean of 2000) | 0.52 | 0.53 | 2.1 | 0.849 |

Week 1 chose the candidate methods, and the scope text was written after seeing these labels,
so these numbers are optimistic. They are not evidence for adopting any method.

## Week 2: pre-registered hold-out test (fixed 2026-11-03, before week-2 data exists)

**Data.** Built with `build_label_set.py` on or after 2026-11-10, window from 2026-11-04 to the
build date, excluding week-1 DOIs. Labelled blind, the same way as week 1, before `evaluate.py` is run on it.

**Methods.** Exactly M0 to M4 as implemented in `evaluate.py` at the commit that adds this file,
including the `SCOPE` text. M1 and M4 learn from week-1 labels only. No edits to the methods or
the scope text after week-2 labels exist; any new idea is a new method for week 3.

**Metrics.** Gain must = 2, maybe = 1, skip = 0. Primary: NDCG over the full list.
Secondary: P@4 (the report's size), P@10, skip@10. Abstract-neutrality: the mean rank percentile
of must-reads without an abstract minus the mean for must-reads with one (positive = papers
without an abstract are pushed down).

**Decision rule.** Among M1 to M4, the candidate is the method with the highest NDCG. Adopt it only if:

1. its NDCG beats M0's and its skip@10 is no worse than M0's;
2. abstract-neutrality (labeller's decision, option b, 2026-11-03): no-abstract must-reads sit no
   more than 0.10 rank percentile below must-reads with an abstract. If week 2 has fewer than 3
   no-abstract must-reads, this check is recorded as undetermined, not passed.

If two methods are within 0.01 NDCG, prefer the one with fewer requirements: scope text (needs no
labels) over centroid, and MiniLM (about 90 MB) over SPECTER. If no method passes, keep M0 and revisit.

**Deviation (recorded 2026-11-09, before labelling).** The labeller chose to build the set on
2026-11-09, one day before the pre-registered earliest date, so the window is 2026-11-04 to
2026-11-09 (files `*-2026-11-09`). Nothing else changed: same methods, scope text, metrics and rule.
The build gave 34 candidates, 6 without an abstract. The cost is a slightly smaller window;
the set was still built and frozen before any week-2 label existed.

**Known limits.** One hold-out week of about 40 papers can separate "clearly better than M0" from
"no better", not close variants from one another. M0's week-2 order comes from the scorer at build
time, which no longer gives Crossref papers invented topics (commit 5ee3cb8), so M0 differs slightly
from week 1. Labels only judge papers the search returned; recall of the search is a separate question.
