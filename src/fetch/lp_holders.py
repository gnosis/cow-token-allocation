"""
Stores the result of querying GNO LP holder proportions and writes to file
`data/{network}-lp-holders.csv`
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

from src.constants import SNAPSHOT_BLOCK_NUMBER
from src.dune_analytics import DuneAnalytics
from src.files import NetworkFile, File, HolderFiles
from src.models import Account
from src.utils.data import index_by_account_with_multiplicity
from src.utils.data import write_to_csv


@dataclass
class LiquidityPosition(Account):
    """Amount of GNO held by `account` in `pool`"""
    pool: str
    gno_amount: int

    def __init__(self, account: str, pool: str, gno_amount: int):
        Account.__init__(self, account)
        self.pool = pool.lower()
        self.gno_amount = gno_amount


@dataclass
class LiquidityProportion(Account):
    """
    Proportion of GNO held by `account` in `pool`.
    Equivalent to the account's pool token balance over the circulating supply.
    """
    pool: str
    lp_proportion: Fraction

    def __init__(self, account: str, pool: str, proportion: Fraction):
        Account.__init__(self, account)
        self.pool = pool.lower()
        self.lp_proportion = proportion

    def to_liquidity_position(self, pool_gno: int) -> LiquidityPosition:
        """
        Converts Proportion into GNO amount by multiplying `lp_proportion` by `pool_gno`
        """
        # TODO: pass Pool { address, gno_balance } and assert(self.pool == pool.address)
        gno_fraction = self.lp_proportion * pool_gno
        return LiquidityPosition(
            account=self.account,
            pool=self.pool,
            gno_amount=gno_fraction.numerator // gno_fraction.denominator
        )

    @classmethod
    def load_from_file(cls, load_file: File) -> dict[str, list[LiquidityProportion]]:
        """Loads liquidity proportions from filename"""
        print(f"Loading LP Proportions from {load_file.name}")
        results = defaultdict(list)
        with open(load_file.filename(), 'r', encoding='utf-8') as file:
            dict_reader = csv.DictReader(file)
            for row in dict_reader:
                try:
                    numerator, denominator = row['lp_proportion'].split('/')
                    proportion = Fraction(int(numerator), int(denominator))
                except ValueError:
                    proportion = Fraction(int(row['lp_proportion']), 1)
                results[row['account']].append(
                    cls(
                        account=row['account'],
                        pool=row['pool'],
                        proportion=proportion,
                    )
                )
        print(f"Loaded {len(results)} lp account records")
        return results


@dataclass
class GenericPool:
    """
    Contains the structure and individual fetching logic for GenericPool dataclass.

    Generic pools are essentially every DeFi protocol for liquidity provision except
    UniswapV3. More concretely, any platform in which the pool itself is also an ERC20
    contract whose circulating supply corresponds directly to the contract's token balance.
    Note that in the case of Balancer V2, we can use the same structure except that the
    contract itself does not hold the corresponding token balances.
    They are concentrated in the Balancer Vault
    """
    address: str
    staking_contract: str
    name: str
    network: str

    @classmethod
    def from_dict(cls, obj: dict) -> GenericPool:
        """Constructor method from python dict"""
        return cls(
            address=obj['address'].lower(),
            staking_contract=obj['staking_contract'],
            name=obj['name'],
            network=obj['network']
        )

    def __str__(self):
        # pylint: disable=consider-using-f-string
        return "{} pool at {} with staking contract {}".format(
            self.name,
            self.address,
            self.staking_contract
        )

    @classmethod
    def load_from_file(cls, network, pool_file) -> list[GenericPool]:
        """Loads Generic Pools from file, filtering by network"""
        results = []
        with open(pool_file, 'r', encoding='utf-8') as pool_csv:
            reader = csv.DictReader(pool_csv)
            for data in reader:
                generic_pool = cls.from_dict(data)
                if generic_pool.network == network:
                    results.append(generic_pool)
        return results

    def fetch_lp_holders(
            self,
            dune: DuneAnalytics,
            block_number: str,
    ) -> list[LiquidityProportion]:
        """
        :param dune: open connection to dune analytics
        :param block_number: str representation of an integer ethereum block number
        :return: collection of `LiquidityProportion` on at `block_number`
        """
        data_set = dune.fetch(
            # uses generic lp holder query instead of the platform specific queries.
            # For quicker results, platform specific queries are much better.
            query_filepath="./queries/generic_lp_holders.sql",
            network=self.network,
            name=str(self),
            parameters=[
                {
                    "key": "BlockNumber",
                    "type": "number",
                    "value": block_number,
                },
                {
                    "key": "PoolAddress",
                    "type": "text",
                    "value": self.address
                },
                {
                    "key": "StakingContract",
                    "type": "text",
                    "value": self.staking_contract
                }
            ]
        )

        # lp_supply used to compute lp_proportion.
        lp_supply = sum(int(entry['lp_balance']) for entry in data_set)
        results = [
            LiquidityProportion(
                account=entry['account'],
                pool=self.address,
                proportion=Fraction(int(entry['lp_balance']), lp_supply)
            )
            for entry in data_set
        ]
        return results


def fetch_lp_holders(
        dune: DuneAnalytics,
        network: str,
        block_number: str,
        load_from: NetworkFile,
        pool_file: str = "./data/generic_pools.csv",
) -> dict[str, list[LiquidityProportion]]:
    """
    :param dune: open connection to dune analytics
    :param network: should be 'mainnet' or 'gchain'
    :param block_number: str representation of an integer ethereum block number
    :param pool_file: File path to list of `GenericPool`
    :param load_from: File path to load existing data from
    :return: collection of `LiquidityProportion` on `network` at `block_number`
    """
    network_file = load_from.filename(network)
    try:
        return LiquidityProportion.load_from_file(network_file)
    except FileNotFoundError:
        print(f"file at {network_file.name} not found. Fetching from Dune")

    pool_list = GenericPool.load_from_file(network, pool_file)
    results = []
    for pool in pool_list:
        results += pool.fetch_lp_holders(dune, block_number)

    results.sort(key=lambda t: (t.pool, -t.lp_proportion))
    write_to_csv(data_list=results, outfile=network_file)
    return index_by_account_with_multiplicity(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch GNO LP holders")
    parser.add_argument(
        "--pool_file",
        type=str,
        help="file path to pools.csv",
        default="./data/generic_pools.csv"
    )
    args = parser.parse_args()
    dune_connection = DuneAnalytics.new_from_environment()
    for chain in ['mainnet', 'gchain']:
        fetch_lp_holders(
            dune_connection,
            chain,
            SNAPSHOT_BLOCK_NUMBER[chain],
            pool_file=args.pool_file,
            load_from=HolderFiles().lp_holders
        )
