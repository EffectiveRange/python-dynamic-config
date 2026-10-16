# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from argparse import Namespace
from pathlib import Path
from context_logger import get_logger
from watchdog.observers import Observer
from typing import Any
from abc import ABC, abstractmethod

from dynamic_config import (
    ConfigSource,
    Parser,
    ConfigArgumentParser,
    DefaultSource,
    EnvironmentSource,
    FileSource,
    DirectorySource,
    ArgumentSource,
    Cache,
    ConfigCache,
    ConfigWatcher,
    Watcher,
)


class Config(ABC):

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def destroy(self) -> None: ...

    @abstractmethod
    def get(self) -> Namespace: ...

    @abstractmethod
    def snapshot(self) -> Namespace: ...

    @abstractmethod
    def refresh(self) -> None: ...


class ConfigBuilder:

    def __init__(self, parser: ConfigArgumentParser):
        self._cache = ConfigCache()
        self._parser = parser
        self._watcher = ConfigWatcher(Observer())
        self._sources: list[ConfigSource] = []

    def with_defaults(self) -> "ConfigBuilder":
        return self._add_source(DefaultSource(self._parser))

    def with_file(self, file_path: str | Path) -> "ConfigBuilder":
        self._watcher.watch(str(file_path))
        return self._add_source(FileSource(self._parser, file_path))

    def with_directory(self, dir_path: str | Path, pattern: str = "*.conf") -> "ConfigBuilder":
        self._watcher.watch(str(dir_path))
        return self._add_source(DirectorySource(self._parser, dir_path, pattern))

    def with_environment(self, prefix: str = "") -> "ConfigBuilder":
        return self._add_source(EnvironmentSource(self._parser, prefix))

    def with_arguments(self) -> "ConfigBuilder":
        return self._add_source(ArgumentSource(self._parser))

    def _add_source(self, source: ConfigSource) -> "ConfigBuilder":
        self._sources.append(source)
        return self

    def build(self) -> "DynamicConfig":
        return DynamicConfig(self._cache, self._parser, self._watcher, self._sources)


class DynamicConfig(Config):

    def __init__(
        self,
        cache: Cache,
        parser: Parser,
        watcher: Watcher,
        sources: list[ConfigSource],
    ) -> None:
        self._cache = cache
        self._parser = parser
        self._watcher = watcher
        self._sources = sources
        self.log = get_logger(type(self).__name__)

    def initialize(self) -> None:
        self.refresh()
        self._watcher.register(self._on_config_file_change)
        self._watcher.start()

    def destroy(self) -> None:
        self._watcher.deregister(self._on_config_file_change)
        self._watcher.stop()
        self._cache.clear()

    def get(self) -> Namespace:
        return self._cache.get()

    def snapshot(self) -> Namespace:
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

    def _on_config_file_change(self, config_path: str) -> None:
        self.refresh()
