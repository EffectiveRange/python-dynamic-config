from argparse import Namespace
from unittest import TestCase

from context_logger import setup_logging

from dynamic_config.cache import ConfigCache, ConfigSnapshot
from tests.utils import TEST_APPLICATION_NAME


class TestConfigSnapshot(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = snapshot.key

        # Then
        self.assertEqual(result, "value")

    def test_immutable_set(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            snapshot.key = "new_value"

    def test_immutable_del(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            del snapshot.key

    def test_equality(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})
        namespace = Namespace(key="value")

        # When
        result = snapshot == namespace

        # Then
        self.assertTrue(result)

    def test_equality_when_not_namespace(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = snapshot == {"key": "value"}

        # Then
        self.assertFalse(result)

    def test_contains(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = "key" in snapshot

        # Then
        self.assertTrue(result)

    def test_values_method(self):
        # Given
        snapshot = ConfigSnapshot({"key": "value"})

        # When
        result = snapshot.values()

        # Then
        self.assertEqual(result, {"key": "value"})


class TestConfigCache(TestCase):

    @classmethod
    def setUpClass(cls):
        setup_logging(TEST_APPLICATION_NAME, 'DEBUG', warn_on_overwrite=False)

    def setUp(self):
        print()

    def test_get(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        result = cache.key

        # Then
        self.assertEqual(result, "value")

    def test_get_missing(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When / Then
        with self.assertRaises(AttributeError):
            cache.missing_key

    def test_immutable_set(self):
        # Given
        cache = ConfigCache()

        # When / Then
        with self.assertRaises(AttributeError):
            cache.key = "new_value"

    def test_equality(self):
        # Given
        cache = ConfigCache({"key": "value"})
        namespace = Namespace(key="value")

        # When
        result = cache == namespace

        # Then
        self.assertTrue(result)

    def test_equality_when_not_namespace(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        result = cache == {"key": "value"}

        # Then
        self.assertFalse(result)

    def test_contains(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        result = "key" in cache

        # Then
        self.assertTrue(result)

    def test_snapshot(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        snapshot = cache.snapshot()

        # Then
        self.assertEqual(snapshot.values(), {"key": "value"})

    def test_update(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        cache.update({"key": "new_value"})

        # Then
        self.assertEqual(cache.key, "new_value")

    def test_update_creates_new_snapshot(self):
        # Given
        cache = ConfigCache({"key": "value"})
        old_snapshot = cache.snapshot()
        cache.update({"key": "new_value"})

        # When
        new_snapshot = cache.snapshot()

        # Then
        self.assertNotEqual(old_snapshot, new_snapshot)
        self.assertEqual(old_snapshot.values(), {"key": "value"})
        self.assertEqual(new_snapshot.values(), {"key": "new_value"})

    def test_clear(self):
        # Given
        cache = ConfigCache({"key": "value"})

        # When
        cache.clear()

        # Then
        self.assertEqual(cache.snapshot().values(), {})
