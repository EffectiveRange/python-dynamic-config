from threading import Event
from common_utility import append_file, create_file
from context_logger import setup_logging
from watchdog.observers import Observer

from unittest.mock import MagicMock

from unittest import TestCase

from dynamic_config import ConfigWatcher
from dynamic_config.watcher import OnConfigFileChanged
from tests.utils import TEST_APPLICATION_NAME, TEST_FILE_SYSTEM_ROOT


class TestConfigFileWatching(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_config_file_watch(self):
        # Given
        changed = Event()
        handler = MagicMock(spec=OnConfigFileChanged)
        handler.side_effect = lambda config_path: changed.set()
        observer = Observer()

        with ConfigWatcher(observer) as watcher:
            watcher.register(handler)

            dummy_file = TEST_FILE_SYSTEM_ROOT / "dummy.conf"
            create_file(dummy_file)
            watcher.watch(dummy_file)

            watcher.start()

            # When
            append_file(dummy_file, "some content")

            # Then
            assert changed.wait(1)
            handler.assert_any_call(str(dummy_file))

    def test_config_directory_watch(self):
        # Given
        changed = Event()
        handler = MagicMock(spec=OnConfigFileChanged)
        handler.side_effect = lambda config_path: changed.set()
        observer = Observer()

        with ConfigWatcher(observer) as watcher:
            watcher.register(handler)

            dummy_dir = TEST_FILE_SYSTEM_ROOT / "dummy_dir"
            dummy_dir.mkdir(exist_ok=True)
            watcher.watch(dummy_dir)

            watcher.start()

            # When
            dummy_file = dummy_dir / "dummy.conf"
            create_file(dummy_file)

            # Then
            assert changed.wait(1)
            handler.assert_any_call(str(dummy_file))
