from argparse import Namespace
import os
from unittest import TestCase
from unittest.mock import MagicMock
from dynamic_config import ConfigArgumentParser
from dynamic_config import DefaultSource
from dynamic_config import FileSource
from dynamic_config.source import ArgumentSource, DirectorySource, EnvironmentSource
from tests.utils import TEST_RESOURCE_ROOT


class TestDefaultSource(TestCase):

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        parser.get_defaults.return_value = {
            "test1": "value",
            "test2": 1234,
        }

        source = DefaultSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertEqual({
            "test1": "value",
            "test2": 1234,
        }, config)

    def test_get_namespace(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        parser.get_defaults.return_value = {
            "test1": "value",
            "test2": 1234,
        }

        source = DefaultSource(parser)

        # When
        config = source.get_namespace()

        # Then
        self.assertIsNotNone(config)
        self.assertEqual(config.test1, "value")
        self.assertEqual(config.test2, 1234)


class TestFileSource(TestCase):

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        file_path = f"{TEST_RESOURCE_ROOT}/config/test-config.conf"

        source = FileSource(parser, file_path)

        # When
        config = source.get_config()

        # Then
        self.assertEqual({
            "test1": "value1",
            "test2": "0",
            "test3": "true",
            "test4": "1111"
        }, config)

    def test_get_namespace(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_config.return_value = mock_config
        file_path = f"{TEST_RESOURCE_ROOT}/config/test-config.conf"

        source = FileSource(parser, file_path)

        # When
        config = source.get_namespace()

        # Then
        self.assertEqual(config, mock_config)
        parser.parse_config.assert_called_with({
            "test1": "value1",
            "test2": "0",
            "test3": "true",
            "test4": "1111"
        })


class TestDirectorySource(TestCase):

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        dir_path = f"{TEST_RESOURCE_ROOT}/config/test-config.d"

        source = DirectorySource(parser, dir_path, pattern="*.conf")

        # When
        config = source.get_config()

        # Then
        self.assertEqual({
            "test1": "another_value",
            "test2": "5678",
            "test3": "false",
            "test4": "5678",
            "test5": "false",
            "test6": "another_value"
        }, config)

    def test_get_namespace(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_config.return_value = mock_config
        dir_path = f"{TEST_RESOURCE_ROOT}/config/test-config.d"

        source = DirectorySource(parser, dir_path, pattern="*.conf")

        # When
        config = source.get_namespace()

        # Then
        self.assertEqual(config, mock_config)
        parser.parse_config.assert_called_with({
            "test1": "another_value",
            "test2": "5678",
            "test3": "false",
            "test4": "5678",
            "test5": "false",
            "test6": "another_value"
        })


class TestEnvironmentSource(TestCase):

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        prefix = "TEST_PREFIX_"
        os.environ["TEST_PREFIX_TEST1"] = "value1"
        os.environ["TEST_PREFIX_TEST2"] = "0"
        os.environ["TEST_PREFIX_TEST3"] = "true"
        os.environ["TEST_PREFIX_TEST4"] = "1111"

        source = EnvironmentSource(parser, prefix=prefix)

        # When
        config = source.get_config()

        # Then
        self.assertEqual({
            "test1": "value1",
            "test2": "0",
            "test3": "true",
            "test4": "1111"
        }, config)

    def test_get_namespace(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_config.return_value = mock_config
        prefix = "TEST_PREFIX_"
        os.environ["TEST_PREFIX_TEST1"] = "value1"
        os.environ["TEST_PREFIX_TEST2"] = "0"
        os.environ["TEST_PREFIX_TEST3"] = "true"
        os.environ["TEST_PREFIX_TEST4"] = "1111"

        source = EnvironmentSource(parser, prefix=prefix)

        # When
        config = source.get_namespace()

        # Then
        self.assertEqual(config, mock_config)
        parser.parse_config.assert_called_with({
            "test1": "value1",
            "test2": "0",
            "test3": "true",
            "test4": "1111"
        })


class TestArgumentSource(TestCase):

    def test_get_config(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        parser.parse_args.return_value = Namespace(test1="value1", test2=0)
        source = ArgumentSource(parser)

        # When
        config = source.get_config()

        # Then
        self.assertEqual({
            "test1": "value1",
            "test2": 0
        }, config)

    def test_get_namespace(self):
        # Given
        parser = MagicMock(spec=ConfigArgumentParser)
        mock_config = MagicMock(spec=Namespace)
        parser.parse_args.return_value = mock_config
        source = ArgumentSource(parser)

        # When
        config = source.get_namespace()

        # Then
        self.assertEqual(config, mock_config)
