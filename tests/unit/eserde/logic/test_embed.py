"""Embedding contract: `.md` inlined as text, structured files as trees, every format, confined roots."""

from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar

import msgspec
import pytest

from eserde.backends.registry import build_default_registry
from eserde.infra.errors import FormatError, LoadError
from eserde.infra.formats import Format
from eserde.logic import embed as embed_mod
from eserde.logic.api import aload, aloads, dumps, load, loads


@pytest.fixture
def docs(tmp_path: Path) -> Path:
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "guia.md").write_text("# Guía\n\npaso 1\npaso 2\n", "utf-8")
    (tmp_path / "content" / "requisitos.md").write_text("- cpu\n- ram\n", "utf-8")
    (tmp_path / "binary.md").write_bytes(b"\xff\xfe not utf-8")
    return tmp_path


class _Doc(msgspec.Struct, frozen=True):
    title: str
    content: str


class _Db(msgspec.Struct, frozen=True):
    host: str
    port: int


class _Cfg(msgspec.Struct, frozen=True):
    db: _Db


async def test_yaml_pattern_full(docs: Path) -> None:
    (docs / "doc.yaml").write_text(
        "id: guia\n"
        "title: Guía de instalación\n"
        "content:\n"
        "  format: markdown\n"
        "  source: ./content/guia.md\n"
        "sections:\n"
        "  - id: requisitos\n"
        "    source: ./content/requisitos.md\n",
        "utf-8",
    )
    d = loads(docs / "doc.yaml", embed=True)
    assert d["content"]["source"].startswith("# Guía")
    assert d["content"]["format"] == "markdown"
    assert d["sections"][0]["source"] == "- cpu\n- ram\n"


@pytest.mark.parametrize("fmt", [Format.JSON, Format.YAML, Format.TOML])
def test_all_formats_inlines(docs: Path, fmt: Format) -> None:
    data = dumps({"source": "content/guia.md"}, format=fmt)
    out = loads(data, format=fmt, embed=True, root=docs)
    assert out["source"].startswith("# Guía")


def test_ini_inlines_under_section(docs: Path) -> None:
    data = dumps({"meta": {"source": "content/guia.md"}}, format=Format.INI)
    out = loads(data, format=Format.INI, embed=True, root=docs)
    assert out["meta"]["source"].startswith("# Guía")


async def test_embed_true_uses_default_key_and_custom_keys(docs: Path) -> None:
    data = dumps({"body": "content/guia.md", "source": "content/requisitos.md"}, format=Format.JSON)
    out = loads(data, format=Format.JSON, embed=("body",), root=docs)
    assert out["body"].startswith("# Guía")
    assert out["source"] == "content/requisitos.md"


def test_off_by_default(docs: Path) -> None:
    out = loads(b'{"source": "content/guia.md"}', format=Format.JSON, root=docs)
    assert out == {"source": "content/guia.md"}


def test_path_source_anchors_at_parent(docs: Path) -> None:
    (docs / "doc.json").write_text('{"source": "content/guia.md"}', "utf-8")
    out = load(docs / "doc.json", embed=True)
    assert out["source"].startswith("# Guía")


def test_absolute_path_inside_root(docs: Path) -> None:
    abs_ref = str(docs / "content" / "guia.md")
    out = loads(dumps({"source": abs_ref}, format=Format.JSON), format=Format.JSON, embed=True, root=docs)
    assert out["source"].startswith("# Guía")


def test_escape_outside_root_rejected(docs: Path) -> None:
    (docs.parent / "outside.md").write_text("nope", "utf-8")
    with pytest.raises(LoadError, match="escapes the document root"):
        loads('{"source": "../outside.md"}', format=Format.JSON, embed=True, root=docs)


def test_unknown_extension_rejected(docs: Path) -> None:
    with pytest.raises(LoadError, match=r"expected \.md or a structured format"):
        loads('{"source": "notes.txt"}', format=Format.JSON, embed=True, root=docs)


def test_declared_format_must_match_markdown(docs: Path) -> None:
    with pytest.raises(LoadError, match="sibling format declares 'rst'"):
        loads('{"source": "content/guia.md", "format": "rst"}', format=Format.JSON, embed=True, root=docs)


def test_missing_file_rejected(docs: Path) -> None:
    with pytest.raises(LoadError, match="not found"):
        loads('{"source": "content/nope.md"}', format=Format.JSON, embed=True, root=docs)


def test_non_utf8_rejected(docs: Path) -> None:
    with pytest.raises(LoadError, match="cannot embed"):
        loads('{"source": "binary.md"}', format=Format.JSON, embed=True, root=docs)


def test_oversized_rejected(docs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embed_mod, "MAX_EMBED_BYTES", 8)
    with pytest.raises(LoadError, match="too large"):
        loads('{"source": "content/guia.md"}', format=Format.JSON, embed=True, root=docs)


def test_bytes_source_without_root_raises() -> None:
    with pytest.raises(FormatError, match="root="):
        loads(b'{"source": "x.md"}', format=Format.JSON, embed=True)


def test_embedded_text_is_not_reprocessed(docs: Path) -> None:
    (docs / "content" / "evil.md").write_text('{"source": "content/guia.md"}', "utf-8")
    (docs / "content" / "holder.md").write_text("source: content/evil.md", "utf-8")
    out = loads('{"source": "content/holder.md"}', format=Format.JSON, embed=True, root=docs)
    assert out["source"] == "source: content/evil.md"


def test_typed_sees_embedded_text(docs: Path) -> None:
    out = loads(
        '{"title": "Guía", "content": "content/guia.md"}',
        format=Format.JSON,
        embed=("content",),
        root=docs,
        type=_Doc,
    )
    assert out.content.startswith("# Guía")


def test_object_hook_sees_embedded_values(docs: Path) -> None:
    seen: list[Any] = []
    loads(
        '{"source": "content/guia.md"}',
        format=Format.JSON,
        embed=True,
        root=docs,
        object_hook=lambda d: (seen.append(d.get("source")), d)[1],
    )
    assert any(v and v.startswith("# Guía") for v in seen)


async def test_aloads_path_anchor(docs: Path) -> None:
    (docs / "doc.yaml").write_text("source: content/guia.md\n", "utf-8")
    out = await aloads(docs / "doc.yaml", embed=True)
    assert out["source"].startswith("# Guía")


async def test_aload_handle_needs_root(docs: Path) -> None:
    (docs / "doc.toml").write_text('source = "content/guia.md"\n', "utf-8")
    with (docs / "doc.toml").open("rb") as fh:
        out = await aload(fh, format=Format.TOML, embed=True, root=docs)
    assert out["source"].startswith("# Guía")


def test_nonstring_under_key_walks_through(docs: Path) -> None:
    out = loads('{"source": {"nested": true}}', format=Format.JSON, embed=True, root=docs)
    assert out == {"source": {"nested": True}}


RESOURCES = Path(__file__).resolve().parents[3] / "resources"


def test_fixture_reference_untouched_without_embed() -> None:
    doc = load(RESOURCES / "sample_embed.json")
    assert doc["content"] == {"source": "./content/sample_embed.md"}


def test_fixture_embeds_companion_markdown() -> None:
    doc = load(RESOURCES / "sample_embed.json", embed=True)
    body = (RESOURCES / "content" / "sample_embed.md").read_text("utf-8")
    assert doc["content"]["source"] == body
    assert doc["content"]["source"].startswith("# Guía de instalación")
    assert "日本語" in doc["content"]["source"]


def test_fixture_embedding_leaves_rest_of_tree_intact() -> None:
    embedded = load(RESOURCES / "sample_embed.json", embed=True)
    plain = load(RESOURCES / "sample.json")
    rest = {k: v for k, v in embedded.items() if k != "content"}
    assert rest == plain


_TABULAR = frozenset({Format.CSV, Format.TSV})


def _payload(fmt: Format, value: Any) -> Any:
    match fmt:
        case Format.CSV | Format.TSV:
            return [{"id": 1, "source": value}]
        case _:
            return {"meta": {"source": value}}


def _sub_payload(fmt: Format) -> Any:
    match fmt:
        case Format.CSV | Format.TSV:
            return [{"id": 1, "name": "turul"}, {"id": 2, "name": "ainulindale"}]
        case _:
            return {"db": {"host": "localhost", "port": 5432}}


def _cell(out: Any, fmt: Format) -> Any:
    match fmt:
        case Format.CSV | Format.TSV:
            return out[0]["source"]
        case _:
            return out["meta"]["source"]


def _write(path: Path, obj: Any, fmt: Format) -> Path:
    path.write_bytes(dumps(obj, format=fmt))
    return path


@pytest.mark.parametrize("inner", list(Format), ids=str)
@pytest.mark.parametrize("outer", list(Format), ids=str)
def test_structured_matrix_embeds_tree(tmp_path: Path, outer: Format, inner: Format) -> None:
    sub = _write(tmp_path / f"sub.{inner.value}", _sub_payload(inner), inner)
    doc = _write(tmp_path / f"doc.{outer.value}", _payload(outer, sub.name), outer)
    out = load(doc, embed=True)
    assert _cell(out, outer) == load(sub)


@pytest.mark.parametrize("inner", list(Format), ids=str)
async def test_structured_async_twins(tmp_path: Path, inner: Format) -> None:
    sub = _write(tmp_path / f"sub.{inner.value}", _sub_payload(inner), inner)
    doc = _write(tmp_path / "doc.yaml", {"source": sub.name}, Format.YAML)
    assert (await aload(doc, embed=True))["source"] == load(sub)
    assert (await aloads(doc, embed=True))["source"] == load(sub)


def test_structured_from_bytes_with_root(tmp_path: Path) -> None:
    _write(tmp_path / "sub.toml", {"k": "v"}, Format.TOML)
    out = loads(b"source: sub.toml\n", format=Format.YAML, embed=True, root=tmp_path)
    assert out == {"source": {"k": "v"}}


def test_nested_references_resolve_against_their_document(tmp_path: Path) -> None:
    (tmp_path / "parts" / "text").mkdir(parents=True)
    (tmp_path / "parts" / "text" / "intro.md").write_text("# Intro\n", "utf-8")
    _write(tmp_path / "parts" / "leaf.json", {"leaf": True}, Format.JSON)
    _write(
        tmp_path / "parts" / "mid.yaml",
        {"body": {"source": "text/intro.md"}, "child": {"source": "leaf.json"}},
        Format.YAML,
    )
    (tmp_path / "doc.yaml").write_text("part:\n  source: parts/mid.yaml\n", "utf-8")
    out = load(tmp_path / "doc.yaml", embed=True)
    assert out == {"part": {"source": {"body": {"source": "# Intro\n"}, "child": {"source": {"leaf": True}}}}}


def test_custom_keys_recurse_into_sub_documents(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("A", "utf-8")
    _write(tmp_path / "sub.json", {"body": "a.md", "source": "a.md"}, Format.JSON)
    out = loads(b'{"body": "sub.json"}', format=Format.JSON, embed=("body",), root=tmp_path)
    assert out == {"body": {"body": "A", "source": "a.md"}}


def test_diamond_references_allowed(tmp_path: Path) -> None:
    _write(tmp_path / "shared.yaml", {"x": 1}, Format.YAML)
    _write(tmp_path / "left.json", {"source": "shared.yaml"}, Format.JSON)
    _write(tmp_path / "right.toml", {"source": "shared.yaml"}, Format.TOML)
    out = loads(
        b'{"l": {"source": "left.json"}, "r": {"source": "right.toml"}}',
        format=Format.JSON,
        embed=True,
        root=tmp_path,
    )
    assert out["l"]["source"] == out["r"]["source"] == {"source": {"x": 1}}


def test_self_cycle_rejected(tmp_path: Path) -> None:
    (tmp_path / "loop.yaml").write_text("source: loop.yaml\n", "utf-8")
    with pytest.raises(LoadError, match="embedding cycle"):
        load(tmp_path / "loop.yaml", embed=True)


def test_indirect_cycle_rejected(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("source: b.json\n", "utf-8")
    (tmp_path / "b.json").write_text('{"next": {"source": "./a.yaml"}}', "utf-8")
    with pytest.raises(LoadError, match="embedding cycle"):
        load(tmp_path / "a.yaml", embed=True)


def test_sub_document_escape_rejected(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (tmp_path / "secret.md").write_text("nope", "utf-8")
    (root / "sub.yaml").write_text("source: ../secret.md\n", "utf-8")
    with pytest.raises(LoadError, match="escapes the document root"):
        loads(b'{"source": "sub.yaml"}', format=Format.JSON, embed=True, root=root)


def test_broken_sub_document_names_reference(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{not json", "utf-8")
    with pytest.raises(LoadError, match=r"cannot embed 'bad\.json'"):
        loads(b'{"source": "bad.json"}', format=Format.JSON, embed=True, root=tmp_path)


def test_broken_deep_reference_returns_nothing(tmp_path: Path) -> None:
    _write(tmp_path / "sub.yaml", {"ok": {"source": "missing.md"}}, Format.YAML)
    with pytest.raises(LoadError, match="not found"):
        loads(b'{"a": {"source": "sub.yaml"}}', format=Format.JSON, embed=True, root=tmp_path)


@pytest.mark.parametrize(("name", "declared"), [("sub.yaml", "yaml"), ("sub.yml", "yaml"), ("sub.json", "json")])
def test_declared_format_matching_structured_accepted(tmp_path: Path, name: str, declared: str) -> None:
    (tmp_path / name).write_text('{"k": 1}', "utf-8")
    out = loads(
        dumps({"format": declared, "source": name}, format=Format.JSON), format=Format.JSON, embed=True, root=tmp_path
    )
    assert out == {"format": declared, "source": {"k": 1}}


def test_declared_markdown_on_structured_rejected(tmp_path: Path) -> None:
    _write(tmp_path / "sub.yaml", {"k": 1}, Format.YAML)
    with pytest.raises(LoadError, match="is yaml, but its sibling format declares 'markdown'"):
        loads(b'{"format": "markdown", "source": "sub.yaml"}', format=Format.JSON, embed=True, root=tmp_path)


def test_structured_oversized_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embed_mod, "MAX_EMBED_BYTES", 4)
    _write(tmp_path / "sub.json", {"k": "long enough"}, Format.JSON)
    with pytest.raises(LoadError, match="too large"):
        loads(b'{"source": "sub.json"}', format=Format.JSON, embed=True, root=tmp_path)


class _StubYaml:
    format: ClassVar[Format] = Format.YAML

    def loads(self, data: bytes) -> Any:
        return {"stub": len(data)}

    def dumps(self, obj: Any) -> bytes:
        return b""


def test_sub_documents_decode_through_given_registry(tmp_path: Path) -> None:
    registry = build_default_registry()
    registry.replace(Format.YAML, _StubYaml())
    (tmp_path / "sub.yaml").write_text("k: 1\n", "utf-8")
    out = loads(b'{"source": "sub.yaml"}', format=Format.JSON, embed=True, root=tmp_path, registry=registry)
    assert out == {"source": {"stub": 5}}


def test_structured_typed_schema(tmp_path: Path) -> None:
    _write(tmp_path / "db.toml", {"host": "h", "port": 5432}, Format.TOML)
    out = loads(b'{"db": "db.toml"}', format=Format.JSON, embed=("db",), root=tmp_path, type=_Cfg)
    assert out == _Cfg(db=_Db(host="h", port=5432))
