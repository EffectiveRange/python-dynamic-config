# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path
from context_logger import get_logger
from watchdog.observers import Observer
from typing import Any, Protocol
from abc import ABC, abstractmethod

from dynamic_config import (
    Source,
    Parser,
    ConfigArgumentParser,
    DefaultSource,
    EnvironmentSource,
    FileSource,
    DirectorySource,
    ArgumentSource,
    Cache,
    ConfigCache,
    FileWatcher,
    Watcher,
)


@dataclass
class ConfigChange:
    config_key: str
    old_value: Any
    new_value: Any


class OnConfigChangeEvent(Protocol):

    def __call__(self, file_path: str, changes: dict[str, ConfigChange]) -> None: ...


class Config(ABC):

    @abstractmethod
    def initialize(self) -> None: ...

    @abstractmethod
    def deinitialize(self) -> None: ...

    @abstractmethod
    def get(self) -> Namespace: ...

    @abstractmethod
    def snapshot(self) -> Namespace: ...

    @abstractmethod
    def refresh(self, dynamic_only: bool = True) -> None: ...

    @abstractmethod
    def register(self, handler: OnConfigChangeEvent) -> None: ...

    @abstractmethod
    def deregister(self, handler: OnConfigChangeEvent) -> None: ...


class ConfigBuilder:

    def __init__(self, parser: ConfigArgumentParser):
        self._cache = ConfigCache()
        self._parser = parser
        self._watcher = FileWatcher(Observer())
        self._sources: list[Source] = []

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

    def build(self) -> "DynamicConfig":
        return DynamicConfig(self._cache, self._parser, self._watcher, self._sources)

    def _add_source(self, source: Source) -> "ConfigBuilder":
        self._sources.append(source)
        return self


class DynamicConfig(Config):

    def __init__(
        self,
        cache: Cache,
        parser: Parser,
        watcher: Watcher,
        sources: list[Source],
    ) -> None:
        self._cache = cache
        self._parser = parser
        self._watcher = watcher
        self._sources = sources
        self._handlers: list[OnConfigChangeEvent] = []
        self.log = get_logger(type(self).__name__)

    def initialize(self) -> None:
        self.log.debug("Initializing configuration")
        self.refresh(dynamic_only=False)
        self._watcher.register(self._on_config_file_change)
        self._watcher.start()

    def deinitialize(self) -> None:
        self.log.debug("Deinitializing configuration")
        self._watcher.deregister(self._on_config_file_change)
        self._watcher.stop()
        self._cache.clear()

    def get(self) -> Namespace:
        return self._cache.get()

    def snapshot(self) -> Namespace:
        return self._cache.snapshot()

    def refresh(self, dynamic_only: bool = True) -> None:
        self.log.debug("Refreshing configuration", dynamic_only=dynamic_only)

        new_config: dict[str, Any] = {}

        for source in self._sources:
            new_config.update(vars(source.get_config()))

        update: dict[str, Any] = {}

        if dynamic_only:
            for key in self._parser.get_dynamic_arguments().keys():
                if key in new_config:
                    update[key] = new_config[key]
        else:
            for key in new_config:
                update[key] = new_config[key]

        self._cache.update(update)

    def register(self, handler: OnConfigChangeEvent) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def deregister(self, handler: OnConfigChangeEvent) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def _on_config_file_change(self, file_path: str) -> None:
        old_config: dict[str, Any] = dict(self.snapshot().values())

        self.refresh()

        new_config: dict[str, Any] = dict(self.snapshot().values())

        changes: dict[str, ConfigChange] = {}
        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                changes[key] = ConfigChange(config_key=key, old_value=old_value, new_value=new_value)

        if changes:
            self.log.debug("Configuration changes detected", changes=changes)
            for handler in self._handlers:
                handler(file_path, changes)
        else:
            self.log.debug("No configuration changes detected")
