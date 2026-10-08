"""Explicit source registry; unknown sources are not accepted."""
from __future__ import annotations
from packages.connectors.contracts import Connector, ConnectorError, SourceSpec


class SourceRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, SourceSpec] = {}

    def register(self, spec: SourceSpec) -> None:
        if spec.source in self._sources and self._sources[spec.source] != spec:
            raise ConnectorError(f"source already registered with different specification: {spec.source}")
        self._sources[spec.source] = spec

    def get(self, source: str) -> SourceSpec:
        try:
            return self._sources[source]
        except KeyError as exc:
            raise ConnectorError(f"unknown source: {source}") from exc

    def all(self) -> tuple[SourceSpec, ...]:
        return tuple(self._sources[key] for key in sorted(self._sources))
