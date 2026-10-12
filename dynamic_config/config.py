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
        self._cache = ConfigCache()
        self._parser = parser
        self._sources: list[ConfigSource] = []

    def with_defaults(self) -> "ConfigBuilder":
        return self._add_source(DefaultSource(self._parser))

    def with_file(self, file_path: str | Path) -> "ConfigBuilder":
        return self._add_source(FileSource(self._parser, file_path))

    def with_directory(self, dir_path: str | Path, pattern: str = "*.conf") -> "ConfigBuilder":
        return self._add_source(DirectorySource(self._parser, dir_path, pattern))

    def with_environment(self, prefix: str = "") -> "ConfigBuilder":
        return self._add_source(EnvironmentSource(self._parser, prefix))

    def with_arguments(self) -> "ConfigBuilder":
        return self._add_source(ArgumentSource(self._parser))

    def _add_source(self, source: ConfigSource) -> "ConfigBuilder":
        self._sources.append(source)
        return self

    def build(self) -> "DynamicConfig":
        return DynamicConfig(self._cache, self._parser, self._sources)


class DynamicConfig:

    def __init__(
        self,
        cache: ConfigCache,
        parser: ConfigArgumentParser,
        sources: list[ConfigSource],
    ) -> None:
        self._cache = cache
        self._parser = parser
        self._sources = sources

    def get(self) -> Namespace:
        return self._cache

    def get_snapshot(self) -> Namespace:
        return self._cache.snapshot()

    def refresh(self) -> None:
        old_config = self._cache.snapshot().values()
        new_config: dict[str, Any] = {}

        for source in self._sources:
            new_config.update(source.get_config())

        update: dict[str, Any] = old_config

        for key in self._parser.get_dynamic_arguments().keys():
            if key in new_config:
                update[key] = new_config[key]

        self._cache.update(update)
