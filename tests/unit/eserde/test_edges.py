"""Edge-case and adversarial corpus, distilled from real bugs in peer codecs.

Each class pins behaviour we inherited or hardened against upstream issue
history: msgspec (surrogates, trailing commas, deep nesting), orjson (lone
surrogate encode, big-int fidelity), rtoml/toml-rs (BOM, duplicate keys,
recursion), PyYAML/serde_yaml (billion-laughs DoS, merge keys, tabs, `.inf`),
and rust-ini (preamble keys, `==`). Behaviour that is *lossy by design*
(YAML core schema) is asserted so a future change is a loud decision, not drift.
"""

from __future__ import annotations

import math

import msgspec
import pytest

from eserde import DumpError, Format, LoadError, dumps, loads

##### JSON — msgspec-derived edges #####


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"[-0.0]", [-0.0]),
        (b'{"a":1,"a":2}', {"a": 2}),
        (b"9" * 200, int("9" * 200)),
        (b"[[[[[[1]]]]]]", [[[[[[1]]]]]]),
        (b'{"float": 1.5, "exp": 1e3}', {"float": 1.5, "exp": 1000.0}),
    ],
    ids=["neg-zero", "dup-keys-last-wins", "bignum-exact", "nested", "floats"],
)
def test_loads_json_ok(raw: bytes, expected: object) -> None:
    assert loads(raw, format=Format.JSON) == expected


@pytest.mark.parametrize(
    "raw",
    [b"[1e400]", b'"\\ud800"', b"[1,2,]", b"", b"   \n", b'\xef\xbb\xbf{"a":1}', b"{,}", b"[NaN]", b"01"],
    ids=[
        "inf-overflow",
        "lone-surrogate",
        "trailing-comma",
        "empty",
        "whitespace",
        "bom",
        "empty-object-slot",
        "nan-token",
        "leading-zero",
    ],
)
def test_loads_json_rejects(raw: bytes) -> None:
    with pytest.raises(LoadError):
        loads(raw, format=Format.JSON)


def test_loads_json_deep_nesting_survives() -> None:
    depth = 1000
    assert loads(b"[" * depth + b"]" * depth, format=Format.JSON) is not None


##### JSONC — comment / tolerance edges #####


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1}//x', b"[1,2,]", b"/*lead*/[1]", b'{"a":/*mid*/1}'],
    ids=["comment-no-eol", "trailing-comma", "leading-block", "inline-block"],
)
def test_loads_jsonc_tolerates(raw: bytes) -> None:
    loads(raw, format=Format.JSONC)


def test_loads_jsonc_nested_block_not_supported() -> None:
    with pytest.raises(LoadError):
        loads(b'{"a":1}/*/*x*/y*/', format=Format.JSONC)


##### YAML — PyYAML/serde_yaml/saphyr-derived edges #####


def test_loads_yaml_tabs_rejected() -> None:
    with pytest.raises(LoadError):
        loads(b"a:\n\tb: 1\n", format=Format.YAML)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"a: .inf\n", {"a": math.inf}),
        (b"a: .nan\n", {"a": math.nan}),
        (b"a: 1:30\n", {"a": "1:30"}),
        (b"a: &x {k: 1}\nb: {<<: *x}\n", {"a": {"k": 1}, "b": {"k": 1}}),
        (b"p: &p {a: 1}\nq: &q {b: 2}\nr:\n  <<: [*p, *q]\n", {"p": {"a": 1}, "q": {"b": 2}, "r": {"a": 1, "b": 2}}),
        (b"a: !!python/object:os.system ['id']\n", {"a": ["id"]}),
        (b"~: 1\n", {"null": 1}),
        (b"a: 1\r\n", {"a": 1}),
    ],
    ids=[
        "inf-preserved",
        "nan-preserved",
        "sexagesimal-str",
        "merge-key-resolved",
        "merge-seq",
        "python-tag-inert",
        "tilde-key",
        "crlf",
    ],
)
def test_loads_yaml_core_schema(raw: bytes, expected: dict) -> None:
    result = loads(raw, format=Format.YAML)
    for key, value in expected.items():
        if isinstance(value, float) and math.isnan(value):
            assert math.isnan(result[key])
        else:
            assert result[key] == value


def test_loads_yaml_bignum_loses_to_float_engine_limit() -> None:
    assert loads(b"a: " + b"9" * 29, format=Format.YAML) == {"a": 1e29}


def test_loads_yaml_empty_stream_rejected() -> None:
    with pytest.raises(LoadError):
        loads(b"", format=Format.YAML)


def test_loads_yaml_explicit_null_doc() -> None:
    assert loads(b"---\n", format=Format.YAML) is None


def test_loads_yaml_billion_laughs_aborts_on_budget() -> None:
    doc = "l0: &l0 [a,b,c,d,e,f,g,h]\n"
    doc += "".join(f"l{i}: &l{i} [" + ",".join(f"*l{i - 1}" for _ in range(8)) + "]\n" for i in range(1, 25))
    with pytest.raises(LoadError, match="budget"):
        loads(doc.encode(), format=Format.YAML)


def test_loads_yaml_ordinary_alias_ok() -> None:
    assert loads(b"a: &x {k: 1}\nb: *x\n", format=Format.YAML) == {"a": {"k": 1}, "b": {"k": 1}}


##### TOML — toml-rs/rtoml-derived edges #####


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"\xef\xbb\xbfa = 1\n", {"a": 1}),
        (b"a = 1979-05-27T07:32:00Z\n", {"a": "1979-05-27T07:32:00Z"}),
        ('a = "x\u2028y"\n'.encode(), {"a": "x\u2028y"}),
        (b"", {}),
    ],
    ids=["bom-ok", "datetime-iso-string", "line-sep-kept", "empty-ok"],
)
def test_loads_toml_ok(raw: bytes, expected: dict) -> None:
    assert loads(raw, format=Format.TOML) == expected


@pytest.mark.parametrize(
    "raw",
    [b"a = 1\na = 2\n", b"[a]\nb = 1\n[a]\nc = 2\n", b"[a" + b".a" * 500 + b"]\nk=1\n"],
    ids=["dup-key", "dup-table", "deep-tables-recursion"],
)
def test_loads_toml_rejects(raw: bytes) -> None:
    with pytest.raises(LoadError):
        loads(raw, format=Format.TOML)


##### INI — rust-ini-derived edges #####


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (b"[a]\nk=1\n[a]\nj=2\n", {"a": {"k": "1", "j": "2"}}),
        (b"[a]\nk=1\n[a]\nk=2\nj=3\n", {"a": {"k": "2", "j": "3"}}),
        (b"[a]\nk==v\n", {"a": {"k": "=v"}}),
        (b"[a]\nk=x=y\n", {"a": {"k": "x=y"}}),
        (b"\xef\xbb\xbf[a]\nk=v\n", {"a": {"k": "v"}}),
        (b"[a]\r\nk=v\r\n", {"a": {"k": "v"}}),
        (b"", {}),
        ("[d\u00e9bito]\nclave=valor\n".encode(), {"d\u00e9bito": {"clave": "valor"}}),
    ],
    ids=[
        "dup-section-merges",
        "dup-key-override",
        "double-equals",
        "value-with-equals",
        "bom-ok",
        "crlf",
        "empty-ok",
        "unicode",
    ],
)
def test_loads_ini_ok(raw: bytes, expected: dict) -> None:
    assert loads(raw, format=Format.INI) == expected


def test_loads_ini_preamble_rejected() -> None:
    with pytest.raises(LoadError):
        loads(b"k=v\n", format=Format.INI)


##### typed validation across the strict boundary #####


def test_loads_ini_strict_typed_rejects_string_int() -> None:
    class Svc(msgspec.Struct):
        port: int

    with pytest.raises(LoadError):
        loads(b"[s]\nport=8080\n", format=Format.INI, type=dict[str, Svc])


def test_loads_ini_coerced_typed() -> None:
    class Svc(msgspec.Struct):
        port: int

    assert loads(b"[s]\nport=8080\n", format=Format.INI, type=dict[str, Svc], strict=False) == {"s": Svc(port=8080)}


##### dumps — encoding edges (orjson-derived) #####


@pytest.mark.parametrize(
    "obj",
    [{"x": float("nan")}, {"x": float("inf")}, {"x": -float("inf")}],
    ids=["nan", "inf", "neg-inf"],
)
def test_dumps_json_nonfinite_becomes_null(obj: dict) -> None:
    assert loads(dumps(obj, format=Format.JSON), format=Format.JSON) == {"x": None}


def test_dumps_json_bignum_exact() -> None:
    assert dumps({"x": 2**200}, format=Format.JSON) == b'{"x":' + str(2**200).encode() + b"}"


@pytest.mark.parametrize("fmt", [Format.JSON, Format.YAML, Format.TOML, Format.JSONC])
def test_dumps_lone_surrogate_raises_dump_error(fmt: Format) -> None:
    with pytest.raises(DumpError):
        dumps({"x": "\ud800"}, format=fmt)


def test_dumps_tuple_key_stringified() -> None:
    assert loads(dumps({(1, 2): "x"}, format=Format.YAML), format=Format.YAML) == {"[1, 2]": "x"}


def test_dumps_empty_root() -> None:
    assert dumps({}, format=Format.JSON) == b"{}"


##### numeric fidelity — the Node intermediate #####


def test_bigint_exact_roundtrip_jsonc() -> None:
    tree = {"x": int("9" * 40)}
    assert loads(dumps(tree, format=Format.JSONC), format=Format.JSONC) == tree


def test_dumps_yaml_writes_bignum_digits_exactly() -> None:
    digits = int("9" * 40)
    assert dumps({"x": digits}, format=Format.YAML) == f"x: {'9' * 40}\n".encode()


def test_loads_jsonc_bignum_exact() -> None:
    assert loads(b"9" * 40, format=Format.JSONC) == int("9" * 40)


@pytest.mark.parametrize("fmt", [Format.YAML, Format.TOML])
def test_nonfinite_floats_survive_roundtrip(fmt: Format) -> None:
    tree = {"pos": math.inf, "neg": -math.inf}
    result = loads(dumps(tree, format=fmt), format=fmt)
    assert result["pos"] == math.inf
    assert result["neg"] == -math.inf


def test_dumps_toml_bignum_raises_loudly() -> None:
    with pytest.raises(DumpError, match="64-bit"):
        dumps({"x": 2**130}, format=Format.TOML)


def test_jsonc_string_escaping_exact() -> None:
    tree = {"k": 'a\n"b\t\\c\x01ünïcødé ✓'}
    assert loads(dumps(tree, format=Format.JSONC), format=Format.JSONC) == tree


def test_jsonc_empty_document_rejected() -> None:
    with pytest.raises(LoadError, match="empty"):
        loads(b"", format=Format.JSONC)
