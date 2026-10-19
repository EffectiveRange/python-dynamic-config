from context_logger import setup_logging
from watchdog.observers.api import BaseObserver
from unittest.mock import MagicMock
from pathlib import Path
from unittest import TestCase

from dynamic_config import FileWatcher
from tests.utils import TEST_APPLICATION_NAME


class TestConfigWatcher(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_register(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()

        # When
        watcher.register(handler)

        # Then
        self.assertIn(handler, watcher._handlers)

    def test_register_duplicate(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)

        # When
        watcher.register(handler)

        # Then
        self.assertEqual(watcher._handlers.count(handler), 1)

    def test_deregister(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)

        # When
        watcher.deregister(handler)

        # Then
        self.assertNotIn(handler, watcher._handlers)

    def test_deregister_nonexistent(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()

        # When
        watcher.deregister(handler)

        # Then
        self.assertNotIn(handler, watcher._handlers)

    def test_watch(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        path = "/some/path"

        # When
        watcher.watch(Path(path))

        # Then
        self.assertIn(path, watcher._watches)
        observer.schedule.assert_called_once_with(watcher, path, recursive=True)

    def test_watch_duplicate(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        path = "/some/path"
        watcher.watch(Path(path))

        # When
        watcher.watch(Path(path))

        # Then
        self.assertEqual(list(watcher._watches.keys()).count(path), 1)

    def test_unwatch(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        path = "/some/path"
        watcher.watch(Path(path))

        # When
        watcher.unwatch(path)

        # Then
        self.assertNotIn(path, watcher._watches)
        observer.unschedule.assert_called_once()

    def test_unwatch_nonexistent(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        path = "/some/path"

        # When
        watcher.unwatch(path)

        # Then
        self.assertNotIn(path, watcher._watches)

    def test_start(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)

        path = "/some/path"
        watcher.watch(Path(path))

        # When
        watcher.start()

        # Then
        observer.start.assert_called_once()
        for path in watcher._watches:
            observer.schedule.assert_any_call(watcher, path, recursive=True)

    def test_stop(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)

        path = "/some/path"
        watcher.watch(Path(path))

        # When
        watcher.stop()

        # Then
        observer.stop.assert_called_once()
        for watch in watcher._watches.values():
            observer.unschedule.assert_any_call(watch)

    def test_on_any_event_when_created(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "created"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_called_once_with(str(event.src_path))

    def test_on_any_event_when_modified(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "modified"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_called_once_with(str(event.src_path))

    def test_on_any_event_when_moved(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "moved"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_called_once_with(str(event.src_path))

    def test_on_any_event_when_deleted(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "deleted"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_called_once_with(str(event.src_path))

    def test_on_any_event_when_unhandled_event_type(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "closed"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_not_called()

    def test_on_any_event_when_directory(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock()
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "modified"
        event.is_directory = True
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_not_called()

    def test_on_any_event_when_handler_raises_exception(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = FileWatcher(observer)
        handler = MagicMock(side_effect=Exception("Handler error"))
        watcher.register(handler)
        event = MagicMock()
        event.event_type = "modified"
        event.is_directory = False
        event.src_path = "/some/path/config.yaml"

        # When
        watcher.on_any_event(event)

        # Then
        handler.assert_called_once_with(str(event.src_path))
