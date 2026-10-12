from unittest import TestCase
from unittest.mock import MagicMock
from dynamic_config import (
    ConfigArgumentParser,
    ConfigBuilder,
    DynamicConfig,
    DefaultSource,
    FileSource,
    DirectorySource,
    EnvironmentSource,
    ArgumentSource,
    ConfigCache,
)
from dynamic_config.parser import ConfigAction
from dynamic_config.source import ConfigSource


class TestConfigBuilder(TestCase):

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

    def test_get(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        config = DynamicConfig(cache, MagicMock(spec=ConfigArgumentParser), [])

        # When
        result = config.get()

        # Then
        self.assertEqual(result, cache)

    def test_get_snapshot(self):
        # Given
        cache = MagicMock(spec=ConfigCache)
        config = DynamicConfig(cache, MagicMock(spec=ConfigArgumentParser), [])

        # When
        result = config.get_snapshot()

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
            "test2": MagicMock(spec=ConfigAction),
            "test4": MagicMock(spec=ConfigAction),
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
        config = DynamicConfig(cache, parser, sources)

        # When
        config.refresh()

        # Then
        cache.update.assert_called_once_with(
            {"test1": "value1", "test2": "value2-1", "test3": "value3", "test4": "value4-2"}
        )
