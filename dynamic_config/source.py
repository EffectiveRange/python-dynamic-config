# SPDX-FileCopyrightText: 2024 Ferenc Nandor Janky <ferenj@effective-range.com>
# SPDX-FileCopyrightText: 2024 Attila Gombos <attila.gombos@effective-range.com>
# SPDX-License-Identifier: MIT

import os
import glob
from pathlib import Path
from typing import Any
from dynamic_config import Parser
from argparse import ArgumentParser, Namespace
from abc import ABC, abstractmethod
from configparser import ConfigParser
from context_logger import get_logger


class Source(ABC):

    @abstractmethod
    def get_config(self) -> Namespace: ...


class DefaultSource(Source):

    def __init__(self, parser: Parser) -> None:
        self._parser = parser
        self.log = get_logger(type(self).__name__)

    def get_config(self) -> Namespace:
        self.log.debug("Fetching default configuration")

        defaults = self._parser.get_defaults()

        return Namespace(**defaults)


class FileSource(Source):

    def __init__(self, parser: Parser, path: str | Path) -> None:
        self._parser = parser
        self._path = Path(path)
        self.log = get_logger(type(self).__name__)

    def get_config(self) -> Namespace:
        self.log.debug("Fetching configuration from file", file=self._path)

        config = self._get_file_config(self._path)

        return self._parser.parse_config(config)

    def _get_file_config(self, path: str | Path) -> dict[str, Any]:
        file_parser = ConfigParser(interpolation=None)
        file_parser.read(path)

        config = {}
        for section in file_parser.sections():
            for key, value in file_parser.items(section):
                config[key] = value

        return config


class DirectorySource(FileSource):

    def __init__(
        self,
        parser: Parser,
        dir_path: str | Path,
        pattern: str = "*.conf",
        recursive: bool = False,
    ) -> None:
        self._parser = parser
        self._dir_path = Path(dir_path)
        self._pattern = pattern
        self._recursive = recursive
        self.log = get_logger(type(self).__name__)

    def get_config(self) -> Namespace:
        self.log.debug("Fetching configuration from directory", dir=self._dir_path, pattern=self._pattern)

        config = {}

        file_paths = sorted(glob.glob(str(self._dir_path / self._pattern), recursive=self._recursive))

        for file_path in file_paths:
            file_config = self._get_file_config(file_path)
            config.update(file_config)

        return self._parser.parse_config(config)


class EnvironmentSource(Source):

    def __init__(self, parser: Parser, prefix: str = "") -> None:
        self._parser = parser
        self._prefix = prefix
        self.log = get_logger(type(self).__name__)

    def get_config(self) -> Namespace:
        self.log.debug("Fetching configuration from environment", prefix=self._prefix)

        config = {
            key.lower()[len(self._prefix) :]: value for key, value in os.environ.items() if key.startswith(self._prefix)
        }

        return self._parser.parse_config(config)


class ArgumentSource(Source):

    def __init__(self, parser: ArgumentParser) -> None:
        self._parser = parser
        self.log = get_logger(type(self).__name__)

    def get_config(self) -> Namespace:
        self.log.debug("Fetching configuration from command-line arguments")

        return self._parser.parse_known_args()[0]
