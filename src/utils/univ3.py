"""
Code and data structures used to query the UniswapV3 subgraph at
https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import requests

from src.models import GnoHolder

# Constants taken from:
# https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/utils/tickMath.ts#L19-L26
Q32 = 2 ** 32
Q96 = 2 ** 96
MAX_U256 = 2 ** 256 - 1
MIN_TICK = -887272
MAX_TICK = -1 * MIN_TICK


def pool_query(block_number: int, token: str) -> str:
    """
    Constructs and returns Graph query for all pools involving `token` at `block_number`
    Compatible with UniswapV3 subgraph:
    https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3
    """
    return f"""
    {{
      pools0: pools(
        block: {{ number: {block_number} }}
        where: {{ token0: \"{token}\" }}
      ) {{
        id
        totalValueLockedToken0
        tick
        sqrtPrice
        liquidity
      }}
      pools1: pools(
        block: {{ number: {block_number} }}
        where: {{ token1: \"{token}\" }}
      ) {{
        id
        totalValueLockedToken1
        tick
        sqrtPrice
        liquidity
      }}
    }}
    """


def position_query(block_number: int, pool_list: list[str]) -> str:
    """
    Constructs and returns Graph query for all positions in pools
    involving `token` at `block_number`. Compatible with UniswapV3 subgraph:
    https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3
    """
    return f"""
    {{
      positions(
        block: {{ number: {block_number} }}
        where: {{
          pool_in: {json.dumps(pool_list)}
          liquidity_gt: "0"
        }}
      ) {{
        owner
        liquidity
        tickLower {{ tickIdx }}
        tickUpper {{ tickIdx }}
        pool {{ id }}
      }}
    }}
    """


@dataclass
class Pool:
    """
    Contains all relevant UniswapV3 pool information
    needed to extract Token amount from each position.
    """
    address: str
    liquidity: int
    sqrt_price: int
    tick: Optional[int]
    queried_token_index: int


@dataclass
class Position:
    """
    All relevant UniswapV3 Position information
    needed to extract Token amount.
    """
    account: str
    liquidity: int
    tick_lower: int
    tick_upper: int
    pool: Pool
    token: str

    @staticmethod
    def reduce_to_gno_holder(position_list: list[Position]) -> GnoHolder:
        """Transforms list[Position] -> GnoHolder"""
        account_set = set(p.account for p in position_list)
        assert len(account_set) == 1
        return GnoHolder(
            account=account_set.pop(),
            amount=sum(p.gno_amount() for p in position_list)
        )

    def gno_amount(self):
        """
        Returns amount of gno corresponding to Position
        uses amount0 formula when token is token0 otherwise amount1
        """
        token_index = self.pool.queried_token_index
        if token_index == 0:
            return self.get_amount_0()
        if token_index == 1:
            return self.get_amount_1()
        raise IndexError(f"Uniswap Pools do not have token index {token_index}")

    def get_amount_0(self) -> int:
        """
        Function transcribed from UniswapV3 SDK:
        https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/entities/position.ts#L68-L95
        :return: amount of token0
        """
        if self.pool.tick < self.tick_lower:
            return get_amount0_delta(
                get_sqrt_ratio_at_tick(self.tick_lower),
                get_sqrt_ratio_at_tick(self.tick_upper),
                self.liquidity,
                False
            )

        if self.pool.tick < self.tick_upper:
            return get_amount0_delta(
                self.pool.sqrt_price,
                get_sqrt_ratio_at_tick(self.tick_upper),
                self.liquidity,
                False
            )

        return 0

    def get_amount_1(self) -> int:
        """
        Transcribed from UniswapV3 SDK
        https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/entities/position.ts#L100-L127
        :return: amount of token 1
        """
        if self.pool.tick < self.tick_lower:
            return 0

        if self.pool.tick < self.tick_upper:
            return get_amount1_delta(
                get_sqrt_ratio_at_tick(self.tick_lower),
                self.pool.sqrt_price,
                self.liquidity,
                False
            )

        return get_amount1_delta(
            get_sqrt_ratio_at_tick(self.tick_lower),
            get_sqrt_ratio_at_tick(self.tick_upper),
            self.liquidity,
            False
        )


def execute_query(query: str):
    """
    Executes UniswapV3 subgraph queries.
    :param query: Graph QL Query
    :return: results of the query.
    """
    graph_url = 'https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3'
    response = requests.post(graph_url, json={'query': query, 'variables': None})
    return response.json()


def get_amount0_delta(
        sqrt_ratio_ax96: int,
        sqrt_ratio_bx96: int,
        liquidity: int,
        round_up: bool
) -> int:
    """
    Transcribed from UniswapV3 SDK
    https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/utils/sqrtPriceMath.ts#L25-L36
    """
    if sqrt_ratio_ax96 > sqrt_ratio_bx96:
        sqrt_ratio_ax96, sqrt_ratio_bx96 = sqrt_ratio_bx96, sqrt_ratio_ax96

    numerator1 = liquidity << 96
    numerator2 = sqrt_ratio_bx96 - sqrt_ratio_ax96

    if round_up:
        return mul_div_round_up(numerator1, numerator2, sqrt_ratio_bx96)
    return ((numerator1 * numerator2) // sqrt_ratio_bx96) // sqrt_ratio_ax96


def get_amount1_delta(
        sqrt_ratio_ax96: int,
        sqrt_ratio_bx96: int,
        liquidity: int,
        round_up: bool
) -> int:
    """
    Transcribed from UniswapV3 SDK
    https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/utils/sqrtPriceMath.ts#L38-L46
    """
    if sqrt_ratio_ax96 > sqrt_ratio_bx96:
        sqrt_ratio_ax96, sqrt_ratio_bx96 = sqrt_ratio_bx96, sqrt_ratio_ax96

    if round_up:
        return mul_div_round_up(liquidity, sqrt_ratio_bx96 - sqrt_ratio_ax96, Q96)
    return (liquidity * (sqrt_ratio_bx96 - sqrt_ratio_ax96)) // Q96


# pylint: disable=too-many-branches
def get_sqrt_ratio_at_tick(tick: int) -> int:
    """
    Function transcribed from UniswapV3 SDK:
    https://github.com/Uniswap/v3-sdk/blob/c807b04812cecca2b1e32c1c26b508296764a8bc/src/utils/tickMath.ts#L37-L75
    :param tick: the tick for which to compute the sqrt ratio
    :return: square root ratio at tick (as defined by uniswap v3)
    """
    abs_tick = abs(tick)
    ratio = 0x100000000000000000000000000000000
    if (abs_tick & 0x1) != 0:
        ratio = 0xfffcb933bd6fad37aa2d162d1a594001
    if (abs_tick & 0x2) != 0:
        ratio = mul_shift(ratio, 0xfff97272373d413259a46990580e213a)
    if (abs_tick & 0x4) != 0:
        ratio = mul_shift(ratio, 0xfff2e50f5f656932ef12357cf3c7fdcc)
    if (abs_tick & 0x8) != 0:
        ratio = mul_shift(ratio, 0xffe5caca7e10e4e61c3624eaa0941cd0)
    if (abs_tick & 0x10) != 0:
        ratio = mul_shift(ratio, 0xffcb9843d60f6159c9db58835c926644)
    if (abs_tick & 0x20) != 0:
        ratio = mul_shift(ratio, 0xff973b41fa98c081472e6896dfb254c0)
    if (abs_tick & 0x40) != 0:
        ratio = mul_shift(ratio, 0xff2ea16466c96a3843ec78b326b52861)
    if (abs_tick & 0x80) != 0:
        ratio = mul_shift(ratio, 0xfe5dee046a99a2a811c461f1969c3053)
    if (abs_tick & 0x100) != 0:
        ratio = mul_shift(ratio, 0xfcbe86c7900a88aedcffc83b479aa3a4)
    if (abs_tick & 0x200) != 0:
        ratio = mul_shift(ratio, 0xf987a7253ac413176f2b074cf7815e54)
    if (abs_tick & 0x400) != 0:
        ratio = mul_shift(ratio, 0xf3392b0822b70005940c7a398e4b70f3)
    if (abs_tick & 0x800) != 0:
        ratio = mul_shift(ratio, 0xe7159475a2c29b7443b29c7fa6e889d9)
    if (abs_tick & 0x1000) != 0:
        ratio = mul_shift(ratio, 0xd097f3bdfd2022b8845ad8f792aa5825)
    if (abs_tick & 0x2000) != 0:
        ratio = mul_shift(ratio, 0xa9f746462d870fdf8a65dc1f90e061e5)
    if (abs_tick & 0x4000) != 0:
        ratio = mul_shift(ratio, 0x70d869a156d2a1b890bb3df62baf32f7)
    if (abs_tick & 0x8000) != 0:
        ratio = mul_shift(ratio, 0x31be135f97d08fd981231505542fcfa6)
    if (abs_tick & 0x10000) != 0:
        ratio = mul_shift(ratio, 0x9aa508b5b7a84e1c677de54f3e99bc9)
    if (abs_tick & 0x20000) != 0:
        ratio = mul_shift(ratio, 0x5d6af8dedb81196699c329225ee604)
    if (abs_tick & 0x40000) != 0:
        ratio = mul_shift(ratio, 0x2216e584f5fa1ea926041bedfe98)
    if (abs_tick & 0x80000) != 0:
        ratio = mul_shift(ratio, 0x48a170391f7dc42444e8fa2)

    if tick > 0:
        ratio = MAX_U256 // ratio

    if ratio % Q32 > 0:
        return (ratio // Q32) + 1

    return ratio // Q32


def mul_shift(val: int, mul_by: int) -> int:
    """Multiplication followed by bit shift"""
    return (val * mul_by) >> 128


def mul_div_round_up(num1: int, num2: int, denominator: int) -> int:
    """Multiply, then divide and round up"""
    product = num1 * num2
    result = (product + denominator - 1) // denominator
    return result
