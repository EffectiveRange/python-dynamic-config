import os
from pathlib import Path

TEST_APPLICATION_NAME = "python-dynamic-config"
TEST_RESOURCE_ROOT = Path(os.path.dirname(__file__)).absolute()
TEST_FILE_SYSTEM_ROOT = TEST_RESOURCE_ROOT.joinpath("test_root").absolute()
