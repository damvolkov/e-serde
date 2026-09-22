# JSONC

> **Spec:** Deno jsonc: JSON + comments + trailing commas
> **Engine:** `jsonc-parser` 0.33
> **Backend:** `NativeJsoncCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | yes | first-class `None` |
| `.inf` / `.nan` floats | — | outside this format's contract |
| integers beyond 64-bit | yes | exact round-trip |
| comments | yes | accepted on load |
| trailing array commas | yes | accepted |
| anchors & aliases (`&x` / `*x`) | — | outside this format's contract |
| merge keys (`<<`) | — | outside this format's contract |
| leading UTF-8 BOM | — | outside this format's contract |
| repeated `[section]` blocks | — | outside this format's contract |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b'{"k": 1} // why', format=Format.JSONC)
# {'k': 1}   — the comment is metadata, not data
```

## Limits and guarantees

- `//` and `/* */` comments and trailing commas are accepted on load, dropped on dump — comments are not data.
- A leading BOM is rejected, like plain JSON.
- Non-finite floats serialize to `null`, like JSON.

Back to [all formats](index.md).
