"""CLI smoke test: version line and format-to-backend table."""

from __future__ import annotations

from typing import Any

from e_serde.main import main


async def test_main_reports_backends(capsys: Any) -> None:
    main()
    out = capsys.readouterr().out
    assert out.startswith("e-serde ")
    for line in ("json", "jsonc", "yaml", "toml", "ini"):
        assert line in out
