# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

from abc import ABC, abstractmethod
from os.path import abspath
from pathlib import Path
from typing import Any, Protocol
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock, RLock, local

from context_logger import get_logger
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers.api import BaseObserver
from watchdog.observers.api import ObservedWatch


class OnFileChanged(Protocol):

    def __call__(self, file_path: str) -> None: ...


class Watcher(ABC):

    @abstractmethod
    def register(self, handler: OnFileChanged) -> None: ...

    @abstractmethod
    def deregister(self, handler: OnFileChanged) -> None: ...

    @abstractmethod
    def watch(self, path: str | Path, recursive: bool = True, *, is_directory: bool | None = None) -> None: ...

    @abstractmethod
    def unwatch(self, path: str | Path) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


@dataclass
class WatchTarget:
    watch: ObservedWatch
    is_directory: bool
    recursive: bool


class FileWatcher(Watcher, FileSystemEventHandler):

    def __init__(self, observer: BaseObserver, max_workers: int = 4) -> None:
        super().__init__()
        self._observer = observer
        self._handlers: list[OnFileChanged] = []
        self._watches: dict[str, WatchTarget] = {}
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = RLock()
        self._lifecycle_lock = Lock()
        self._callback = local()
        self._closed = False
        self._started = False
        self.log = get_logger(type(self).__name__)

    def __enter__(self) -> "FileWatcher":
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.stop()

    def register(self, handler: OnFileChanged) -> None:
        with self._lock:
            if self._closed:
                raise RuntimeError("Watcher has been stopped")
            if handler not in self._handlers:
                self._handlers.append(handler)

    def deregister(self, handler: OnFileChanged) -> None:
        with self._lock:
            if handler in self._handlers:
                self._handlers.remove(handler)

    def watch(self, path: str | Path, recursive: bool = True, *, is_directory: bool | None = None) -> None:
        self._check_lifecycle_call()

        target_path = Path(abspath(path))
        path_str = str(target_path)

        with self._lifecycle_lock:
            with self._lock:
                if self._closed:
                    raise RuntimeError("Watcher has been stopped")
                if path_str in self._watches:
                    return

            directory = target_path.is_dir() if is_directory is None else is_directory
            observed_path = target_path if directory else target_path.parent

            self.log.debug("Start watching path", path=path_str, recursive=recursive)

            watch = self._observer.schedule(self, str(observed_path), recursive=recursive if directory else False)

            with self._lock:
                self._watches[path_str] = WatchTarget(watch, directory, recursive)

    def unwatch(self, path: str | Path) -> None:
        self._check_lifecycle_call()

        path_str = abspath(path)

        with self._lifecycle_lock:
            with self._lock:
                target = self._watches.pop(path_str, None)
                if target is None:
                    return
                shared = any(other.watch == target.watch for other in self._watches.values())

            self.log.debug("Stop watching path", path=path_str)

            if not shared:
                self._observer.unschedule(target.watch)

    def start(self) -> None:
        self._check_lifecycle_call()

        with self._lifecycle_lock:
            with self._lock:
                if self._closed:
                    raise RuntimeError("Watcher has been stopped; create a new instance")
                if self._started:
                    return

            self.log.debug("Starting observer")

            self._observer.start()
            self._started = True

    def stop(self) -> None:
        self._check_lifecycle_call()

        with self._lifecycle_lock:
            with self._lock:
                if self._closed:
                    return

                self._closed = True

            self.log.debug("Stopping observer")

            try:
                self._observer.stop()
                if self._observer.is_alive():
                    self._observer.join()
            finally:
                self._executor.shutdown(wait=True)
                with self._lock:
                    self._watches.clear()

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.event_type not in ("created", "modified", "moved", "deleted") or event.is_directory:
            return

        paths = [str(event.src_path)]

        if event.event_type == "moved":
            paths.append(str(event.dest_path))

        with self._lock:
            if self._closed:
                return

            for file_path in dict.fromkeys(paths):
                if not file_path or not self._matches(Path(abspath(file_path))):
                    continue

                self.log.debug("File changed", file=file_path, change=event.event_type)

                for handler in self._handlers:
                    self._executor.submit(self._execute_handler, handler, file_path)

    def _matches(self, path: Path) -> bool:
        for path_str, target in self._watches.items():
            watched = Path(path_str)

            if path == watched:
                return True

            if target.is_directory and (path.parent == watched or (target.recursive and watched in path.parents)):
                return True

        return False

    def _check_lifecycle_call(self) -> None:
        if getattr(self._callback, "active", False):
            raise RuntimeError("Manage watcher lifecycle outside its change handlers")

    def _execute_handler(self, handler: OnFileChanged, file_path: str) -> None:
        self._callback.active = True

        try:
            handler(file_path)
        except Exception as error:
            self.log.warn("Handler failed to process file change", file=file_path, error=error)
        finally:
            self._callback.active = False
