import os
import unittest

from src.fetch.contracts import ContractDetector

NODE_URL = os.environ['NODE_URL']


class TestCodeGetter(unittest.TestCase):

    def setUp(self) -> None:
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

    def test_limited_is_contract(self):
        contract_detector = ContractDetector(
            max_batch_size=2,
            node_url=NODE_URL,
            addresses=self.addresses
        )
        with self.assertRaises(RuntimeError):
            contract_detector._limited_is_contract(self.addresses)

        contract_detector.max_batch_size = len(self.addresses)

        self.assertEqual(
            contract_detector._limited_is_contract(self.addresses),
            self.expected
        )

    def test_results(self):
        contract_detector = ContractDetector(
            max_batch_size=2,
            node_url=NODE_URL,
            addresses=self.addresses
        )

        self.assertEqual(contract_detector.results(), self.expected)

    def test_fail_with_bad_input(self):
        contract_detector = ContractDetector(
            max_batch_size=2,
            node_url=NODE_URL,
            addresses=["Bad Input"]
        )
        with self.assertRaises(IOError):
            contract_detector.results()

    def test_limitations(self):
        num_items = 1000
        long_list = [
            "0x" + f"{i}".zfill(40)
            for i in range(num_items)
        ]
        detector = ContractDetector(
            max_batch_size=num_items // 10,
            node_url=NODE_URL,
            addresses=long_list
        )
        results = detector.results()
        self.assertEqual(len(results), num_items)


if __name__ == '__main__':
    unittest.main()
