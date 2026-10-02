"""Interpolation contract: compose-spec `${VAR…}` over string leaves, keys and scalars untouched."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from eserde.infra.errors import LoadError
from eserde.infra.formats import Format
from eserde.logic.api import aload, aloads, load, loads
from eserde.logic.interpolate import interpolate

if TYPE_CHECKING:
    from pathlib import Path

ENV = {"PORT": "9000", "EMPTY": "", "HOST": "gpu"}

COMPOSE = """\
services:
  vllm:
    image: vllm/vllm-openai:${TAG:-latest}
    ports:
      - "${VLLM_PORT:-8000}:8000"
    environment:
      HOST: $HOST
      replicas: 2
"""


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("${PORT}", "9000"),
        ("$PORT", "9000"),
        ("$PORT-x", "9000-x"),
        ("${MISSING}", ""),
        ("$MISSING", ""),
        ("${PORT:-1}", "9000"),
        ("${MISSING:-1}", "1"),
        ("${EMPTY:-1}", "1"),
        ("${EMPTY-1}", ""),
        ("${MISSING-1}", "1"),
        ("${PORT:+on}", "on"),
        ("${EMPTY:+on}", ""),
        ("${EMPTY+on}", "on"),
        ("${MISSING+on}", ""),
        ("${PORT:?boom}", "9000"),
        ("${EMPTY?boom}", ""),
        ("${MISSING:-${HOST}}", "gpu"),
        ("${MISSING:-${ALSO:-deep}}", "deep"),
        ("${PORT:-${UNSET:?never evaluated}}", "9000"),
        ("$$PORT", "$PORT"),
        ("a$$b", "a$b"),
        ("${HOST}:${PORT}/x", "gpu:9000/x"),
        ("plain", "plain"),
        ("ünï${HOST}ç", "ünïgpuç"),
    ],
)
def test_expand(raw: str, expected: str) -> None:
    assert interpolate(raw, ENV) == expected


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        ("${MISSING:?set it}", "required variable MISSING is missing a value: set it"),
        ("${EMPTY:?set it}", "required variable EMPTY"),
        ("${MISSING?x}", "required variable MISSING"),
        ("${PORT", "unterminated"),
        ("price $5", "lone \\$"),
        ("tail $", "lone \\$"),
        ("${}", "missing variable name"),
        ("${PORT:}", "unknown operator"),
        ("${PORT*x}", "unknown operator"),
    ],
)
def test_expand_errors(raw: str, match: str) -> None:
    with pytest.raises(LoadError, match=match):
        interpolate(raw, ENV)


def test_tree_keys_and_scalars_untouched() -> None:
    tree = {"$HOST": ["${PORT}", 1, 2.5, True, None, {"k": "$HOST"}]}
    assert interpolate(tree, ENV) == {"$HOST": ["9000", 1, 2.5, True, None, {"k": "gpu"}]}


def test_copy_never_mutates() -> None:
    tree = {"a": ["${PORT}"]}
    interpolate(tree, ENV)
    assert tree == {"a": ["${PORT}"]}


def test_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ESERDE_TEST_VAR", "from-env")
    assert interpolate("${ESERDE_TEST_VAR}") == "from-env"


def test_compose_ports() -> None:
    tree = loads(COMPOSE, format=Format.YAML, interpolate={"HOST": "gpu"})
    vllm = tree["services"]["vllm"]
    assert vllm["image"] == "vllm/vllm-openai:latest"
    assert vllm["ports"] == ["8000:8000"]
    assert vllm["environment"] == {"HOST": "gpu", "replicas": 2}


def test_off_by_default() -> None:
    assert loads(COMPOSE, format=Format.YAML)["services"]["vllm"]["ports"] == ["${VLLM_PORT:-8000}:8000"]


def test_true_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VLLM_PORT", "8100")
    assert loads(COMPOSE, format=Format.YAML, interpolate=True)["services"]["vllm"]["ports"] == ["8100:8000"]


@pytest.mark.parametrize("fmt", [Format.JSON, Format.TOML])
def test_any_format(fmt: Format) -> None:
    source = {Format.JSON: '{"url": "${HOST}:${PORT}"}', Format.TOML: 'url = "${HOST}:${PORT}"'}[fmt]
    assert loads(source, format=fmt, interpolate=ENV) == {"url": "gpu:9000"}


def test_file(tmp_path: Path) -> None:
    path = tmp_path / "compose.yaml"
    path.write_text(COMPOSE, "utf-8")
    assert load(path, interpolate={"VLLM_PORT": "1"})["services"]["vllm"]["ports"] == ["1:8000"]


async def test_async_twins(tmp_path: Path) -> None:
    path = tmp_path / "compose.yaml"
    path.write_text(COMPOSE, "utf-8")
    assert (await aload(path, interpolate={"VLLM_PORT": "2"}))["services"]["vllm"]["ports"] == ["2:8000"]
    assert (await aloads(path, interpolate={"VLLM_PORT": "3"}))["services"]["vllm"]["ports"] == ["3:8000"]


def test_interpolated_reference_embeds(tmp_path: Path) -> None:
    (tmp_path / "prod.md").write_text("prod notes", "utf-8")
    (tmp_path / "doc.yaml").write_text("notes:\n  source: ./${STAGE:-dev}.md\n", "utf-8")
    assert loads(tmp_path / "doc.yaml", embed=True, interpolate={"STAGE": "prod"}) == {
        "notes": {"source": "prod notes"}
    }


def test_failure_maps_to_load_error() -> None:
    with pytest.raises(LoadError, match="interpolation failed"):
        loads('{"a": "${X:?need X}"}', format=Format.JSON, interpolate={})
