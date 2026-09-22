# YAML

> **Spec:** YAML 1.2 core schema, plus the 1.1 merge key
> **Engine:** `saphyr` 0.0.12
> **Backend:** `NativeYamlCodec`

## Capabilities

| Feature | Supported | Behaviour |
| --- | --- | --- |
| `null` values | yes | first-class `None` |
| `.inf` / `.nan` floats | yes | round-trip exactly |
| integers beyond 64-bit | — | outside this format's contract |
| comments | yes | accepted on load |
| trailing array commas | yes | accepted |
| anchors & aliases (`&x` / `*x`) | yes | resolved, budget-guarded |
| merge keys (`<<`) | yes | resolved; explicit keys win |
| leading UTF-8 BOM | yes | stripped |
| repeated `[section]` blocks | — | outside this format's contract |

## Example

```python
import eserde
from eserde import Format

eserde.loads(b"base: &b {x: 1}\ndoc:\n  <<: *b\n  y: 2\n", format=Format.YAML)
# {'base': {'x': 1}, 'doc': {'y': 2, 'x': 1}}
```

## Limits and guarantees

- Core schema only: `yes`/`no`/`on`/`off` are strings; timestamps are not typed — datetimes are ISO **strings** on both ends.
- Integers beyond 64 bits resolve to `float` on load (engine limitation); dumps write exact digits, so PyYAML-style readers still round-trip.
- Multi-document streams are rejected: one document per load.
- Exponential alias expansion (billion laughs) is rejected by a materialization budget instead of eating the machine.

Back to [all formats](index.md).
