"""Embedding contract: `.md` references inlined under declared keys, all formats, confined roots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import msgspec
import pytest

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


def test_non_md_rejected(docs: Path) -> None:
    with pytest.raises(LoadError, match=r"only plain \.md"):
        loads('{"source": "notes.txt"}', format=Format.JSON, embed=True, root=docs)


def test_declared_format_must_be_markdown(docs: Path) -> None:
    with pytest.raises(LoadError, match="must be markdown"):
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
