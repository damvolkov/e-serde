# e-serde: a config loader that takes typing, speed and your machine seriously

> Copy-paste ready for Substack. Links: repo → https://github.com/damvolkov/e-serde · docs → https://damvolkov.github.io/e-serde/

---

Every few months I catch myself rebuilding the same wheel: read a YAML here, a TOML there, an old INI nobody dares touch, validate it into a model, and ship. The Python ecosystem has all the pieces — `msgspec`, `orjson`, `tomllib`, `PyYAML`, `configparser` — but it has never had a **single door**. Five APIs, five failure modes, five ways to silently corrupt the same tree depending on which library you happened to install first.

So I built the door. It's called **e-serde** — part of my `e-` (eager) stack — and it's now public:

- **Repo:** https://github.com/damvolkov/e-serde
- **Docs:** https://damvolkov.github.io/e-serde/

## What it is

Six functions with `json`-module manners — `loads`/`dumps`/`load`/`dump` plus async twins — that decode JSON, JSONC, YAML, TOML and INI into plain Python or **straight into a frozen `msgspec` model**. One wheel. Under the hood: Rust for YAML (saphyr), TOML (toml-rs), JSONC (Deno's jsonc-parser), INI (rust-ini), C for JSON (msgspec). Zero runtime dependencies beyond msgspec itself.

```python
import eserde

cfg = eserde.loads(Path("config.toml"))  # format from the extension, no ceremony


class Server(msgspec.Struct, frozen=True):
    host: str
    port: int


srv = eserde.loads(Path("prod.yaml"), type=Server)  # decode in Rust, validate in C
```

The async twins move both I/O **and** parsing off the event loop. Because the Rust codecs release the GIL, decoding parallelizes across cores: a fan-out of 10 MB YAML runs ~2× faster than the same work done serially. The JSON path — msgspec's C decoder holding the GIL — stays flat, and we say so in the docs. No chart dodging.

## What the numbers say

Median decode of a 100 KB config, CPython 3.14, release build:

| Format | e-serde | nearest rival | margin |
| --- | --- | --- | --- |
| JSON | 0.17 ms | orjson 0.16 ms | tie by construction — we *are* msgspec |
| YAML | 2.2 ms | PyYAML (C) 11.9 ms | 5.3× |
| TOML | 1.6 ms | rtoml 2.3 ms | 1.4× |
| INI | 1.9 ms | configparser 19 ms | 10× |
| JSONC | 0.7 ms | **pyjson5 0.4 ms** | we're behind, and it's in the README |

That last row matters. A benchmark suite you cannot lose with is a brochure, not an engineering tool. e-serde ships its rival matrix — twelve competitors, parametrized, with charts you can regenerate with `make bench`.

## The philosophy (the part that actually shaped the code)

**The contract over the convenience.** Every format publishes what it supports — YAML 1.2 core + merge keys, TOML v1.1, RFC 8259 — as machine-readable claims (`eserde.STANDARDS`) that the test suite executes against the live codecs. When a dependency bump tried to sneak a YAML regression past us (an engine that resolved empty nodes to `""` instead of `null`), CI went red on the exact cell, and the version got pinned with a comment. Silent drift is the failure mode of config libraries. We made it structurally impossible.

**Wrong is wrong, loudly.** Non-finite floats round-trip exactly in YAML and TOML; JSON maps them to `null` because JSON has no other honest option, and we document that too. A 200-digit integer stays exact or the library refuses; it will never hand you `1e+200` pretending it's the same number. Billion-laughs YAML bombs get rejected by an expansion budget in milliseconds instead of eating the machine's RAM. A lone surrogate raises `DumpError`, not a raw `UnicodeEncodeError`.

**Interop, not rivalry.** `eserde.compat` is a drop-in for anything that duck-types `json.dumps`; `type=` validates pydantic and attrs models; per-call `default=`/`encoders=`/`dec_hook=` hooks mean your exotic types never need a monkey-patch. We're not asking you to replace msgspec or pydantic — we're the I/O layer they didn't have.

**Built on open source, and honest about it.** The codecs are the ecosystem's own: saphyr, toml-rs, jsonc-parser, msgspec. We wrap the best instead of reinventing worse — and every engine version is pinned, tested and published with it.

## Built with local open-source models only

The whole project — code, tests, docs, benchmarks — was produced with **local, open-weight models running on local hardware**. No cloud API, no telemetry, no per-token invoice. The stack I build (speech runtimes, agents, this serde layer) runs on my machine, trained by the community, auditable by anyone. I consider that a feature with a moral dimension: the tool that serializes your config shouldn't need to phone home, and neither should the hands that wrote it.

## Get it

```bash
uv add e-serde        # or: pip install e-serde
```

Wheels for Linux (x86_64/aarch64), macOS (both) and Windows, CPython 3.14.

- Repo: https://github.com/damvolkov/e-serde
- Docs (per-format contracts, limits, examples): https://damvolkov.github.io/e-serde/

Issues and uncomfortable critiques welcome. Agreement must be earned.
