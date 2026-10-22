# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from argparse import Namespace
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from copy import deepcopy
from pathlib import Path
from threading import Lock, RLock, local
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

    def __init__(self, parser: ConfigArgumentParser, max_watcher_workers: int = 4):
        self._cache = ConfigCache()
        self._parser = parser
        self._watcher = FileWatcher(Observer(), max_workers=max_watcher_workers)
        self._sources: list[Source] = []

    def with_defaults(self) -> "ConfigBuilder":
        return self._add_source(DefaultSource(self._parser))

    def with_file(self, file_path: str | Path) -> "ConfigBuilder":
        self._watcher.watch(str(file_path))
        return self._add_source(FileSource(self._parser, file_path))

    def with_directory(self, dir_path: str | Path, pattern: str = "*.conf") -> "ConfigBuilder":
        self._watcher.watch(str(dir_path), is_directory=True)
        return self._add_source(DirectorySource(self._parser, dir_path, pattern))

    def with_environment(self, prefix: str = "") -> "ConfigBuilder":
        return self._add_source(EnvironmentSource(self._parser, prefix))

    def with_arguments(self, args: list[str] | None = None) -> "ConfigBuilder":
        return self._add_source(ArgumentSource(self._parser, args))

    def build(self, max_handler_workers: int = 4) -> "DynamicConfig":
        return DynamicConfig(self._cache, self._parser, self._watcher, self._sources, max_workers=max_handler_workers)

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
        max_workers: int = 4,
    ) -> None:
        self._cache = cache
        self._parser = parser
        self._watcher = watcher
        self._sources = sources
        self._handlers: list[OnConfigChangeEvent] = []
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = RLock()
        self._lifecycle_lock = Lock()
        self._callback = local()
        self._closed = False
        self._initialized = False
        self.log = get_logger(type(self).__name__)

    def initialize(self) -> None:
        if getattr(self._callback, "active", False):
            raise RuntimeError("Initialize configuration outside its change handlers")

        with self._lifecycle_lock:
            with self._lock:
                if self._closed:
                    raise RuntimeError("Configuration has been de-initialized; build a new instance")

                if self._initialized:
                    return

                self.log.debug("Initializing configuration")

                self.refresh(dynamic_only=False)

                self.log.info("Initial configuration loaded", config=self.snapshot().values())

                self._watcher.register(self._on_config_file_change)

            try:
                self._watcher.start()
            except Exception:
                self._shutdown()
                raise

            self._initialized = True

    def deinitialize(self) -> None:
        if getattr(self._callback, "active", False):
            raise RuntimeError("Deinitialize configuration outside its change handlers")

        with self._lifecycle_lock:
            self._shutdown()

    def get(self) -> Namespace:
        return self._cache.get()

    def snapshot(self) -> Namespace:
        return self._cache.snapshot()

    def refresh(self, dynamic_only: bool = True) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Configuration has been de-initialized")

            self.log.debug("Refreshing configuration", dynamic_only=dynamic_only)

            new_config: dict[str, Any] = {}
            for source in self._sources:
                new_config.update(vars(source.get_config()))

            if dynamic_only:
                dynamic = self._parser.get_dynamic_arguments()
                current = self.snapshot().values()
                new_config = {key: value for key, value in new_config.items() if key in dynamic}
                new_config.update({key: value for key, value in current.items() if key not in dynamic})

            self._cache.replace(new_config)

    def register(self, handler: OnConfigChangeEvent) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Configuration has been de-initialized")

            if handler not in self._handlers:
                self._handlers.append(handler)

    def deregister(self, handler: OnConfigChangeEvent) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def _shutdown(self) -> None:
        with self._lock:
            if self._closed:
                return

            self.log.debug("De-initializing configuration")

            self._closed = True
            self._watcher.deregister(self._on_config_file_change)

        try:
            self._watcher.stop()
        finally:
            self._executor.shutdown(wait=True)
            with self._lock:
                self._cache.clear()

    def _on_config_file_change(self, file_path: str) -> None:
        with self._lock:
            if self._closed:
                return

            old_config: dict[str, Any] = self.snapshot().values()

            self.refresh()

            new_config: dict[str, Any] = self.snapshot().values()

            changes: dict[str, ConfigChange] = {}
            for key in old_config.keys() | new_config.keys():
                old_value = old_config.get(key)
                new_value = new_config.get(key)

                if key not in old_config or key not in new_config or old_value != new_value:
                    changes[key] = ConfigChange(config_key=key, old_value=old_value, new_value=new_value)

            if changes:
                self.log.info("Configuration changes detected", file=file_path, changes=changes)

                for handler in self._handlers:
                    self._executor.submit(self._execute_handler, handler, file_path, deepcopy(changes))
            else:
                self.log.debug("No configuration changes detected")

    def _execute_handler(self, handler: OnConfigChangeEvent, file_path: str, changes: dict[str, ConfigChange]) -> None:
        self._callback.active = True

        try:
            handler(file_path, changes)
        except Exception as error:
            self.log.warn("Handler failed to process configuration change", file=file_path, error=error)
        finally:
            self._callback.active = False
