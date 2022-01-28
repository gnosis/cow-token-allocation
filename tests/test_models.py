import unittest
from fractions import Fraction

from src.fetch.lp_holders import LiquidityProportion


class TestLiquidityProportion(unittest.TestCase):
    def test_to_liquidity_position(self):
        proportion = LiquidityProportion(
            account="0x1",
            pool="0x2",
            proportion=Fraction(1, 10)
        )
        position = proportion.to_liquidity_position(100)
        self.assertEqual(position.gno_amount, 10)


if __name__ == '__main__':
    unittest.main()
