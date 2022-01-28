"""
Fetching the amount of `Token` held by each liquidity provider
for Uniswap V3 pools at a specific block
"""
from collections import defaultdict

from src.constants import GNO_TOKEN, SNAPSHOT_BLOCK_NUMBER
from src.files import HolderFiles
from src.models import GnoHolder
from src.utils.univ3 import execute_query, Position, Pool, pool_query, \
    position_query
from src.utils.data import write_to_csv, File


def fetch_pools(block_number: int, token: str) -> list[Pool]:
    """
    Fetches all UniV3 pools involving `token` at `block_number`
    :return: a list of Pools
    """
    pools = execute_query(pool_query(block_number, token))['data']
    results = []
    for data in pools['pools0']:
        results.append(
            Pool(
                address=data['id'],
                liquidity=int(data['liquidity']),
                sqrt_price=int(data['sqrtPrice']),
                tick=int(data['tick']),
                queried_token_index=0
            )
        )
    for data in pools['pools1']:
        results.append(
            Pool(
                address=data['id'],
                liquidity=int(data['liquidity']),
                sqrt_price=int(data['sqrtPrice']),
                tick=int(data['tick']),
                queried_token_index=1
            )
        )
    return results


def fetch_univ3_gno(
        block_number: int,
        token: str,  # For our purposes we only ever use GNO.
        load_from: File,
) -> dict[str, GnoHolder]:
    """
    Fetches all open liquidity positions for all UniV3 pools
    involving `token` at `block_number`. Note that out of range
    positions with zero balance are not returned
    :param block_number: block at which to get balances
    :param token: address string of token to get balances for
    :param load_from: location of existing file
    :return: all relevant positions indexed by account
    """
    try:
        return GnoHolder.load_from_file(name="UniV3 Gno Holders", load_file=load_from)
    except FileNotFoundError:
        print(f"file at {load_from.name} not found. Fetching from The Graph")

    pool_list = fetch_pools(block_number, token)
    indexed_pools = {
        pool.address: pool
        for pool in pool_list
    }

    position_list = execute_query(
        position_query(
            block_number,
            list(indexed_pools.keys()))
    )['data']['positions']

    results = defaultdict(list)
    for gql_position in position_list:
        pool_id = gql_position['pool']['id']
        position = Position(
            liquidity=int(gql_position['liquidity']),
            account=gql_position['owner'],
            tick_lower=int(gql_position['tickLower']['tickIdx']),
            tick_upper=int(gql_position['tickUpper']['tickIdx']),
            pool=indexed_pools[pool_id],
            token=token
        )
        results[position.account].append(position)

    return_dict = {
        account: Position.reduce_to_gno_holder(results[account])
        for account in results
    }
    gno_holders = list(return_dict.values())
    gno_holders.sort(key=lambda h: h.amount, reverse=True)

    write_to_csv(
        data_list=gno_holders,
        outfile=load_from
    )
    return return_dict


if __name__ == '__main__':
    positions = fetch_univ3_gno(
        block_number=SNAPSHOT_BLOCK_NUMBER['mainnet'],
        token=GNO_TOKEN['mainnet'],
        load_from=HolderFiles().univ3_holders
    )

    for holder in positions.values():
        print(f"Account {holder.account} holds {holder.amount} GNO in UniV3 positions")
