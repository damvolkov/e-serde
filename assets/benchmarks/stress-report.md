# Concurrency stress report

Throughput in decodes/s on 32 cores; `eff` = best throughput ÷ single-worker.

## JSON · 100kb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| stdlib-json | 1343 | 1496 | x1.1 | 49.0 ms | GIL-bound plateau |
| simplejson | 2076 | 2076 | x1.0 | 0.5 ms | GIL-bound plateau |
| ujson | 3582 | 3582 | x1.0 | 0.3 ms | GIL-bound plateau |
| orjson | 3822 | 4253 | x1.1 | 5.5 ms | GIL-bound plateau |
| msgspec | 5722 | 5722 | x1.0 | 0.2 ms | GIL-bound plateau |
| e-serde | 5266 | 5266 | x1.0 | 0.3 ms | GIL-bound plateau |
| e-serde·async | 3309 | 3309 | x1.0 | 0.4 ms | GIL-bound plateau |

## JSON · 10mb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| stdlib-json | 14 | 15 | x1.0 | 148.7 ms | GIL-bound plateau |
| simplejson | 17 | 17 | x1.0 | 58.7 ms | GIL-bound plateau |
| ujson | 20 | 20 | x1.0 | 51.3 ms | GIL-bound plateau |
| orjson | 28 | 28 | x1.0 | 36.5 ms | GIL-bound plateau |
| msgspec | 31 | 31 | x1.0 | 35.1 ms | GIL-bound plateau |
| e-serde | 33 | 33 | x1.0 | 32.0 ms | GIL-bound plateau |
| e-serde·async | 30 | 30 | x1.0 | 27.5 ms | GIL-bound plateau |

## JSONC · 100kb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| json5 | — | — | — | — | skipped: serial cost beyond budget |
| pyjson5 | 2347 | 2384 | x1.0 | 6.3 ms | GIL-bound plateau |
| e-serde | 1229 | 2192 | x1.8 | 1.4 ms | GIL-bound plateau |
| e-serde·async | 1101 | 1330 | x1.2 | 16.4 ms | GIL-bound plateau |

## JSONC · 10mb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| json5 | — | — | — | — | skipped: serial cost beyond budget |
| pyjson5 | 18 | 18 | x1.0 | 59.1 ms | GIL-bound plateau |
| e-serde | 9 | 13 | x1.4 | 276.1 ms | GIL-bound plateau |
| e-serde·async | 9 | 12 | x1.3 | 340.5 ms | GIL-bound plateau |

## YAML · 100kb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| pyyaml | 68 | 68 | x1.0 | 23.9 ms | GIL-bound plateau |
| ruamel | — | — | — | — | skipped: serial cost beyond budget |
| e-serde | 290 | 1387 | x4.8 | 9.5 ms | sub-linear growth |
| e-serde·async | 251 | 775 | x3.1 | 35.0 ms | sub-linear growth |

## YAML · 10mb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| pyyaml | 0 | 0 | x1.0 | 2794.6 ms | GIL-bound plateau |
| ruamel | — | — | — | — | skipped: serial cost beyond budget |
| e-serde | 2 | 8 | x3.4 | 795.4 ms | sub-linear growth |
| e-serde·async | 2 | 7 | x3.1 | 960.9 ms | sub-linear growth |

## TOML · 100kb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| stdlib-tomllib | 109 | 109 | x1.0 | 16.6 ms | GIL-bound plateau |
| tomli | 163 | 167 | x1.0 | 23.8 ms | GIL-bound plateau |
| rtoml | 420 | 424 | x1.0 | 16.4 ms | GIL-bound plateau |
| tomlkit | 13 | 13 | x1.0 | 103.9 ms | GIL-bound plateau |
| e-serde | 616 | 1420 | x2.3 | 6.6 ms | sub-linear growth |
| e-serde·async | 472 | 1063 | x2.3 | 16.0 ms | sub-linear growth |

## TOML · 10mb

| decoder | ops/s @1 | ops/s peak | eff | p99 @ peak | verdict |
| --- | --- | --- | --- | --- | --- |
| stdlib-tomllib | 1 | 1 | x1.0 | 952.2 ms | GIL-bound plateau |
| tomli | 2 | 2 | x1.0 | 612.3 ms | GIL-bound plateau |
| rtoml | 0 | 0 | x1.0 | 6963.7 ms | GIL-bound plateau |
| tomlkit | — | — | — | — | skipped: serial cost beyond budget |
| e-serde | 3 | 8 | x2.3 | 898.0 ms | sub-linear growth |
| e-serde·async | 4 | 8 | x2.2 | 910.8 ms | sub-linear growth |
