from abc import ABC, abstractmethod

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers.api import BaseObserver


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
        self._paths: set[str] = set()

    def register(self, path: str) -> None:
        if path not in self._paths:
            self._paths.add(path)
            self._observer.schedule(self, path, recursive=True)

    def unregister(self, path: str) -> None:
        if path in self._paths:
            self._paths.remove(path)
            self._observer.unschedule(path)

    def start(self) -> None:
        for path in self._paths:
            self._observer.schedule(self, path, recursive=True)
        self._observer.start()

    def stop(self) -> None:
        self._observer.stop()
        for path in self._paths:
            self._observer.unschedule(path)
        self._paths.clear()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            print(f"Configuration file changed: {event.src_path}")
