"""Comparative concurrency stress: who scales, who plateaus, who collapses.

Not a speed benchmark — a capacity sweep. Each decoder runs under growing
concurrency (thread-pool workers; for e-serde, also asyncio fan-out) and we record
throughput, time-to-result tails (queue wait included) and peak RSS until the
library hits its asymptote: the GIL, oversubscription collapse, or memory.

Output: assets/benchmarks/stress-{format}.png + assets/benchmarks/stress-report.md
Run: make stress
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from benchmark.payloads import payload  # noqa: E402
from benchmark.rivals import LOAD_RIVALS  # noqa: E402
from eserde import Format, aloads  # noqa: E402

type Decoder = Callable[[bytes], Any]

SIZES: dict[str, dict[str, Any]] = {
    "100kb": {"n": 192, "rounds": 3, "knees": (1, 2, 4, 8, 16, 32, 48, 64), "sweep_budget_s": 150.0},
    "10mb": {"n": 8, "rounds": 2, "knees": (1, 4, 8, 16, 32), "sweep_budget_s": 120.0},
}
COLLAPSE_RATIO = 0.8
MIN_VERDICT_POINTS = 3
SCALE_EFFICIENCY = 6.0
SUBLINEAR_EFFICIENCY = 2.0


def rss_mib() -> float:
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return float(line.split()[1]) / 1024
    return -1.0


class _Peak:
    def __init__(self) -> None:
        self._value = rss_mib()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._watch, daemon=True)

    def _watch(self) -> None:
        while not self._stop.is_set():
            self._value = max(self._value, rss_mib())
            time.sleep(0.02)

    def __enter__(self) -> _Peak:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join()

    @property
    def value(self) -> float:
        return self._value


@dataclass(frozen=True, slots=True)
class Sample:
    ops_s: float
    p50_ms: float
    p99_ms: float
    rss_mib: float


def _summarize(latencies: list[float], wall: float, count: int, rss: float) -> Sample:
    latencies.sort()
    return Sample(
        count / wall,
        latencies[len(latencies) // 2] * 1000,
        latencies[max(0, int(len(latencies) * 0.99) - 1)] * 1000,
        rss,
    )


def run_threads(decode: Decoder, data: bytes, count: int, workers: int) -> Sample:
    latencies: list[float] = []

    def timed(_: int) -> None:
        start = time.perf_counter()
        decode(data)
        latencies.append(time.perf_counter() - start)

    with _Peak() as peak:
        wall_start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(timed, range(count)))
        wall = time.perf_counter() - wall_start
    return _summarize(latencies, wall, count, peak.value)


def run_gather(fmt: Format, data: bytes, count: int, workers: int) -> Sample:
    latencies: list[float] = []

    async def main() -> None:
        semaphore = asyncio.Semaphore(workers)

        async def gated() -> None:
            async with semaphore:
                start = time.perf_counter()
                await aloads(data, format=fmt)
                latencies.append(time.perf_counter() - start)

        await asyncio.gather(*(gated() for _ in range(count)))

    with _Peak() as peak:
        wall_start = time.perf_counter()
        asyncio.run(main())
        wall = time.perf_counter() - wall_start
    return _summarize(latencies, wall, count, peak.value)


def verdict(points: dict[int, Sample]) -> str:
    knees = sorted(points)
    base = points[knees[0]].ops_s
    mid_key = knees[len(knees) // 2]
    best = max(sample.ops_s for sample in points.values())
    ratio = best / base
    grew = ratio > SCALE_EFFICIENCY / 2
    collapsed = (
        grew and len(knees) >= MIN_VERDICT_POINTS and points[knees[-1]].ops_s < points[mid_key].ops_s * COLLAPSE_RATIO
    )
    match (ratio >= SCALE_EFFICIENCY, ratio >= SUBLINEAR_EFFICIENCY, collapsed):
        case (True, _, False):
            return "scales with cores"
        case (False, True, False):
            return "sub-linear growth"
        case (_, _, True):
            return "collapses under oversubscription"
        case _:
            return "GIL-bound plateau"


def sweep() -> dict[str, dict[str, dict[str, dict[int, Sample]]]]:
    results: dict[str, dict[str, dict[str, dict[int, Sample]]]] = {}
    for fmt in Format:
        if fmt is Format.INI:
            continue
        per_size: dict[str, dict[str, dict[int, Sample]]] = {}
        for size, cfg in SIZES.items():
            data = payload(fmt, size)
            curves: dict[str, dict[int, Sample]] = {}
            for label, decode in LOAD_RIVALS[fmt].items():
                probe = run_threads(decode, data, 1, 1)
                predicted_s = cfg["n"] / probe.ops_s * len(cfg["knees"]) * cfg["rounds"] / 4
                if predicted_s > cfg["sweep_budget_s"]:
                    curves[label] = {}
                else:
                    curves[label] = {k: run_threads(decode, data, cfg["n"], k) for k in cfg["knees"]}
                sys.stdout.write(
                    f"{fmt.value:6} {label:16} {size:6} {'skipped' if not curves[label] else verdict(curves[label]) if len(curves[label]) > 1 else 'ok'}\n"
                )
            curves["e-serde·async"] = {k: run_gather(fmt, data, cfg["n"], k) for k in cfg["knees"]}
            sys.stdout.write(f"{fmt.value:6} {'e-serde·async':16} {size:6} {verdict(curves['e-serde·async'])}\n")
            per_size[size] = curves
        results[fmt.value] = per_size
    return results


def chart(fmt_value: str, size: str, curve: dict[str, dict[int, Sample]]) -> None:
    usable = {name: points for name, points in curve.items() if len(points) > 1}
    if not usable:
        return
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    for name, points in usable.items():
        knees = sorted(points)
        ax.plot(
            knees,
            [points[k].ops_s for k in knees],
            marker="o",
            linewidth=2.4 if name.startswith("e-serde") else 1.3,
            label=name,
        )
    ax.set_xscale("log", base=2)
    ax.set_xticks(sorted({k for points in usable.values() for k in points}))
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlabel("concurrency (workers)")
    ax.set_ylabel("throughput [decodes/s]")
    ax.set_title(f"{fmt_value} · {size}")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "assets" / "benchmarks" / f"stress-{fmt_value}-{size}.png", dpi=150)
    plt.close(fig)


def report(results: dict[str, dict[str, dict[str, dict[int, Sample]]]]) -> None:
    lines = [
        "# Concurrency stress report",
        "",
        f"Throughput in decodes/s on {os.cpu_count()} cores; `eff` = best throughput ÷ single-worker.",
        "",
    ]
    for fmt_value, per_size in results.items():
        for size, curve in per_size.items():
            lines += [
                f"## {fmt_value.upper()} · {size}",
                "",
                "| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for name, points in curve.items():
                if not points:
                    lines.append(f"| {name} | — | — | — | — | skipped: serial cost beyond budget |")
                    continue
                knees = sorted(points)
                peak_knee = max(knees, key=lambda k: points[k].ops_s)
                eff = points[peak_knee].ops_s / points[knees[0]].ops_s
                lines.append(
                    f"| {name} | {points[knees[0]].ops_s:.0f} | {points[peak_knee].ops_s:.0f} | x{eff:.1f} | {points[peak_knee].p99_ms:.1f} ms | {verdict(points)} |"
                )
            lines.append("")
    (ROOT / "assets" / "benchmarks" / "stress-report.md").write_text("\n".join(lines))


def main() -> int:
    results = sweep()
    dump = {
        f: {
            s: {n: {str(k): [v.ops_s, v.p50_ms, v.p99_ms, v.rss_mib] for k, v in c.items()} for n, c in curves.items()}
            for s, curves in sizes.items()
        }
        for f, sizes in results.items()
    }
    (ROOT / "assets" / "benchmarks" / "stress-results.json").write_text(__import__("json").dumps(dump, indent=1))
    for fmt_value, per_size in results.items():
        for size, curve in per_size.items():
            chart(fmt_value, size, curve)
    report(results)
    sys.stdout.write("stress artifacts -> assets/benchmarks/stress-*\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
