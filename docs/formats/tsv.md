# TSV

> **Spec:** RFC 4180 dialect: tab-delimited
> **Engine:** `csv` 1.4
> **Backend:** `NativeTsvCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | yes | first-class `None` |
| `.inf` / `.nan` floats | yes | round-trip exactly |
| integers beyond 64-bit | yes | exact round-trip |
| comments | — | outside this format's contract |
| trailing array commas | — | outside this format's contract |
| anchors & aliases (`&x` / `*x`) | — | outside this format's contract |
| merge keys (`<<`) | — | outside this format's contract |
| leading UTF-8 BOM | yes | stripped |
| repeated `[section]` blocks | — | outside this format's contract |
| `iloads`/`idumps` record streaming | yes | one record at a time, never the whole document |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b'id\tname\n1\tTurul\n', format=Format.TSV)
# [{'id': 1, 'name': 'Turul'}]   — same codec, tab-delimited
```

## Limits and guarantees

- Tab is the only difference from CSV — quoted fields may still contain tabs.
- Same header, null, ragged and inference rules as CSV.

Back to [all formats](index.md).
