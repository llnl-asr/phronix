"""Pin a task list, and load the instances it names.

The task list is a committed file of instance ids, not a query evaluated at run
time. Two reasons, both about the comparison being meaningful:

* **Every arm must see the same sequence.** The learning arm's task N depends on
  1..N-1; comparing it against an arm that saw a different order compares
  nothing.
* **Runs weeks apart must be comparable.** A dataset that gains or reorders rows
  upstream would silently change what "the benchmark" means.

Selection is seeded and stratified by repository, so a 30-task subset is not
thirty variations of one codebase — which would make cross-repo skill reuse
impossible to observe, and that is one of the metrics.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SPLITS = {
    "lite": ("princeton-nlp/SWE-bench_Lite", "test"),
    "verified": ("princeton-nlp/SWE-bench_Verified", "test"),
    "full": ("princeton-nlp/SWE-bench", "test"),
}


class DatasetUnavailable(RuntimeError):
    """The SWE-bench dataset could not be loaded."""


def load_instances(split: str = "lite",
                   cache_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load a SWE-bench split as ``{instance_id: instance}``.

    Prefers a local JSONL cache so a run does not depend on the network, and so a
    machine without egress can still replay a pinned task list.
    """
    if cache_dir:
        cached = Path(cache_dir) / f"{split}.jsonl"
        if cached.is_file():
            out: Dict[str, Dict[str, Any]] = {}
            for line in cached.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    out[record["instance_id"]] = record
            return out

    if split not in SPLITS:
        raise DatasetUnavailable(f"unknown split {split!r}; known: {', '.join(SPLITS)}")
    name, subset = SPLITS[split]
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise DatasetUnavailable(
            "the `datasets` package is needed to fetch SWE-bench. Install it with "
            "`PIP_EXTRA_INDEX_URL= pip install datasets`, or point --dataset-cache "
            "at a directory holding <split>.jsonl.") from exc

    try:
        data = load_dataset(name, split=subset)
    except Exception as exc:
        raise DatasetUnavailable(f"could not load {name}: {exc}") from exc
    return {row["instance_id"]: dict(row) for row in data}


def cache_instances(instances: Dict[str, Dict[str, Any]], cache_dir: Path,
                    split: str) -> Path:
    """Write a split to local JSONL so later runs need no network."""
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{split}.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in instances.values():
            handle.write(json.dumps(record) + "\n")
    return path


def select(instances: Dict[str, Dict[str, Any]], limit: int = 30,
           seed: int = 0, stratify: bool = True) -> List[str]:
    """Choose *limit* instance ids, seeded and reproducible.

    Stratified round-robin across repositories by default. An unstratified sample
    of SWE-bench Lite is dominated by django and sympy, and a run where almost
    every task shares a codebase cannot show cross-repo skill reuse — the metric
    that distinguishes a genuinely transferable lesson from one that memorised a
    single project's layout.
    """
    rng = random.Random(seed)
    ids = sorted(instances)
    if not stratify:
        rng.shuffle(ids)
        return ids[:limit]

    by_repo: Dict[str, List[str]] = {}
    for instance_id in ids:
        by_repo.setdefault(instances[instance_id].get("repo", "?"), []).append(instance_id)
    for bucket in by_repo.values():
        rng.shuffle(bucket)

    repos = sorted(by_repo)
    rng.shuffle(repos)
    chosen: List[str] = []
    while len(chosen) < limit and any(by_repo.values()):
        for repo in repos:
            if by_repo[repo] and len(chosen) < limit:
                chosen.append(by_repo[repo].pop())
    return chosen


def write_task_file(path: Path, ids: Iterable[str], split: str, seed: int,
                    instances: Optional[Dict[str, Dict[str, Any]]] = None) -> Path:
    """Write the pinned list, with a header recording how it was produced.

    The header is what makes the file auditable a year later: without the split
    and seed, a task list is a bag of ids nobody can regenerate or justify.
    """
    ids = list(ids)
    digest = hashlib.sha256("\n".join(ids).encode()).hexdigest()[:12]
    lines = [
        f"# SWE-bench {split} — {len(ids)} instances, seed {seed}, stratified by repo",
        f"# checksum {digest}",
        "# Order is significant: the learning arm's task N benefits from 1..N-1,",
        "# so every arm must run this sequence exactly as written.",
    ]
    if instances:
        repos = sorted({instances[i].get("repo", "?") for i in ids if i in instances})
        lines.append(f"# repositories: {', '.join(repos)}")
    lines += ["", *ids, ""]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path


def read_task_file(path: Path) -> List[str]:
    """Read a pinned list, preserving order and ignoring comments."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"task list not found: {path}")
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]
