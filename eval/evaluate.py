"""Score the pre-registered ranking methods against blind labels.

Usage (from the repo root, in an env with sentence-transformers):
    # Week-1 exploratory numbers (leave-one-out for the label-based method):
    python -m eval.evaluate --test 2026-11-03
    # Week-2 hold-out (as run 2026-11-09): label-based methods learn from week 1 only:
    python -m eval.evaluate --train 2026-11-03 --test 2026-11-09
    # Week-3 hold-out: learn from weeks 1 and 2; a second --test stamp pools the
    # abstract-neutrality check (week 4) when week 3 alone has too few papers:
    python -m eval.evaluate --train 2026-11-03 2026-11-09 --test <week-3 stamp> [<week-4 stamp>]

The methods, scope text, metrics and decision rule are fixed in eval/README.md and
must not be edited after the hold-out labels exist.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from pathlib import Path

import numpy as np

EVAL_DIR = Path(__file__).parent
GAIN = {"must": 2, "must-read": 2, "maybe": 1, "skip": 0}

# Frozen 2026-11-03, written from the user's stated scope. It was drafted after seeing the
# week-1 labels, so its week-1 numbers are optimistic; week 2 is its clean test.
SCOPE = (
    "Research that advances how X-ray or synchrotron measurements are made, modelled, or analysed: "
    "X-ray and synchrotron sources, detectors, optics, imaging physics, computed tomography, "
    "reconstruction, simulation, phase contrast, spectroscopy such as X-ray photoelectron spectroscopy, "
    "and fundamental X-ray science; plus applications of X-ray CT to materials, manufacturing, "
    "defects, and industrial inspection or nondestructive evaluation."
)
MODELS = {"MiniLM": "all-MiniLM-L6-v2", "SPECTER": "allenai-specter"}


def load(stamp: str):
    papers = json.loads((EVAL_DIR / f"candidates-{stamp}.json").read_text(encoding="utf-8"))["papers"]
    rows = list(csv.reader((EVAL_DIR / f"labels-{stamp}.csv").open(encoding="utf-8-sig")))[1:]
    labels = {r[0]: GAIN[r[1].strip().lower()] for r in rows}
    missing = [p["id"] for p in papers if p["id"] not in labels]
    if missing:
        sys.exit(f"labels-{stamp}.csv is missing labels for {missing}")
    return papers, np.array([labels[p["id"]] for p in papers])


def load_many(stamps):
    papers, ys = [], []
    for stamp in stamps:
        ps, y = load(stamp)
        papers += ps
        ys.append(y)
    return papers, np.concatenate(ys)


def embed(model, papers, titles_only: bool = False):
    sep = model.tokenizer.sep_token or " "
    texts = [p["title"] + (f" {sep} {p['abstract']}" if p["abstract"] and not titles_only else "") for p in papers]
    return model.encode(texts, normalize_embeddings=True)


def centroid_score(E_test, E_train, y_train, loo: bool):
    # Similarity to the average must-read minus similarity to the average skip.
    S = E_test @ E_train.T
    scores = []
    for i in range(len(E_test)):
        keep = np.ones(len(E_train), bool)
        if loo:
            keep[i] = False
        scores.append(S[i, keep & (y_train == 2)].mean() - S[i, keep & (y_train == 0)].mean())
    return np.array(scores)


def zscore(x):
    return (x - x.mean()) / (x.std() or 1.0)


def percentiles(scores):
    order = np.argsort(-scores, kind="stable")
    pct = np.empty(len(scores))
    pct[order] = np.arange(len(scores)) / max(1, len(scores) - 1)
    return pct


def neutrality_deviations(scores, y, has_abstract):
    """Week-3 abstract-neutrality check (label-matched, must and maybe).

    For each must or maybe paper without an abstract: its rank percentile (0 = top) minus the
    mean percentile of papers with an abstract and the same label. Positive = pushed down.
    Deviations are computed within one week's list, so they can be pooled across weeks.
    """
    pct = percentiles(scores)
    out = []
    for gain in (2, 1):
        ref = y == gain
        if not (ref & has_abstract).any():
            continue
        base = pct[ref & has_abstract].mean()
        out += list(pct[ref & ~has_abstract] - base)
    return out


def metrics(scores, y, has_abstract):
    order = np.argsort(-scores, kind="stable")
    g = y[order]
    dcg = lambda gains: sum((2.0**x - 1) / math.log2(k + 2) for k, x in enumerate(gains))
    # Option (b) check: where do must-reads land, as a rank percentile (0 = top), with vs without abstract?
    pct = percentiles(scores)
    must = y == 2
    dev = neutrality_deviations(scores, y, has_abstract)
    return {
        "P@4": float(np.mean(g[:4] == 2)),
        "P@10": float(np.mean(g[:10] == 2)),
        "skip@10": int(np.sum(g[:10] == 0)),
        "NDCG": dcg(g) / dcg(sorted(y, reverse=True)),
        "must pct (abs)": float(pct[must & has_abstract].mean()) if (must & has_abstract).any() else float("nan"),
        "must pct (no abs)": float(pct[must & ~has_abstract].mean()) if (must & ~has_abstract).any() else float("nan"),
        "neutral gap": float(np.mean(dev)) if dev else float("nan"),
    }


def score_week(test, y, train, y_train, loo, models):
    """All methods' scores for one week's candidate list."""
    results = {"M0 current keyword scorer": -np.array([p["current_rank"] for p in test], float)}
    for short, model in models.items():
        E = embed(model, test)
        E_train = E if loo else embed(model, train)
        scope = E @ model.encode([SCOPE], normalize_embeddings=True)[0]
        if short == "MiniLM":
            centroid = centroid_score(E, E_train, y_train, loo)
            results["M1 MiniLM centroid"] = centroid
            results["M2 MiniLM scope text"] = scope
            results["M4 MiniLM centroid + scope"] = zscore(centroid) + zscore(scope)
            # Added 2026-11-09 for week 3: every paper embedded from its title alone, so a
            # missing abstract cannot shift where it lands (no length bias by construction).
            T = embed(model, test, titles_only=True)
            T_train = T if loo else embed(model, train, titles_only=True)
            results["M5 MiniLM title-only centroid"] = centroid_score(T, T_train, y_train, loo)
        else:
            results["M3 SPECTER scope text"] = scope
    return results


def print_table(table):
    cols = list(next(iter(table.values())))
    print(f"{'method':<30}" + "".join(f"{c:>17}" for c in cols))
    for name, m in table.items():
        print(f"{name:<30}" + "".join(f"{m[c]:>17.3f}" if isinstance(m[c], float) else f"{m[c]:>17}" for c in cols))


def main() -> None:
    from sentence_transformers import SentenceTransformer

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--test", nargs="+", required=True,
                        help="Date stamp(s) of the set(s) to score. Metrics are per week; extra weeks pool the neutrality check.")
    parser.add_argument("--train", nargs="+", help="Date stamp(s) of the labels the centroids learn from; omit for leave-one-out.")
    args = parser.parse_args()

    models = {short: SentenceTransformer(name) for short, name in MODELS.items()}
    train, y_train = load_many(args.train) if args.train else (None, None)
    loo = args.train is None
    mode = "leave-one-out" if loo else f"trained on {' + '.join(args.train)}"
    pooled = {}
    for stamp in args.test:
        test, y = load(stamp)
        has_abstract = np.array([bool(p["abstract"]) for p in test])
        results = score_week(test, y, *(train, y_train) if not loo else (test, y), loo, models)
        rng = random.Random(0)
        table = {name: metrics(s, y, has_abstract) for name, s in results.items()}
        draws = [metrics(np.array(rng.sample(range(len(y)), len(y)), float), y, has_abstract) for _ in range(2000)]
        table["random order (mean)"] = {k: float(np.nanmean([d[k] for d in draws])) for k in draws[0]}
        for name, s in results.items():
            pooled.setdefault(name, []).extend(neutrality_deviations(s, y, has_abstract))
        n_check = int(np.sum(~has_abstract & (y >= 1)))
        print(f"test set {stamp}: n={len(y)} (must {np.sum(y == 2)}, maybe {np.sum(y == 1)}, skip {np.sum(y == 0)}), "
              f"{np.sum(~has_abstract)} without abstract ({n_check} must/maybe); centroids {mode}")
        print_table(table)
        print()
    if len(args.test) > 1:
        print(f"pooled neutrality gap over {' + '.join(args.test)}:")
        for name, dev in pooled.items():
            print(f"  {name:<30} {np.mean(dev):>7.3f}  (n={len(dev)})")


if __name__ == "__main__":
    main()
