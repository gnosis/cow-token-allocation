import os

from src.constants import FILE_OUT_PATH
from src.files import NetworkFile, File

TEST_FILE = File(name="test-file.csv", path=FILE_OUT_PATH)
TEST_NETWORK_FILE = NetworkFile(name="test-network-file.csv", path=FILE_OUT_PATH)


def drop_files(func):
    def wrapped_func(self):
        func(self)
        try:
            os.remove(TEST_NETWORK_FILE.filename('mainnet').filename())
        except FileNotFoundError:
            pass
        try:
            os.remove(TEST_FILE.filename())
        except FileNotFoundError:
            pass
        try:
            os.remove(TEST_NETWORK_FILE.filename('gchain').filename())
        except FileNotFoundError:
            pass

    return wrapped_func
