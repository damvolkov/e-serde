---
hide:
  - navigation
  - toc
---

<div class="rx-hero">
  <img src="assets/eserde-banner.svg" alt="e-serde">
  <p>Fast, type-safe structured-data loading for Python. Native <strong>Rust</strong>
  codecs decode any popular config format into native objects — or straight into frozen
  <code>msgspec</code> models. Two verbs, sync and async, one wheel.</p>
</div>

<div class="rx-grid">
  <div><h3>Rust-fast</h3><p>JSON via <code>msgspec</code> (C); YAML, TOML, JSONC, INI via Rust. GIL released during decode.</p></div>
  <div><h3>Type-safe</h3><p>Pass <code>type=</code> and the tree is validated into a Struct, dataclass or TypedDict by msgspec.</p></div>
  <div><h3>json-semantics</h3><p><code>loads/dumps/load/dump</code> plus <code>a</code>-prefixed async twins. Drop-in feel, no surprises.</p></div>
  <div><h3>Seven formats</h3><p>JSON · JSONC · YAML · TOML · INI · CSV · TSV. Format autodetected from the path extension.</p></div>
</div>

## Install

```bash
uv add e-serde          # or: pip install e-serde
```

## First load

```python
import eserde
from pathlib import Path

eserde.loads(b'{"host": "0.0.0.0", "port": 8080}', format=eserde.Format.JSON)
# {'host': '0.0.0.0', 'port': 8080}

eserde.loads(Path("config.toml"))          # format inferred from .toml
```

[Get started →](introduction.md)
