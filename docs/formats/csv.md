# CSV

> **Spec:** RFC 4180: headered records as `list[dict]`, polars-style per-column type inference
> **Engine:** `csv` 1.4
> **Backend:** `NativeCsvCodec`

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

eserde.loads(b'id,name\n1,Turul\n', format=Format.CSV)
# [{'id': 1, 'name': 'Turul'}]   — records with per-column inference
```

## Limits and guarantees

- Header required: the first row names the columns; records decode to `list[dict]`.
- Empty fields are `null`; ragged rows are rejected, never padded.
- Mixed kinds demote a column to strings (polars semantics); a float in an integer column widens it to doubles, big integers stay exact only while the column is integral.

Back to [all formats](index.md).
