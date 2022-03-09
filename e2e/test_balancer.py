import unittest

from e2e.test_util import TEST_NETWORK_FILE, TEST_FILE, drop_files
from src.dune_analytics import DuneAnalytics
from src.fetch.balancer_gno import balancer_gno
from src.fetch.gno_holders import fetch_gno_holders


class BalancerTests(unittest.TestCase):

    @drop_files
    def test_balancer_split(self):
        dune = DuneAnalytics.new_from_environment()
        self.assertEqual(balancer_gno(dune, block_number="0", load_from=TEST_FILE), [])

        snapshot_block = "13974427"
        snapshot_results = balancer_gno(
            dune,
            block_number=snapshot_block,
            load_from=TEST_FILE
        )
        gno_holders = fetch_gno_holders(
            dune,
            network='mainnet',
            block_number=snapshot_block,
            load_from=TEST_NETWORK_FILE,
        )
        vault_balance = gno_holders['0xba12222222228d8ba445958a75a0704d566bf2c8'].amount
        self.assertEqual(
            sum(map(lambda x: x.gno_balance, snapshot_results)),
            vault_balance,
        )


if __name__ == '__main__':
    unittest.main()
