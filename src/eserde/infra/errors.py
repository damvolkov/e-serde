"""Exception hierarchy. All e-serde failures inherit from `LoaderError`."""

from __future__ import annotations


class LoaderError(Exception):
    """Base for all e-serde exceptions."""


class FormatError(LoaderError):
    """Format could not be resolved from extension or was missing for a non-Path source."""


class CodecError(LoaderError):
    """Codec missing, duplicated, or unsupported for a given format."""


class LoadError(CodecError):
    """Backend `loads` failed. Wraps the original codec/backend exception."""


class DumpError(CodecError):
    """Backend `dumps` failed. Wraps the original codec/backend exception."""


class EncoderError(LoaderError):
    """Object cannot be encoded to a JSON-compatible primitive tree."""
