from argparse import Namespace
from pathlib import Path
from typing import Any

from dynamic_config import (
    ConfigSource,
    ConfigArgumentParser,
    DefaultSource,
    EnvironmentSource,
    FileSource,
    DirectorySource,
    ArgumentSource,
)
from dynamic_config.cache import ConfigCache


class ConfigBuilder:

    def __init__(self, parser: ConfigArgumentParser):
        self._parser = parser
        self._sources: list[ConfigSource] = []
        self._cache = ConfigCache()

    def with_defaults(self) -> "ConfigBuilder":
        return self._add_source(DefaultSource(self._parser))

    def with_file(self, file_path: str | Path) -> "ConfigBuilder":
        return self._add_source(FileSource(self._parser, file_path))

    def with_directory(
        self, dir_path: str | Path, pattern: str = "*.conf"
    ) -> "ConfigBuilder":
        return self._add_source(DirectorySource(self._parser, dir_path, pattern))

    def with_environment(self, prefix: str = "") -> "ConfigBuilder":
        return self._add_source(EnvironmentSource(self._parser, prefix))

    def with_arguments(self) -> "ConfigBuilder":
        return self._add_source(ArgumentSource(self._parser))

    def _add_source(self, source: ConfigSource) -> "ConfigBuilder":
        self._sources.append(source)
        return self

    def build(self) -> "DynamicConfig":
        return DynamicConfig(self._parser, self._sources, self._cache)


class DynamicConfig:

    def __init__(
        self,
        parser: ConfigArgumentParser,
        sources: list[ConfigSource],
        cache: ConfigCache,
    ) -> None:
        self._parser = parser
        self._sources = sources
        self._cache = cache

    def get(self) -> Namespace:
        return self._cache

    def get_snapshot(self) -> Namespace:
        return self._cache.snapshot()

    def refresh(self) -> None:
        config: dict[str, Any] = {}

        for source in self._sources:
            config.update(source.get_config())

        self._cache.update(config)
