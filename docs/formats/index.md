# Formats

e-serde speaks five config formats through five pinned engines. Each page states the **spec**
implemented, the **engine** behind it — exact version, enforced against the lockfiles by the
test-suite — and the **capabilities** that can be relied on.

| Format | Spec | Engine | Version |
| --- | --- | --- | --- |
| [JSON](json.md) | RFC 8259 | `msgspec.json` | 0.21 |
| [JSONC](jsonc.md) | Deno jsonc: JSON + comments + trailing commas | `jsonc-parser` | 0.33 |
| [YAML](yaml.md) | YAML 1.2 core schema, plus the 1.1 merge key | `saphyr` | 0.0.12 |
| [TOML](toml.md) | TOML v1.1 | `toml (toml-rs)` | 1.1 |
| [INI](ini.md) | de-facto INI: sections of string key/value, no interpolation | `rust-ini` | 0.21 |

The capability contract lives in code — `eserde.STANDARDS` — and every claim is executed
against the live codecs by `test_standards.py`. The pages below mirror that contract.
