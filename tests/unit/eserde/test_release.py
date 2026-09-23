"""Release hygiene: the CHANGELOG head must track the crate version.

The release workflow writes both in one commit; this is the tripwire that fires
when the two ever drift apart (as the v0.2.0 squash race proved).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def _cargo_version() -> str:
    manifest = (REPO / "Cargo.toml").read_text(encoding="utf-8")
    found = re.search(r'^\[workspace\.package\][^[]*?^version = "([^"]+)"', manifest, re.MULTILINE | re.DOTALL)
    assert found is not None
    return found.group(1)


def _changelog_head() -> str:
    body = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")
    found = re.search(r"^## \[(\d+\.\d+\.\d+)\]", body, re.MULTILINE)
    assert found is not None
    return found.group(1)


def test_changelog_head_matches_cargo_version() -> None:
    assert _changelog_head() == _cargo_version()


def test_changelog_is_not_stale() -> None:
    assert "release-plz" not in (REPO / "CHANGELOG.md").read_text(encoding="utf-8").lower()
