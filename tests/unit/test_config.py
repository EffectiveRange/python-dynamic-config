from argparse import Namespace
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from dynamic_config import (
    Source,
    ConfigArgument,
    Parser,
    ConfigArgumentParser,
    ConfigBuilder,
    DynamicConfig,
    DefaultSource,
    FileSource,
    DirectorySource,
    EnvironmentSource,
    ArgumentSource,
    Cache,
    Watcher,
)

from dynamic_config.config import ConfigChange, OnConfigChangeEvent
from tests.utils import TEST_APPLICATION_NAME


class TestConfigBuilder(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_with_defaults(self):
        # Given
        parser = ConfigArgumentParser()
        builder = ConfigBuilder(parser)

        # When
        builder = builder.with_defaults()

        # Then
        self.assertIsInstance(builder, ConfigBuilder)
        self.assertIsInstance(builder._sources[0], DefaultSource)

    def test_with_file(self):
        # Given
        parser = ConfigArgumentParser()
        builder = ConfigBuilder(parser)

        # When
        builder = builder.with_file("config.conf")

        # Then
        self.assertIsInstance(builder, ConfigBuilder)
        self.assertIsInstance(builder._sources[0], FileSource)

    def test_with_directory(self):
        # Given
        parser = ConfigArgumentParser()
        builder = ConfigBuilder(parser)

        # When
        builder = builder.with_directory("config_dir")

        # Then
        self.assertIsInstance(builder, ConfigBuilder)
        self.assertIsInstance(builder._sources[0], DirectorySource)

    def test_with_environment(self):
        # Given
        parser = ConfigArgumentParser()
        builder = ConfigBuilder(parser)

        # When
        builder = builder.with_environment()

        # Then
        self.assertIsInstance(builder, ConfigBuilder)
        self.assertIsInstance(builder._sources[0], EnvironmentSource)

    def test_with_arguments(self):
        # Given
        parser = ConfigArgumentParser()
        builder = ConfigBuilder(parser)

        # When
        builder = builder.with_arguments()

        # Then
        self.assertIsInstance(builder, ConfigBuilder)
        self.assertIsInstance(builder._sources[0], ArgumentSource)

    def test_build(self):
        # Given
        parser = ConfigArgumentParser()
        builder = (
            ConfigBuilder(parser)
            .with_defaults()
            .with_directory("config_dir")
            .with_file("config.conf")
            .with_environment()
            .with_arguments()
        )

        # When
        config = builder.build()

        # Then
        self.assertIsInstance(config, DynamicConfig)
        self.assertIsInstance(builder._sources[0], DefaultSource)
        self.assertIsInstance(builder._sources[1], DirectorySource)
        self.assertIsInstance(builder._sources[2], FileSource)
        self.assertIsInstance(builder._sources[3], EnvironmentSource)
        self.assertIsInstance(builder._sources[4], ArgumentSource)
        self.assertEqual(builder._sources, config._sources)


class TestDynamicConfig(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_initialize(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)

        # When
        config.initialize()

        # Then
        watcher.register.assert_called_once_with(config._on_config_file_change)
        watcher.start.assert_called_once()

    def test_deinitialize(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)

        # When
        config.deinitialize()

        # Then
        watcher.stop.assert_called_once()
        watcher.deregister.assert_called_once_with(config._on_config_file_change)
        cache.clear.assert_called_once()

    def test_get(self):
        # Given
        cache = MagicMock(spec=Cache)
        config = DynamicConfig(cache, MagicMock(spec=Parser), MagicMock(spec=Watcher), [])

        # When
        result = config.get()

        # Then
        self.assertEqual(result, cache.get())

    def test_get_snapshot(self):
        # Given
        cache = MagicMock(spec=Cache)
        config = DynamicConfig(cache, MagicMock(spec=Parser), MagicMock(spec=Watcher), [])

        # When
        result = config.snapshot()

        # Then
        cache.snapshot.assert_called_once()
        self.assertEqual(result, cache.snapshot())

    def test_refresh_dynamic_only(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        parser.get_dynamic_arguments.return_value = {
            "test2": MagicMock(spec=ConfigArgument),
            "test4": MagicMock(spec=ConfigArgument),
            "test5": MagicMock(spec=ConfigArgument),
        }
        source1 = MagicMock(spec=Source)
        source1.get_config.return_value = Namespace(
            test1="value1-1",
            test2="value2-1",
            test3="value3",
            test4="value4-1",
        )
        source2 = MagicMock(spec=Source)
        source2.get_config.return_value = Namespace(
            test3="value3-2",
            test4="value4-2",
        )
        sources: list[Source] = [source1, source2]
        config = DynamicConfig(cache, parser, MagicMock(spec=Watcher), sources)

        # When
        config.refresh()

        # Then
        cache.update.assert_called_once_with({"test2": "value2-1", "test4": "value4-2"})

    def test_refresh_all(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        parser.get_dynamic_arguments.return_value = {
            "test2": MagicMock(spec=ConfigArgument),
            "test4": MagicMock(spec=ConfigArgument),
            "test5": MagicMock(spec=ConfigArgument),
        }
        source1 = MagicMock(spec=Source)
        source1.get_config.return_value = Namespace(
            test1="value1-1",
            test2="value2-1",
            test3="value3",
            test4="value4-1",
        )
        source2 = MagicMock(spec=Source)
        source2.get_config.return_value = Namespace(
            test3="value3-2",
            test4="value4-2",
        )
        sources: list[Source] = [source1, source2]
        config = DynamicConfig(cache, parser, MagicMock(spec=Watcher), sources)

        # When
        config.refresh(dynamic_only=False)

        # Then
        cache.update.assert_called_once_with(
            {"test1": "value1-1", "test2": "value2-1", "test3": "value3-2", "test4": "value4-2"}
        )

    def test_register(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)
        handler = MagicMock(spec=OnConfigChangeEvent)

        # When
        config.register(handler)

        # Then
        self.assertIn(handler, config._handlers)

    def test_register_duplicate(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)
        handler = MagicMock(spec=OnConfigChangeEvent)
        config.register(handler)

        # When
        config.register(handler)

        # Then
        self.assertEqual(config._handlers.count(handler), 1)

    def test_deregister(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)
        handler = MagicMock(spec=OnConfigChangeEvent)
        config._handlers.append(handler)

        # When
        config.deregister(handler)

        # Then
        self.assertNotIn(handler, config._handlers)

    def test_deregister_nonexistent(self):
        # Given
        cache = MagicMock(spec=Cache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)
        handler = MagicMock(spec=OnConfigChangeEvent)

        # When
        config.deregister(handler)

        # Then
        self.assertNotIn(handler, config._handlers)

    def test_on_config_file_change(self):
        # Given
        cache = MagicMock(spec=Cache)
        cache.snapshot.return_value.values.side_effect = [
            {"test1": "value1", "test2": "value2", "test3": "value3"},
            {"test1": "value1-1", "test2": "value2", "test3": "value3-1"},
        ]
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[Source] = []
        config = DynamicConfig(cache, parser, watcher, sources)
        handler = MagicMock(spec=OnConfigChangeEvent)

        config.register(handler)

        file_path = "test.conf"
        changes = {
            "test1": ConfigChange("test1", "value1", "value1-1"),
            "test3": ConfigChange("test3", "value3", "value3-1"),
        }

        # When
        config._on_config_file_change(file_path)

        # Then
        handler.assert_called_once_with(file_path, changes)
