# LinkedIn post — copy-paste ready

> Paste as-is. First comment (optional): the per-format contract docs.

---

🚀 Just released: e-serde — fast, type-safe config loading for Python, on native Rust codecs.

Five formats, one door: JSON · JSONC · YAML · TOML · INI
Six verbs with `json`-module manners: loads / dumps / load / dump + async twins

import eserde
cfg = eserde.loads(Path("config.toml"))
srv = eserde.loads(Path("prod.yaml"), type=Server)  # decode in Rust, validate with msgspec

⚡ Numbers (100 KB, CPython 3.14):
• YAML 5.3× faster than PyYAML-C
• TOML 1.4× faster than rtoml
• INI 10× faster than configparser
• JSONC: pyjson5 beats us ×0.6 — it's in the README, no chart dodging 📊

🧠 What I'm proudest of:
→ STANDARDS: every format's spec claims (YAML 1.2 core, TOML v1.1, RFC 8259) live in code and are executed by the test suite. An engine bump that broke null semantics went red on CI the same day.
→ Billion-laughs YAML bombs rejected in ~0 ms instead of eating your RAM.
→ Concurrency that scales: Rust codecs release the GIL → ~2× on 10 MB YAML across cores, while GIL-bound rivals flat-line at ×1.0.
→ Drop-in interop: json-compatible façade, pydantic/attrs validation, per-call encoder hooks.

🔒 Built 100% with local open-weight models on local hardware. No cloud APIs, no telemetry — the tool that serializes your config shouldn't phone home, and neither should the hands that wrote it.

🐍 Wheels on PyPI for Linux / macOS / Windows (cp314):
📦 Repo: https://github.com/damvolkov/e-serde
📖 Docs: https://damvolkov.github.io/e-serde/

Feedback and uncomfortable critiques welcome — agreement must be earned. 🤝

#python #rust #opensource #serialization #performance #localai #config #msgspec
