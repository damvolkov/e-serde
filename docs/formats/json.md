# JSON

> **Spec:** RFC 8259
> **Engine:** `msgspec.json` 0.21
> **Backend:** `MsgspecJsonCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | yes | first-class `None` |
| `.inf` / `.nan` floats | — | outside this format's contract |
| integers beyond 64-bit | yes | exact round-trip |
| comments | — | outside this format's contract |
| trailing array commas | — | outside this format's contract |
| anchors & aliases (`&x` / `*x`) | — | outside this format's contract |
| merge keys (`<<`) | — | outside this format's contract |
| leading UTF-8 BOM | — | outside this format's contract |
| repeated `[section]` blocks | — | outside this format's contract |
| `iloads`/`idumps` record streaming | yes | one record at a time, never the whole document |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b'{"k": null}', format=Format.JSON)
# {'k': None}
```

## Limits and guarantees

- Strict RFC 8259: `NaN` / `Infinity` tokens and comments are rejected on load.
- `dumps` maps non-finite floats to `null` (JSON has no other honest option).

Back to [all formats](index.md).
