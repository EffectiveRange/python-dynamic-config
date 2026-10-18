from unittest import TestCase
from common_utility import create_directory, create_file, delete_directory
from argparse import BooleanOptionalAction
from threading import Event
from watchdog.observers import Observer
from context_logger import setup_logging
from dynamic_config.cache import ConfigCache
from dynamic_config.config import DynamicConfig
from dynamic_config.parser import ConfigArgumentParser
from dynamic_config.source import ArgumentSource, DefaultSource, FileSource, DirectorySource
from dynamic_config.watcher import ConfigWatcher
from tests.utils import TEST_APPLICATION_NAME, TEST_FILE_SYSTEM_ROOT


class TestConfigUpdateHandling(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()
        delete_directory(TEST_FILE_SYSTEM_ROOT)

    def test_config_update(self):
        # Given
        changed = Event()
        cache = ConfigCache()
        parser = ConfigArgumentParser()
        parser.add_config_argument("--dynamic-default-str", dynamic=True, default="value")
        parser.add_config_argument("--default-int", type=int, default=0)
        group1 = parser.add_config_group("section1")
        group1.add_config_argument("--dynamic-default-bool", dynamic=True, action=BooleanOptionalAction, default=False)
        group1.add_config_argument("--dynamic-int", type=int, dynamic=True)

        config_file = TEST_FILE_SYSTEM_ROOT / "config" / "test.conf"
        create_file(
            config_file,
            """
[default]
dynamic_default_str = value1
default_int = 1234

[section1]
dynamic_default_bool = true
dynamic_int = 5678
""",
        )

        config_dir = TEST_FILE_SYSTEM_ROOT / "config" / "test.conf.d"
        create_directory(config_dir)
        watcher = ConfigWatcher(Observer())
        watcher.watch(config_file)
        watcher.watch(config_dir)
        sources = [
            DefaultSource(parser),
            FileSource(parser, config_file),
            DirectorySource(parser, config_dir),
            ArgumentSource(parser),
        ]
        config = DynamicConfig(cache=cache, parser=parser, watcher=watcher, sources=sources)

        config.initialize()

        config.register(lambda file_path, changes: changed.set())

        # When
        create_file(
            config_dir / "new.conf",
            """
[default]
dynamic_default_str = new_value1
default_int = 4321

[section1]
dynamic_default_bool = false
dynamic_int = 8765
""",
        )

        # Then
        changed.wait(timeout=1)

        self.assertEqual(config.get().dynamic_default_str, "new_value1")
        self.assertEqual(config.get().default_int, 1234)
        self.assertEqual(config.get().dynamic_default_bool, False)
        self.assertEqual(config.get().dynamic_int, 8765)
