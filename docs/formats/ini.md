# INI

> **Spec:** de-facto INI: sections of string key/value, no interpolation
> **Engine:** `rust-ini` 0.21
> **Backend:** `NativeIniCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | — | outside this format's contract |
| `.inf` / `.nan` floats | — | outside this format's contract |
| integers beyond 64-bit | — | outside this format's contract |
| comments | yes | accepted on load |
| trailing array commas | — | outside this format's contract |
| anchors & aliases (`&x` / `*x`) | — | outside this format's contract |
| merge keys (`<<`) | — | outside this format's contract |
| leading UTF-8 BOM | yes | stripped |
| repeated `[section]` blocks | yes | merged |
| `iloads`/`idumps` record streaming | — | outside this format's contract |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b"[s]\nport = 8080\n", format=Format.INI, type=dict[str, Svc], strict=False)
# {'s': Svc(port=8080)}   — strings coerced by the schema
```

## Limits and guarantees

- Values are strings — pass `type=` with `strict=False` to coerce via msgspec.
- Nested structures cannot be represented; `dumps` raises on them.
- No interpolation, no general-section inheritance, by design.
- Repeated sections merge (configparser semantics): later keys win, siblings survive.

Back to [all formats](index.md).
