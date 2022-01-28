import unittest
from datetime import datetime, date

from src.fetch.trader_data import CowSwapTrader
from src.models import Allocation


def date_from_postgres(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


class TestTraderData(unittest.TestCase):
    def test_compute_allocation_tier(self):
        traders = [
            CowSwapTrader(
                account=f"0x{i}",
                eligible_volume=10 ** (i + 3),
                num_trades=1,
                first_trade=date_from_postgres('2021-01-01'),
                last_trade=date_from_postgres('2021-02-01'),
            )
            for i in range(5)
        ]
        expected = [
            0,  # 10^3 is on lower boundary of tier 0
            1,  # 10^4 is on upper boundary of tier 1
            3,  # 10^5 is lower boundary of tier 3
            5,  # 10^6 is lower boundary of tier 5
            5,  # 10^7 is above lower boundary of tier 5
        ]
        for trader, expected_tier in zip(traders, expected):
            self.assertEqual(trader.allocation_tier, expected_tier)

    def test_merge(self):
        mainnet_trader = CowSwapTrader(
            account=f"0x1",
            eligible_volume=10,
            num_trades=1,
            first_trade=date_from_postgres('2021-01-01'),  # January
            last_trade=date_from_postgres('2021-03-01'),  # March
        )
        gchain_trader = CowSwapTrader(
            account=f"0x1",
            eligible_volume=10,
            num_trades=1,
            first_trade=date_from_postgres('2021-02-01'),  # February
            last_trade=date_from_postgres('2021-04-01'),  # April
        )

        expected = CowSwapTrader(
            account=f"0x1",
            eligible_volume=20,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),  # January
            last_trade=date_from_postgres('2021-04-01'),  # April
        )
        self.assertEqual(expected, mainnet_trader.merge(gchain_trader))
        self.assertEqual(expected, gchain_trader.merge(mainnet_trader))

        other_trader = CowSwapTrader(
            account=f"0x2",
            eligible_volume=1,
            num_trades=1,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-04-01'),
        )
        with self.assertRaises(AssertionError):
            mainnet_trader.merge(other_trader)

    def test_is_eligible(self):
        eligible_trader = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=3,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-03-01'),
        )
        self.assertTrue(eligible_trader.is_eligible())
        insufficient_volume = CowSwapTrader(
            account=f"0x1",
            eligible_volume=999,
            num_trades=3,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-03-01'),
        )
        self.assertFalse(insufficient_volume.is_eligible())
        insufficient_num_trades = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-03-01'),
        )
        self.assertFalse(insufficient_num_trades.is_eligible())
        insufficient_days_between = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-02'),
        )
        self.assertFalse(insufficient_days_between.is_eligible())

    def test_days_between_first_and_last(self):
        zero_days_between = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-01'),
        )
        self.assertEqual(0, zero_days_between.days_between_first_and_last())

        one_days_between = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-02'),
        )
        self.assertEqual(1, one_days_between.days_between_first_and_last())
        four_days_between = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-05'),
        )
        self.assertEqual(4, four_days_between.days_between_first_and_last())

    def test_to_primary_allocation(self):
        not_eligible = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-05'),
        )
        with self.assertRaises(AssertionError):
            not_eligible.to_primary_allocation(total_weight=10, supply=100)

        eligible = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=3,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-02-01'),
        )
        self.assertEqual(
            Allocation(account='0x1', amount=10),
            eligible.to_primary_allocation(total_weight=10, supply=100)
        )

    def test_to_consolation_allocation(self):
        not_eligible = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1,
            num_trades=2,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-01-05'),
        )
        self.assertEqual(
            Allocation(account='0x1', amount=10),
            not_eligible.to_consolation_allocation(num_recipients=10, supply=100)
        )

        eligible = CowSwapTrader(
            account=f"0x1",
            eligible_volume=1000,
            num_trades=3,
            first_trade=date_from_postgres('2021-01-01'),
            last_trade=date_from_postgres('2021-02-05'),
        )
        with self.assertRaises(AssertionError):
            eligible.to_consolation_allocation(num_recipients=10, supply=100)


if __name__ == '__main__':
    unittest.main()
