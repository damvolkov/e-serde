"""Report trigger: pytest-benchmark JSON -> grouped bar charts + compact markdown table.

Run after a benchmark session (`make bench` renders automatically):

    uv run python tests/benchmark/report.py .benchmark/bench.json .benchmark

One PNG per matrix (loads, dumps, typed, async, memory): x = rival, grouped bars =
payload size, log scale, speedups annotated against the reference row at 100 KB.
Partial runs degrade gracefully: absent matrices are simply not rendered.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from math import isfinite
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

_SIZE_ORDER = ("1kb", "100kb", "10mb")
_FORMAT_ORDER = ("json", "jsonc", "yaml", "toml", "ini")
_COLORS = {"1kb": "#b8c9e0", "100kb": "#5b82b8", "10mb": "#1d3a5f", "": "#5b82b8"}
_REFERENCE_SIZE = "100kb"
_BASE_CANDIDATES = ("e-serde", "e-serde:plain", "loads-bytes")
_PREFERRED = {
    "test_loads_typed": (
        "e-serde:plain",
        "e-serde:struct",
        "e-serde:dataclass",
        "msgspec:struct",
        "pydantic:orjson",
        "pydantic:pyyaml",
        "pydantic:rtoml",
    ),
    "test_aloads": ("loads-bytes", "aloads-bytes", "loads-file", "aloads-file"),
}
# test key -> (figure name, ylabel, size where the speedup annotations live)
_FIGURES = {
    "test_loads": ("loads.png", "median [ms]", _REFERENCE_SIZE),
    "test_dumps": ("dumps.png", "median [ms]", _REFERENCE_SIZE),
    "test_loads_typed": ("typed.png", "median [ms]", _REFERENCE_SIZE),
    "test_aloads": ("async.png", "median [ms] (8 workers)", "10mb"),
    "test_loads_peak:mem": ("memory.png", "tracemalloc peak [KiB]", _REFERENCE_SIZE),
}

type Rivals = dict[str, float]
type Matrix = dict[str, dict[str, Rivals]]  # format -> size -> rival -> value


def _index(benchmarks: list[dict[str, Any]]) -> dict[str, Matrix]:
    table: dict[str, Matrix] = defaultdict(dict)
    for entry in benchmarks:
        params: dict[str, str] = entry.get("params") or {}
        rival = params.get("rival") or params.get("drive")
        if "fmt" not in params or "size" not in params or rival is None:
            continue
        test = entry["name"].split("[", 1)[0]
        sizes = table[test].setdefault(params["fmt"], {})
        sizes.setdefault(params["size"], {})[rival] = entry["stats"]["median"] * 1000
        if extra := entry.get("extra_info"):
            memory = table[f"{test}:mem"].setdefault(params["fmt"], {})
            memory.setdefault(params["size"], {})[rival] = extra["peak_kib"]
    return table


def _formats(matrix: Matrix) -> list[str]:
    present = set(matrix)
    return [f for f in _FORMAT_ORDER if f in present] + sorted(present - set(_FORMAT_ORDER))


def _rivals(by_size: dict[str, Rivals], preferred: tuple[str, ...], base: str) -> list[str]:
    seen = {rival for rivals in by_size.values() for rival in rivals}
    ordered = [name for name in preferred if name in seen]
    ordered += sorted(seen - set(ordered))
    if base in ordered and base.startswith("e-serde"):
        ordered.remove(base)
        ordered.append(base)
    return ordered


def _panel(
    ax: plt.Axes,
    fmt: str,
    by_size: dict[str, Rivals],
    *,
    base: str,
    ylabel: str,
    preferred: tuple[str, ...],
    ref: str,
) -> None:
    sizes = [size for size in _SIZE_ORDER if size in by_size]
    rivals = _rivals(by_size, preferred, base)
    width = 0.82 / max(len(sizes), 1)
    offset = -0.41 + width / 2
    base_ms = by_size.get(ref, {}).get(base)
    for size in sizes:
        values = by_size[size]
        heights = [values.get(rival, float("nan")) for rival in rivals]
        ax.bar(
            [tick + offset for tick in range(len(rivals))], heights, width=width * 0.9, color=_COLORS[size], label=size
        )
        if size == ref and base_ms:
            for tick, rival, height in zip(range(len(rivals)), rivals, heights, strict=True):
                if isfinite(height) and rival != base:
                    ax.annotate(
                        f"×{height / base_ms:.1f}",
                        (tick + offset, height * 1.06),
                        ha="center",
                        fontsize=6,
                        color="#333333",
                    )
        offset += width
    ax.set_yscale("log")
    ax.set_title(fmt, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=8)
    ax.set_xticks(range(len(rivals)), rivals, rotation=38, ha="right", fontsize=7)
    ax.grid(axis="y", which="major", alpha=0.2)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6, loc="upper left")


def _figure(test: str, matrix: Matrix, path: Path, ylabel: str, ref: str) -> None:
    formats = _formats(matrix)
    preferred = _PREFERRED.get(test, ())
    present = {rival for by_size in matrix.values() for rivals in by_size.values() for rival in rivals}
    base = next((name for name in _BASE_CANDIDATES if name in present), "")
    fig, axes = plt.subplots(1, len(formats), figsize=(4.6 * len(formats), 4.0), squeeze=False)
    for ax, fmt in zip(axes[0], formats, strict=True):
        _panel(ax, fmt, matrix[fmt], base=base, ylabel=ylabel, preferred=preferred, ref=ref)
    fig.suptitle(f"{test.replace('test_', '').replace(':mem', '')} — {ylabel} (× = vs {base} @ {ref})", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _table(test: str, matrix: Matrix, ref: str) -> list[str]:
    present = {rival for by_size in matrix.values() for rivals in by_size.values() for rival in rivals}
    base = next((name for name in _BASE_CANDIDATES if name in present), "")
    lines = [
        f"## {test.replace('test_', '').replace(':mem', ': memory')} @ {ref}",
        "",
        f"| format | rival | median | vs `{base}` |",
        "|---|---|---|---|",
    ]
    for fmt in _formats(matrix):
        speeds = matrix[fmt].get(ref, {})
        reference = speeds.get(base)
        for rival, ms in sorted(speeds.items(), key=lambda item: item[1]):
            ratio = f"×{ms / reference:.2f}" if reference else ""
            lines.append(f"| {fmt} | {rival} | {ms:.4f} | {ratio} |")
    lines.append("")
    return lines


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Render e-serde benchmark report from pytest-benchmark JSON.")
    parser.add_argument("bench_json", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args(argv[1:])

    table = _index(json.loads(args.bench_json.read_text(encoding="utf-8"))["benchmarks"])
    args.out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# e-serde benchmark report",
        "",
        "Lower is better. × is the ratio against the reference row (e-serde, or the sync path for async).",
        "",
    ]
    for test, (name, ylabel, ref) in _FIGURES.items():
        if matrix := table.get(test):
            _figure(test, matrix, args.out_dir / name, ylabel, ref)
            lines += _table(test, matrix, ref)
    (args.out_dir / "report.md").write_text("\n".join(lines))
    written = ", ".join(sorted(path.name for path in args.out_dir.glob("*.png")))
    sys.stdout.write(f"report rendered -> {args.out_dir} ({written}, report.md)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
