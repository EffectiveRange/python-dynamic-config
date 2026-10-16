# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol
from types import TracebackType

from context_logger import get_logger
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers.api import BaseObserver
from watchdog.observers.api import ObservedWatch


class OnConfigChangeEvent(Protocol):

    def __call__(self, config_path: str) -> None: ...


class Watcher(ABC):

    @abstractmethod
    def register(self, handler: OnConfigChangeEvent) -> None: ...

    @abstractmethod
    def deregister(self, handler: OnConfigChangeEvent) -> None: ...

    @abstractmethod
    def watch(self, path: str | Path) -> None: ...

    @abstractmethod
    def unwatch(self, path: str | Path) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class ConfigWatcher(Watcher, FileSystemEventHandler):

    def __init__(self, observer: BaseObserver) -> None:
        super().__init__()
        self._observer = observer
        self._handlers: list[OnConfigChangeEvent] = []
        self._watches: dict[str, ObservedWatch] = {}
        self.log = get_logger(type(self).__name__)

    def __enter__(self) -> "ConfigWatcher":
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        self.stop()

    def register(self, handler: OnConfigChangeEvent) -> None:
        if handler not in self._handlers:
            self._handlers.append(handler)

    def deregister(self, handler: OnConfigChangeEvent) -> None:
        if handler in self._handlers:
            self._handlers.remove(handler)

    def watch(self, path: str | Path) -> None:
        path_str = str(path)
        if path_str not in self._watches:
            self._watches[path_str] = self._observer.schedule(self, path_str, recursive=True)

    def unwatch(self, path: str | Path) -> None:
        path_str = str(path)
        if path_str in self._watches.keys():
            watch = self._watches.pop(path_str)
            self._observer.unschedule(watch)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(1)
        self._watches.clear()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type in ("created", "modified", "moved", "deleted") and not event.is_directory:
            config_path = str(event.src_path)

            self.log.debug("Config file changed", file=config_path)

            for handler in self._handlers:
                handler(config_path)
