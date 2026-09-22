# TOML

> **Spec:** TOML v1.1
> **Engine:** `toml (toml-rs)` 1.1
> **Backend:** `NativeTomlCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | — | outside this format's contract |
| `.inf` / `.nan` floats | yes | round-trip exactly |
| integers beyond 64-bit | — | outside this format's contract |
| comments | yes | accepted on load |
| trailing array commas | yes | accepted |
| anchors & aliases (`&x` / `*x`) | — | outside this format's contract |
| merge keys (`<<`) | — | outside this format's contract |
| leading UTF-8 BOM | yes | stripped |
| repeated `[section]` blocks | — | outside this format's contract |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b'speed = inf\n', format=Format.TOML)
# {'speed': inf}   — and .nan survives the round-trip
```

## Limits and guarantees

- No null type: `None` cannot be encoded.
- Integers are 64-bit by spec: values beyond `i64` raise `DumpError` rather than corrupt.
- Native datetimes are decoded to ISO strings, matching the dump encoder policy.

Back to [all formats](index.md).
