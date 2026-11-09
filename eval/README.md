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
# week 3 (see the pre-registration below):
python -m eval.build_label_set --since 2026-11-10 --until <build date> --exclude eval/candidates-2026-11-03.json --exclude eval/candidates-2026-11-09.json
python -m eval.evaluate --train 2026-11-03 2026-11-09 --test <build date>
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

## Week 2 (2026-11-09): hold-out result

34 candidates, window 2026-11-04 to 2026-11-09; must 15, maybe 8, skip 11; 6 without abstract,
of which 1 is a must-read (P23). M1 and M4 trained on week-1 labels only.
`python -m eval.evaluate --train 2026-11-03 --test 2026-11-09`

| Method | P@4 | P@10 | skip@10 | NDCG | must pct (abstract) | must pct (no abstract) |
|---|---|---|---|---|---|---|
| M0 current keyword scorer | 0.75 | 0.60 | 1 | 0.932 | 0.294 | 0.970 |
| M1 MiniLM centroid | 1.00 | 0.80 | 1 | 0.965 | 0.245 | 0.848 |
| M2 MiniLM scope text | 0.50 | 0.70 | 2 | 0.879 | 0.390 | 0.212 |
| M3 SPECTER scope text | 0.75 | 0.60 | 2 | 0.922 | 0.353 | 0.667 |
| M4 MiniLM centroid + scope | 1.00 | 0.80 | 1 | 0.954 | 0.266 | 0.545 |
| random order (mean) | 0.44 | 0.44 | 3.2 | 0.798 | 0.499 | 0.499 |

**Decision, by the rule as written.** Candidate: M1 (highest NDCG among M1 to M4).
Condition 1 passes (NDCG 0.965 > 0.932, skip@10 1 = 1). Condition 2 is **undetermined**: only 1
no-abstract must-read, fewer than the required 3. Undetermined is not passed, so **M0 stays**.

Not evidence for any decision (n = 1), but noted: M0 and M1 both put the one no-abstract
must-read near the bottom of the list (percentiles 0.97 and 0.85); only M2 did not (0.21).

## Week 3: pre-registered hold-out test (fixed 2026-11-09, before week-3 data exists)

**Why the change.** Week 2 could not decide on abstract neutrality. Both the keyword scorer and
the embedding methods probably favour papers with more text: fewer words give fewer keyword
hits, and a title-only embedding sits away from a centroid built from title-plus-abstract text.
The labeller's view (2026-11-09): an abstract is a nice-to-have, and a title usually says
what a paper is about. So the rule now asks that a new method be no less fair than the
current scorer, rather than meeting an absolute bar, and M5 tests ranking on titles alone.
This was decided after seeing week-2 results, under which M1 would pass the new form of the check;
that is why week 3 is scored on fresh data only and week 2 is never pooled into the test.

**Data.** Built with `build_label_set.py` on or after 2026-11-16, window from 2026-11-10 to the
build date, excluding week-1 and week-2 DOIs. Labelled blind before `evaluate.py` is run on it.

**Methods.** M0 to M4 unchanged (same code and `SCOPE` text as week 2). New: M5, the MiniLM
centroid with every paper (training and test) embedded from its title only. M1, M4 and M5 learn
from week-1 and week-2 labels. No edits to methods after week-3 labels exist.

**Metrics.** As week 2, plus the *neutral gap*: for each must-read or maybe without an abstract,
its rank percentile minus the mean percentile of papers with an abstract and the same label;
the gap is the mean of these (positive = pushed down). `evaluate.py` prints it.

**Decision rule.** Among M1 to M5, the candidate is the method with the highest NDCG on week 3. Adopt it only if:

1. its NDCG beats M0's and its skip@10 is no worse than M0's (week 3 only);
2. its neutral gap is no larger than M0's. The check needs at least 3 no-abstract must-read or
   maybe papers. If week 3 has fewer, build and label week 4 the same way and pool the per-paper
   deviations of weeks 3 and 4 (`--test <week 3> <week 4>`); condition 1 still uses week 3 alone.
   If the pool still has fewer than 3, the check is undetermined, not passed.

Ties (within 0.01 NDCG) prefer fewer requirements: scope text over centroid, MiniLM over SPECTER,
and M5 over M1 (titles are always present). If no method passes, keep M0 and revisit.

**Exploratory, week-2 data (seen while writing this; not evidence).** On week 2, M5 scored NDCG
0.935 and neutral gap 0.191, against M0 0.932 / 0.468 and M1 0.965 / 0.154 (n = 3). Ranking on
titles alone did not remove the gap there, which hints that papers without abstracts may also
have less descriptive titles (for example, conference records). Week 3 tests this properly.
