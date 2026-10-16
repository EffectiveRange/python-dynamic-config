from unittest import TestCase
from common_utility import create_file
from argparse import BooleanOptionalAction
import pytest
from watchdog.observers import Observer
from context_logger import setup_logging
from dynamic_config.cache import ConfigCache
from dynamic_config.config import DynamicConfig
from dynamic_config.parser import ConfigArgumentParser
from dynamic_config.source import ArgumentSource, DefaultSource, FileSource, DirectorySource
from dynamic_config.watcher import ConfigWatcher
from tests.utils import TEST_APPLICATION_NAME, TEST_FILE_SYSTEM_ROOT


@pytest.mark.skip(reason="wip")
class TestConfigUpdateHandling(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_config_update(self):
        # Given
        cache = ConfigCache()
        parser = ConfigArgumentParser()
        parser.add_config_argument("test1", dynamic=True, default="value")
        parser.add_config_argument("test2", type=int, default=0)
        group1 = parser.add_config_group("section1")
        group1.add_config_argument("test3", dynamic=True, action=BooleanOptionalAction, default=False)
        group1.add_config_argument("test4", type=int, dynamic=True)

        config_file = TEST_FILE_SYSTEM_ROOT / "config" / "test.conf"
        create_file(
            config_file,
            """
[default]
test1 = value1
test2 = 1234

[section1]
test3 = true
test4 = 5678
""",
        )

        config_dir = TEST_FILE_SYSTEM_ROOT / "config" / "test.conf.d"
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

        # When
        create_file(
            config_dir / "new.conf",
            """
[default]
test1 = new_value1
test2 = 4321

[section1]
test3 = false
test4 = 8765
""",
        )

        # Then
        self.assertEqual(config.get().test1, "new_value1")
        self.assertEqual(config.get().test2, 4321)
        self.assertEqual(config.get().test3, False)
        self.assertEqual(config.get().test4, 8765)
