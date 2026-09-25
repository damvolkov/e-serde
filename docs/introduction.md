# Introduction

e-serde is part of the **Eager** (`e-`) stack by [damvolkov](https://github.com/damvolkov) —
a family of local-first, production-grade components. e-serde is its serialization layer.

## Why

Python has never lacked config loaders; it lacks a *fast, type-safe, uniform* one. The
usual options are either a pure-Python parser that is easy but slow, or a fast C/Rust
codec that is quick but format-specific and typing-optional. Choosing formats means
choosing a different API and a different failure mode per format.

e-serde's thesis: take the **speed and robustness of C and Rust** — the same engines
that already power the fastest JSON and TOML libraries — and put them behind one
small surface, so a config file becomes a validated Python object with a single call.

## Built with open-source models

The codecs are not reimplemented here; they are the state of the art, wrapped:

| Concern      | Engine                                   | Language |
| ------------ | ---------------------------------------- | -------- |
| JSON decode  | msgspec                                  | C        |
| YAML         | saphyr (YAML 1.2 core schema)            | Rust     |
| TOML         | toml (toml-rs org)                       | Rust     |
| JSONC        | jsonc-parser (from Deno)                 | Rust     |
| INI          | rust-ini                                 | Rust     |
| CSV · TSV    | csv (BurntSushi)                         | Rust     |
| Validation   | msgspec.convert (Structs/dataclasses)    | C        |

Everything Rust lives in a single PyO3 extension module, compiled by `maturin`, released
as prebuilt wheels. The only runtime dependency is `msgspec`.

## What it is not

- Not a config *framework* — no env vars, no layering, no schema registry. It decodes bytes
  into objects. Reach for that on top if you need it.
- Not losslessly round-trippable for every format by design: JSONC comments are dropped on
  dump, TOML has no null, YAML rejects non-scalar keys. These limits are explicit, not
  surprising.

Next: [Installation →](installation.md)
