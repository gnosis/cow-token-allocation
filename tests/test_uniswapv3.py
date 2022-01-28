import unittest

from src.constants import GNO_TOKEN
from src.fetch.univ3_gno import fetch_pools, fetch_univ3_gno
from src.files import File
from src.models import GnoHolder
from src.utils.univ3 import execute_query, Position, Pool


class TestUniswapV3Fetching(unittest.TestCase):
    def setUp(self) -> None:
        self.gno_token = GNO_TOKEN['mainnet']
        self.load_from = File("dummyfile", path="/tmp")

    def test_fetch_pools(self):
        block_number = 13974427
        known_pools = [
            "0xa46466ad5507be77ff5abdc27df9dfeda9bd7aee",  # GNO-WETH 1%
            "0xf56d08221b5942c428acc5de8f78489a97fc5599",  # GNO-WETH 0.3%
            "0x7b24f3f2c6fc51ca67c91bcdfeb07bc75249fd1d",  # STAKE-GNO
        ]
        fetched_pool_addresses = set([
            pool.address for pool in fetch_pools(block_number, self.gno_token)
        ])
        # Note that there could be more pools, so we check that know are a subset
        self.assertEqual(set(known_pools), fetched_pool_addresses)

        # Fetch pools one block before deployment of stake-gno pool
        # https://etherscan.io/tx/0xb5ef5080803f2ebc63e6e1d3bbda66dcd0101cc9e215eed86dee2c6224425b7a
        block_before_third_pool = 13556960
        fetched_pool_addresses = [
            pool.address for pool in
            fetch_pools(block_before_third_pool, self.gno_token)
        ]
        self.assertEqual([known_pools[0], known_pools[1]], fetched_pool_addresses)

        block_before_second_pool = 13088764
        fetched_pool_addresses = [
            pool.address for pool in
            fetch_pools(block_before_second_pool, self.gno_token)
        ]
        self.assertEqual([known_pools[0]], fetched_pool_addresses)

        block_before_all_pools = 12506297
        self.assertEqual([], fetch_pools(block_before_all_pools, self.gno_token))

    def test_fetch_positions(self):
        block_before_all_gno_pools = 12506297
        self.assertEqual(
            fetch_univ3_gno(block_before_all_gno_pools, self.gno_token, self.load_from),
            {}
        )
        # Position created at pool deployment:
        # https://etherscan.io/tx/0xdf8ac88c61315d6394590da1f4db654bed61eb3ccbd95dfd4574ea0097786e21
        expected_position = Position(
            liquidity=486537409445421775016,
            account='0x43905fa1d882383d45ce14203bf8b05e96d7f025',
            tick_lower=-28200,
            tick_upper=-22000,
            pool=Pool(
                address='0xa46466ad5507be77ff5abdc27df9dfeda9bd7aee',
                liquidity=0,
                sqrt_price=0,
                tick=None,
                queried_token_index=0
            ),
            token=self.gno_token
        )

        # TODO - uniswap code doesn't handle the case that Pool tick is null!
        #  https://github.com/gnosis/cow-airdrop/issues/79
        # self.assertEqual(
        #     fetch_positions(block_before_all_gno_pools + 1, self.gno_token),
        #     {'0x43905fa1d882383d45ce14203bf8b05e96d7f025': [expected_position]}
        # )
        #
        # gno_added = 351.730977107037373565
        # self.assertEqual(expected_position.gno_amount(), gno_added)

    def test_fetch_snapshot_positions(self):
        snapshot_block = 13974427
        positions = fetch_univ3_gno(snapshot_block, self.gno_token, self.load_from)

        print(positions)


class TestUniswapV3Utils(unittest.TestCase):
    def setUp(self) -> None:
        self.gno_token = GNO_TOKEN['mainnet']
        self.known_position = Position(
            account='0x262d23a2d916f6cf08e0235315aa51e22d142d0b',
            liquidity=9960379146413809147,
            tick_lower=-19440,
            tick_upper=-17880,
            pool=Pool(
                address='0xf56d08221b5942c428acc5de8f78489a97fc5599',
                liquidity=19537272358549520024637,
                sqrt_price=29195303592534882591060524447,
                tick=-19968,
                queried_token_index=0
            ),
            token=self.gno_token
        )

    def test_amount0_at_enter(self):
        # https://etherscan.io/tx/0xc4d80986c668b650618ab71e77ce80ea6b87c31f32dd3858627e24494ac40735
        enter_block = 13937938
        positions_at_enter = execute_query(
            known_position_query(enter_block)
        )['data']['positions']

        self.assertEqual(len(positions_at_enter), 1)
        enter_position = position_from_gql_response(
            positions_at_enter[0],
            self.gno_token
        )
        self.assertEqual(enter_position, self.known_position)
        self.assertEqual(enter_position.gno_amount(), 1975310305035215489)

    def test_amount0_at_snapshot(self):
        # Snapshot
        snapshot_block = 13974427
        positions_at_snapshot = execute_query(
            known_position_query(snapshot_block)
        )['data']['positions']

        self.assertEqual(len(positions_at_snapshot), 1)
        snapshot_position = position_from_gql_response(
            positions_at_snapshot[0],
            self.gno_token
        )
        expected_position_at_snapshot = Position(
            liquidity=9960379146413809147,
            account='0x262d23a2d916f6cf08e0235315aa51e22d142d0b',
            tick_lower=-19440,
            tick_upper=-17880,
            pool=Pool(
                address='0xf56d08221b5942c428acc5de8f78489a97fc5599',
                liquidity=20058775852597111838701,
                sqrt_price=30582684202898457702045392508,
                tick=-19039,
                queried_token_index=0
            ),
            token=self.gno_token
        )
        self.assertEqual(expected_position_at_snapshot, snapshot_position)
        self.assertEqual(snapshot_position.gno_amount(), 1452633721896451861)

    def test_amount0_at_exit(self):
        # https://etherscan.io/tx/0x7560f1ecef16e8b11ad61ee5adad0ff402acf8991b59a9358d8a2f849685e465
        exit_block = 14025779
        positions_at_exit = execute_query(
            known_position_query(exit_block)
        )['data']['positions']

        self.assertEqual(len(positions_at_exit), 1)
        exit_position = position_from_gql_response(
            positions_at_exit[0],
            self.gno_token
        )
        self.assertEqual(exit_position.gno_amount(), 0)

    def test_position_reduction(self):
        dummy_pool = Pool("", 0, 0, 0, 0)
        positions = [
            Position(account="0x1", liquidity=0, tick_lower=0, tick_upper=0,
                     pool=dummy_pool, token=""),
            Position(account="0x2", liquidity=0, tick_lower=0, tick_upper=0,
                     pool=dummy_pool, token=""),
        ]

        with self.assertRaises(AssertionError):
            # Different accounts don't reduce
            Position.reduce_to_gno_holder(positions)

        self.assertEqual(
            Position.reduce_to_gno_holder([self.known_position, self.known_position]),
            GnoHolder(
                self.known_position.account,
                2 * self.known_position.gno_amount()
            )
        )


def position_from_gql_response(gql_position, token) -> Position:
    pool_data = gql_position['pool']
    pool = Pool(
        liquidity=int(pool_data['liquidity']),
        sqrt_price=int(pool_data['sqrtPrice']),
        tick=int(pool_data['tick']),
        address=pool_data['id'],
        queried_token_index=0
    )
    return Position(
        liquidity=int(gql_position['liquidity']),
        account=gql_position['owner'],
        tick_lower=int(gql_position['tickLower']['tickIdx']),
        tick_upper=int(gql_position['tickUpper']['tickIdx']),
        pool=pool,
        token=token
    )


def known_position_query(block_number: int) -> str:
    return f"""
        {{
          positions(
            block: {{ number: {block_number} }}
            where: {{
              pool: "0xf56d08221b5942c428acc5de8f78489a97fc5599"
              owner: "0x262d23a2d916f6cf08e0235315aa51e22d142d0b"
            }}
          ) {{
            owner
            liquidity
            tickLower {{ tickIdx }}
            tickUpper {{ tickIdx }}
            pool {{
              id
              liquidity
              tick
              sqrtPrice
            }}
          }}
        }}
        """


if __name__ == '__main__':
    unittest.main()
