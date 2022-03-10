import unittest

from e2e.test_util import TEST_NETWORK_FILE, drop_files
from src.constants import NODE_URL
from src.fetch.contracts import EvmAccountInfo


class TestCodeGetter(unittest.TestCase):

    def setUp(self) -> None:
        self.addresses = [
            "0xc0602240900fe3e8f4d4ee3f588dc6ad6251fd97",  # Wallet Contract
            "0xa4A6A282A7fC7F939e01D62D884355d79f5046C1",  # EOA
        ]
        self.expected = {
            "0xc0602240900fe3e8f4d4ee3f588dc6ad6251fd97": "0x363d3d373d3d3d363d732a2b85eb1054d6f0c6c2e37da05ed3e5fea684ef5af43d82803e903d91602b57fd5bf3",
        }

    @drop_files
    def test_results(self):
        contract_detector = EvmAccountInfo(
            max_batch_size=2,
            node_url=NODE_URL['mainnet'],
            addresses=self.addresses,
            network='mainnet'
        )

        self.assertEqual(
            self.expected.keys(),
            contract_detector.contracts(TEST_NETWORK_FILE)
        )

    def test_fail_with_bad_input(self):
        contract_detector = EvmAccountInfo(
            max_batch_size=2,
            node_url=NODE_URL['mainnet'],
            addresses=["Bad Input"],
            network='mainnet'
        )
        with self.assertRaises(IOError):
            contract_detector.contracts(TEST_NETWORK_FILE)

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
