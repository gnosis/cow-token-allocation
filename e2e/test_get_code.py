import os
import unittest

from src.fetch.contracts import EvmAccountInfo
from src.files import NetworkFile

NODE_URL = {
    'mainnet': os.environ.get('NODE_URL'),
    'gchain': 'https://rpc.gnosischain.com/',
}

test_file = NetworkFile(name="test-file.csv", path='./out/test')


class TestCodeGetter(unittest.TestCase):

    def setUp(self) -> None:
        self.dummy_file = test_file
        self.addresses = [
            "0x9008D19f58AAbD9eD0D60971565AA8510560ab41",  # GPv2Settlement
            "0x6810e776880c02933d47db1b9fc05908e5386b96",  # GnosisToken
            "0xba12222222228d8ba445958a75a0704d566bf2c8",  # BalancerVault
            "0xa4A6A282A7fC7F939e01D62D884355d79f5046C1",  # EOA
        ]
        self.expected = {
            "0x9008D19f58AAbD9eD0D60971565AA8510560ab41": True,
            "0x6810e776880c02933d47db1b9fc05908e5386b96": True,
            "0xba12222222228d8ba445958a75a0704d566bf2c8": True,
            "0xa4A6A282A7fC7F939e01D62D884355d79f5046C1": False
        }

    @staticmethod
    def drop_files(func):
        def wrapped_func(self):
            func(self)
            try:
                os.remove(test_file.filename('mainnet').filename())
            except FileNotFoundError:
                pass
            try:
                os.remove(test_file.filename('gchain').filename())
            except FileNotFoundError:
                pass

        return wrapped_func

    @drop_files
    def test_limited_is_contract(self):
        contract_detector = EvmAccountInfo(
            max_batch_size=2,
            node_url=NODE_URL['mainnet'],
            addresses=self.addresses,
            network='mainnet'
        )
        with self.assertRaises(RuntimeError):
            contract_detector._limited_is_contract(self.addresses)

        contract_detector.max_batch_size = len(self.addresses)

        self.assertEqual(
            contract_detector._limited_is_contract(self.addresses),
            self.expected
        )

    @drop_files
    def test_results(self):
        contract_detector = EvmAccountInfo(
            max_batch_size=2,
            node_url=NODE_URL['mainnet'],
            addresses=self.addresses,
            network='mainnet'
        )

        self.assertEqual(contract_detector.contracts(self.dummy_file), self.expected)

    def test_fail_with_bad_input(self):
        contract_detector = EvmAccountInfo(
            max_batch_size=2,
            node_url=NODE_URL['mainnet'],
            addresses=["Bad Input"],
            network='mainnet'
        )
        with self.assertRaises(IOError):
            contract_detector.contracts(self.dummy_file)

    @drop_files
    def test_limitations(self):
        num_items = 1000
        long_list = [
            "0x" + f"{i}".zfill(40)
            for i in range(num_items)
        ]
        detector = EvmAccountInfo(
            max_batch_size=num_items // 3,
            node_url=NODE_URL['mainnet'],
            addresses=long_list,
            network='mainnet'
        )
        results = detector.contracts(self.dummy_file)
        self.assertEqual(len(results), num_items)

    @drop_files
    def test_null_balances(self):
        without_balance = [
            "0x" + f"{42}".zfill(40),
            "0x" + f"{31}".zfill(40),
        ]
        fetcher = EvmAccountInfo(
            node_url=NODE_URL['gchain'],
            addresses=without_balance,
            network='gchain'
        )
        self.assertEqual(fetcher.get_null_balances(), set(without_balance))

        with_balance = ['0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d']
        fetcher.addresses = with_balance
        self.assertEqual(fetcher.get_null_balances(), set())


if __name__ == '__main__':
    unittest.main()
