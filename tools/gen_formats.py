"""Regenerate docs/formats/*.md from the eserde.STANDARDS contract.

Run via `make docs-formats` after changing standards.py; test_standards checks the pages are not stale.
"""

import pathlib
import sys

from eserde import STANDARDS, Feature, Format

LIMITS = {
    Format.JSON: [
        "Strict RFC 8259: `NaN` / `Infinity` tokens and comments are rejected on load.",
        "`dumps` maps non-finite floats to `null` (JSON has no other honest option).",
    ],
    Format.JSONC: [
        "`//` and `/* */` comments and trailing commas are accepted on load, dropped on dump — comments are not data.",
        "A leading BOM is rejected, like plain JSON.",
        "Non-finite floats serialize to `null`, like JSON.",
    ],
    Format.YAML: [
        "Core schema only: `yes`/`no`/`on`/`off` are strings; timestamps are not typed — datetimes are ISO **strings** on both ends.",
        "Integers beyond 64 bits resolve to `float` on load (engine limitation); dumps write exact digits, so PyYAML-style readers still round-trip.",
        "Multi-document streams are rejected: one document per load.",
        "Exponential alias expansion (billion laughs) is rejected by a materialization budget instead of eating the machine.",
    ],
    Format.CSV: [
        "Header required: the first row names the columns; records decode to `list[dict]`.",
        "Empty fields are `null`; ragged rows are rejected, never padded.",
        "Mixed kinds demote a column to strings (polars semantics); a float in an integer column widens it to doubles, big integers stay exact only while the column is integral.",
    ],
    Format.TSV: [
        "Tab is the only difference from CSV — quoted fields may still contain tabs.",
        "Same header, null, ragged and inference rules as CSV.",
    ],
    Format.TOML: [
        "No null type: `None` cannot be encoded.",
        "Integers are 64-bit by spec: values beyond `i64` raise `DumpError` rather than corrupt.",
        "Native datetimes are decoded to ISO strings, matching the dump encoder policy.",
    ],
    Format.INI: [
        "Values are strings — pass `type=` with `strict=False` to coerce via msgspec.",
        "Nested structures cannot be represented; `dumps` raises on them.",
        "No interpolation, no general-section inheritance, by design.",
        "Repeated sections merge (configparser semantics): later keys win, siblings survive.",
    ],
}
DESC = {
    Feature.NULL: ("`null` values", "first-class `None`"),
    Feature.NONFINITE: ("`.inf` / `.nan` floats", "round-trip exactly"),
    Feature.BIGNUM: ("integers beyond 64-bit", "exact round-trip"),
    Feature.COMMENTS: ("comments", "accepted on load"),
    Feature.TRAILING_COMMAS: ("trailing array commas", "accepted"),
    Feature.STREAM: ("`iloads`/`idumps` record streaming", "one record at a time, never the whole document"),
    Feature.ANCHORS: ("anchors & aliases (`&x` / `*x`)", "resolved, budget-guarded"),
    Feature.MERGE_KEYS: ("merge keys (`<<`)", "resolved; explicit keys win"),
    Feature.BOM_TOLERANT: ("leading UTF-8 BOM", "stripped"),
    Feature.MERGE_DUP_SECTIONS: ("repeated `[section]` blocks", "merged"),
}
BACKEND = {
    Format.JSON: "MsgspecJsonCodec",
    Format.JSONC: "NativeJsoncCodec",
    Format.YAML: "NativeYamlCodec",
    Format.TOML: "NativeTomlCodec",
    Format.INI: "NativeIniCodec",
    Format.CSV: "NativeCsvCodec",
    Format.TSV: "NativeTsvCodec",
}
ABSENT = "outside this format's contract"


def snippet(fmt: Format) -> str:
    return {
        Format.JSON: "eserde.loads(b'{\"k\": null}', format=Format.JSON)\n# {'k': None}",
        Format.JSONC: "eserde.loads(b'{\"k\": 1} // why', format=Format.JSONC)\n# {'k': 1}   — the comment is metadata, not data",
        Format.YAML: "eserde.loads(b\"base: &b {x: 1}\\ndoc:\\n  <<: *b\\n  y: 2\\n\", format=Format.YAML)\n# {'base': {'x': 1}, 'doc': {'y': 2, 'x': 1}}",
        Format.TOML: "eserde.loads(b'speed = inf\\n', format=Format.TOML)\n# {'speed': inf}   — and .nan survives the round-trip",
        Format.INI: "eserde.loads(b\"[s]\\nport = 8080\\n\", format=Format.INI, type=dict[str, Svc], strict=False)\n# {'s': Svc(port=8080)}   — strings coerced by the schema",
        Format.CSV: "eserde.loads(b'id,name\\n1,Turul\\n', format=Format.CSV)\n# [{'id': 1, 'name': 'Turul'}]   — records with per-column inference",
        Format.TSV: "eserde.loads(b'id\\tname\\n1\\tTurul\\n', format=Format.TSV)\n# [{'id': 1, 'name': 'Turul'}]   — same codec, tab-delimited",
    }[fmt]


index = [
    "# Formats",
    "",
    "e-serde speaks every format through its own pinned engine. Each page states the **spec**",
    "implemented, the **engine** behind it — exact version, enforced against the lockfiles by the",
    "test-suite — and the **capabilities** that can be relied on.",
    "",
    "| Format | Spec | Engine | Version |",
    "| --- | --- | --- | --- |",
]
for fmt in Format:
    s = STANDARDS[fmt]
    index.append(f"| [{fmt.value.upper()}]({fmt.value}.md) | {s.spec} | `{s.engine}` | {s.version} |")
index += [
    "",
    "The capability contract lives in code — `eserde.STANDARDS` — and every claim is executed",
    "against the live codecs by `test_standards.py`. The pages below mirror that contract.",
    "",
]
pathlib.Path("docs/formats/index.md").write_text("\n".join(index))

for fmt in Format:
    s = STANDARDS[fmt]
    lines = [
        f"# {fmt.value.upper()}",
        "",
        f"> **Spec:** {s.spec}",
        f"> **Engine:** `{s.engine}` {s.version}",
        f"> **Backend:** `{BACKEND[fmt]}`",
        "",
        "## Capabilities",
        "",
        "| Feature | Supported | Behaviour |",
        "| --- | --- | --- |",
    ]
    for feature in Feature:
        name, how = DESC[feature]
        state = "yes" if feature in s.features else "—"
        behaviour = how if feature in s.features else ABSENT
        lines.append(f"| {name} | {state} | {behaviour} |")
    lines += [
        "",
        "## Example",
        "",
        "```python",
        "import eserde",
        "from eserde import Format",
        "",
        snippet(fmt),
        "```",
        "",
        "## Limits and guarantees",
        "",
    ]
    lines += [f"- {t}" for t in LIMITS[fmt]]
    lines += ["", "Back to [all formats](index.md).", ""]
    pathlib.Path(f"docs/formats/{fmt.value}.md").write_text("\n".join(lines))

sys.stdout.write(f"generated {len(list(pathlib.Path('docs/formats').glob('*.md')))} pages\n")
