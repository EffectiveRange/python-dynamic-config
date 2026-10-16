from abc import ABC, abstractmethod

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers.api import BaseObserver
from watchdog.observers.api import ObservedWatch


class Watcher(ABC):

    @abstractmethod
    def register(self, path: str) -> None: ...

    @abstractmethod
    def unregister(self, path: str) -> None: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...


class ConfigWatcher(Watcher, FileSystemEventHandler):

    def __init__(self, observer: BaseObserver) -> None:
        super().__init__()
        self._observer = observer
        self._watches: dict[str, ObservedWatch] = {}

    def register(self, path: str) -> None:
        if path not in self._watches:
            self._watches[path] = self._observer.schedule(self, path, recursive=True)

    def unregister(self, path: str) -> None:
        if path in self._watches.keys():
            watch = self._watches.pop(path)
            self._observer.unschedule(watch)

    def start(self) -> None:
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        for watch in self._watches.values():
            self._observer.unschedule(watch)
        self._watches.clear()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            pass
