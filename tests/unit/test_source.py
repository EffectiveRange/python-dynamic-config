from argparse import ArgumentParser, Namespace
import os
from unittest import TestCase
from unittest.mock import MagicMock

from context_logger import setup_logging
from dynamic_config import (
    Parser,
    ConfigArgumentParser,
    DefaultSource,
    FileSource,
    ArgumentSource,
    DirectorySource,
    EnvironmentSource,
)
from tests.utils import TEST_APPLICATION_NAME, TEST_RESOURCE_ROOT


class TestDefaultSource(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=Parser)
        parser.get_defaults.return_value = {
            "test1": "value",
            "test2": 1234,
        }

        source = DefaultSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertIsNotNone(config)
        self.assertEqual(config.test1, "value")
        self.assertEqual(config.test2, 1234)

    def test_get_config_preserves_none(self):
        # Given
        parser = ConfigArgumentParser()
        parser.add_config_argument("--image", default=None)
        source = DefaultSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertIsNone(config.image)

    def test_get_config_converts_string_defaults(self):
        # Given
        def parse_size(value):
            return int(value[:-1]) * 1024**3

        parser = ConfigArgumentParser()
        parser.add_config_argument("--memory", default="4G", type=parse_size)
        source = DefaultSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertEqual(config.memory, 4294967296)


class TestFileSource(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=Parser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_config.return_value = mock_config
        file_path = TEST_RESOURCE_ROOT / "config" / "test-config.conf"

        source = FileSource(parser, file_path)

        # When
        config = source.get_config()

        # Then
        self.assertEqual(config, mock_config)
        parser.parse_config.assert_called_with({"test1": "value1", "test2": "0", "test3": "true", "test4": "1111"})


class TestDirectorySource(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=Parser)
        parser.parse_config.return_value = MagicMock(spec=Namespace)
        dir_path = TEST_RESOURCE_ROOT / "config" / "test-config.d"

        source = DirectorySource(parser, dir_path, pattern="*.conf")

        # When
        config = source.get_config()

        # Then
        self.assertEqual(config, parser.parse_config.return_value)
        parser.parse_config.assert_called_once_with(
            {
                "test1": "another_value",
                "test2": "5678",
                "test3": "false",
                "test4": "5678",
                "test5": "false",
                "test6": "another_value",
            }
        )


class TestEnvironmentSource(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=Parser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_config.return_value = mock_config
        prefix = "TEST_PREFIX_"
        os.environ["TEST_PREFIX_TEST1"] = "value1"
        os.environ["TEST_PREFIX_TEST2"] = "0"
        os.environ["TEST_PREFIX_TEST3"] = "true"
        os.environ["TEST_PREFIX_TEST4"] = "1111"

        source = EnvironmentSource(parser, prefix=prefix)

        # When
        config = source.get_config()

        # Then
        self.assertEqual(config, mock_config)
        parser.parse_config.assert_called_with({"test1": "value1", "test2": "0", "test3": "true", "test4": "1111"})


class TestArgumentSource(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, "DEBUG", warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ArgumentParser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_known_args.return_value = (mock_config, [])
        source = ArgumentSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertEqual(config, mock_config)
