from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from dynamic_config import (
    ConfigSource,
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
    ConfigCache,
    Watcher,
)
from tests.utils import TEST_APPLICATION_NAME


class TestConfigBuilder(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

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
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_initialize(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[ConfigSource] = []
        config = DynamicConfig(cache, parser, watcher, sources)

        # When
        config.initialize()

        # Then
        watcher.register.assert_called_once_with(config._on_config_file_change)
        watcher.start.assert_called_once()

    def test_destroy(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        parser = MagicMock(spec=Parser)
        watcher = MagicMock(spec=Watcher)
        sources: list[ConfigSource] = []
        config = DynamicConfig(cache, parser, watcher, sources)

        # When
        config.destroy()

        # Then
        watcher.stop.assert_called_once()
        watcher.deregister.assert_called_once_with(config._on_config_file_change)
        cache.clear.assert_called_once()

    def test_get(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        config = DynamicConfig(cache, MagicMock(spec=Parser), MagicMock(spec=Watcher), [])

        # When
        result = config.get()

        # Then
        self.assertEqual(result, cache.get())

    def test_get_snapshot(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        config = DynamicConfig(cache, MagicMock(spec=Parser), MagicMock(spec=Watcher), [])

        # When
        result = config.snapshot()

        # Then
        cache.snapshot.assert_called_once()
        self.assertEqual(result, cache.snapshot())

    def test_refresh(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        cache.snapshot.return_value.values.return_value = {
            "test1": "value1",
            "test2": "value2",
            "test3": "value3",
            "test4": "value4",
        }
        parser = MagicMock(spec=ConfigArgumentParser)
        parser.get_dynamic_arguments.return_value = {
            "test2": MagicMock(spec=ConfigArgument),
            "test4": MagicMock(spec=ConfigArgument),
            "test5": MagicMock(spec=ConfigArgument),
        }
        source1 = MagicMock(spec=ConfigSource)
        source1.get_config.return_value = {
            "test1": "value1-1",
            "test2": "value2-1",
            "test3": "value3",
            "test4": "value4-1",
        }
        source2 = MagicMock(spec=ConfigSource)
        source2.get_config.return_value = {"test3": "value3-2", "test4": "value4-2"}
        sources: list[ConfigSource] = [source1, source2]
        config = DynamicConfig(cache, parser, MagicMock(spec=Watcher), sources)

        # When
        config.refresh()

        # Then
        cache.update.assert_called_once_with(
            {"test1": "value1", "test2": "value2-1", "test3": "value3", "test4": "value4-2"}
        )
