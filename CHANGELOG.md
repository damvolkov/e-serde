# Changelog

All notable changes to e-serde are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is maintained automatically: the release workflow appends the notes of
every tagged version, and a CI test fails if the head of this file ever disagrees
with `Cargo.toml`.

## [0.2.1] — 2026-09-23

- perf(yaml): the billion-laughs pre-scan only runs on documents that
  contain anchors (`&`); alias-free configs keep the old 2.2 ms/100 KB.
- feat(release): the bump commit now carries its own CHANGELOG section and
  GitHub-release notes; a CI tripwire fails if CHANGELOG and Cargo.toml drift.
- fix(release): compute the next version from the semver-max of remote tags
  (`git describe` is blind to the orphaned 0.2.0 bump); tag v0.1.1 — a bogus
  patch produced by that blindness — was withdrawn from tags and releases.
- fix(ci): restore the v0.2.0 version bump that the release flow never pushed
  (the workflow guard swallowed every bump push to protected main).
- docs: benchmark tables and charts regenerated for the lossless-Node
  emitters (JSONC/TOML/YAML/INI dumps ~25% faster); launch posts live outside
  the site build.

## [0.2.0] — 2026-09-23

### Added

- Custom-encoder contract: per-call `default=` and `encoders=` on
  `dumps/dump/adumps/adump`, `object_hook=`/`dec_hook=` on the decode side
  (json/orjson/msgspec semantics, keyword-only).
- `type=` validates pydantic models and generics (`list[M]`, `dict[str, M]`)
  through a lazily imported, cached `TypeAdapter`; violations surface as `LoadError`.
- `eserde.compat`: drop-in `json.dumps`/`json.loads` surface for frameworks that
  duck-type the stdlib module — byte-faithful by default, native compact utf-8
  fast path on `ensure_ascii=False`.
- `eserde.STANDARDS`: machine-readable per-format spec contract (spec, pinned
  engine + version, capability set) with the `test_standards.py` matrix that
  executes every claim both ways and cross-checks engine versions against the
  lockfiles.
- Comparative concurrency stress sweep (`make stress`): throughput, p99 and peak
  RSS versus worker count, with per-format charts and report under
  `assets/benchmarks/`.
- Docs: per-format pages generated from the contract; modular `Formats` section.

### Fixed

- Lossless `Node` tree replaces the `serde_json::Value` intermediate across the
  Rust codecs: big integers and `inf`/`nan` round-trip exactly where the format
  allows (TOML raises beyond its 64-bit range; JSON maps non-finites to `null`).
- Duplicate INI sections merge instead of silently dropping earlier keys.
- YAML merge keys (`<<`) resolve; explicit keys win.
- YAML and INI tolerate a leading UTF-8 BOM (INI previously rejected the file;
  YAML folded the BOM into the first key).
- Lone surrogates on encode raise `DumpError` instead of escaping the hierarchy.
- Empty JSONC documents are rejected.

### Known limitations

- YAML loads integers beyond 64-bit as `float` (engine resolves them that way);
  `dumps` always writes exact digits.
- saphyr pinned to 0.0.12: 0.1.0 regressed spec null semantics (empty node →
  `""`); the STANDARDS test-suite re-verifies on any future bump.

## [0.1.0] — 2026-09-17

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
- Rival benchmark matrix with matplotlib report.
