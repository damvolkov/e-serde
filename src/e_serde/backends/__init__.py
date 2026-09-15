"""Backend layer: one folder per engine, internal dependencies only up to `infra`."""

from e_serde.backends.registry import CodecRegistry, default_registry

__all__ = ["CodecRegistry", "default_registry"]
