# Changelog

All notable changes to e-serde are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Versions are tagged as `vX.Y.Z`; after the first automated release this file is
maintained by release-plz from conventional commits.

## [0.1.0] — 2026-09-16

Initial release.

### Added

- Universal loader: `loads`/`dumps`/`load`/`dump` + async twins over
  `bytes | str | Path`, with format autodetection from extensions.
- Native Rust codecs (one `maturin` extension module): JSONC (`jsonc-parser`),
  YAML 1.2 (`saphyr`), TOML (`toml`), INI (`rust-ini`); JSON via `msgspec.json`.
- Optional schema validation: `type=` routes the decoded tree through
  `msgspec.convert` into Structs, dataclasses or TypedDicts; `strict=False`
  enables coercion.
- Jsonable dump encoder (datetime → ISO, Enum → value, bytes → base64).
- Pluggable `CodecRegistry`; `e-serde` CLI listing active backends.
- Rival benchmark matrix (orjson, ujson, PyYAML, ruamel, rtoml, tomllib,
  tomlkit, pyjson5, json5, configparser, msgspec, pydantic) with matplotlib
  report.
