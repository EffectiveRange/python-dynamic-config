from watchdog.observers.api import BaseObserver
from unittest.mock import MagicMock
from unittest import TestCase

from dynamic_config import ConfigWatcher


class TestConfigWatcher(TestCase):

    def test_register(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = ConfigWatcher(observer)
        path = "/some/path"

        # When
        watcher.register(path)

        # Then
        self.assertIn(path, watcher._watches)

    def test_unregister(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = ConfigWatcher(observer)
        path = "/some/path"
        watcher.register(path)

        # When
        watcher.unregister(path)

        # Then
        self.assertNotIn(path, watcher._watches)

    def test_start(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = ConfigWatcher(observer)

        path = "/some/path"
        watcher.register(path)

        # When
        watcher.start()

        # Then
        observer.start.assert_called_once()
        for path in watcher._watches:
            observer.schedule.assert_any_call(watcher, path, recursive=True)

    def test_stop(self):
        # Given
        observer = MagicMock(spec=BaseObserver)
        watcher = ConfigWatcher(observer)

        path = "/some/path"
        watcher.register(path)

        # When
        watcher.stop()

        # Then
        observer.stop.assert_called_once()
        for path in watcher._watches:
            observer.unschedule.assert_any_call(path)
