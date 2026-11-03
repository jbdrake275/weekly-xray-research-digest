"""Score the pre-registered ranking methods against blind labels.

Usage (from the repo root, in an env with sentence-transformers):
    # Week-1 exploratory numbers (leave-one-out for the label-based method):
    python -m eval.evaluate --test 2026-11-03
    # Hold-out test: label-based methods learn from week 1 only, scored on week 2:
    python -m eval.evaluate --train 2026-11-03 --test 2026-11-10

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


def embed(model, papers):
    sep = model.tokenizer.sep_token or " "
    texts = [p["title"] + (f" {sep} {p['abstract']}" if p["abstract"] else "") for p in papers]
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


def metrics(scores, y, has_abstract):
    order = np.argsort(-scores, kind="stable")
    g = y[order]
    dcg = lambda gains: sum((2.0**x - 1) / math.log2(k + 2) for k, x in enumerate(gains))
    # Option (b) check: where do must-reads land, as a rank percentile (0 = top), with vs without abstract?
    pct = np.empty(len(y))
    pct[order] = np.arange(len(y)) / max(1, len(y) - 1)
    must = y == 2
    return {
        "P@4": float(np.mean(g[:4] == 2)),
        "P@10": float(np.mean(g[:10] == 2)),
        "skip@10": int(np.sum(g[:10] == 0)),
        "NDCG": dcg(g) / dcg(sorted(y, reverse=True)),
        "must pct (abs)": float(pct[must & has_abstract].mean()) if (must & has_abstract).any() else float("nan"),
        "must pct (no abs)": float(pct[must & ~has_abstract].mean()) if (must & ~has_abstract).any() else float("nan"),
    }


def main() -> None:
    from sentence_transformers import SentenceTransformer

    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--test", required=True, help="Date stamp of the set to score, e.g. 2026-11-10.")
    parser.add_argument("--train", help="Date stamp of the labels the centroid learns from; omit for leave-one-out.")
    args = parser.parse_args()

    test, y = load(args.test)
    has_abstract = np.array([bool(p["abstract"]) for p in test])
    train, y_train = load(args.train) if args.train else (test, y)
    loo = args.train is None

    results = {"M0 current keyword scorer": -np.array([p["current_rank"] for p in test], float)}
    for short, name in MODELS.items():
        model = SentenceTransformer(name)
        E = embed(model, test)
        E_train = E if loo else embed(model, train)
        scope = E @ model.encode([SCOPE], normalize_embeddings=True)[0]
        if short == "MiniLM":
            centroid = centroid_score(E, E_train, y_train, loo)
            results["M1 MiniLM centroid"] = centroid
            results["M2 MiniLM scope text"] = scope
            results["M4 MiniLM centroid + scope"] = zscore(centroid) + zscore(scope)
        else:
            results["M3 SPECTER scope text"] = scope

    rng = random.Random(0)
    table = {name: metrics(s, y, has_abstract) for name, s in results.items()}
    draws = [metrics(np.array(rng.sample(range(len(y)), len(y)), float), y, has_abstract) for _ in range(2000)]
    table["random order (mean)"] = {k: float(np.nanmean([d[k] for d in draws])) for k in draws[0]}

    mode = "leave-one-out" if loo else f"trained on {args.train}"
    print(f"test set {args.test}: n={len(y)} (must {np.sum(y == 2)}, maybe {np.sum(y == 1)}, skip {np.sum(y == 0)}), "
          f"{np.sum(~has_abstract)} without abstract; centroid {mode}")
    cols = list(next(iter(table.values())))
    print(f"{'method':<28}" + "".join(f"{c:>18}" for c in cols))
    for name, m in table.items():
        print(f"{name:<28}" + "".join(f"{m[c]:>18.3f}" if isinstance(m[c], float) else f"{m[c]:>18}" for c in cols))


if __name__ == "__main__":
    main()
