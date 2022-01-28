"""
A single script used to fetch results from all other fetchers and combine them
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass

import src.fetch.univ3_gno
from src.constants import SNAPSHOT_BLOCK_NUMBER, GNO_TOKEN, MIN_GNO, \
    GNO_HOLDER_ALLOCATION
from src.dune_analytics import DuneAnalytics
from src.fetch.balancer_gno import balancer_gno
from src.fetch.gno_holders import fetch_gno_holders, GnoHolder
from src.fetch.gno_stakers import fetch_gno_stakers
from src.fetch.lp_holders import fetch_lp_holders, LiquidityPosition, \
    LiquidityProportion, GenericPool
from src.fetch.univ3_gno import fetch_univ3_gno
from src.files import HolderFiles, NetworkFile, File
from src.models import Allocation, Account
from src.utils.data import write_to_csv, flatten_without_duplicates


@dataclass
class VerboseNetworkHolderData:
    """Combined account of total GNO held across all relevant platforms"""
    account: str
    network: str
    gno_held: int
    lp_gno: int
    univ3_gno: int
    staked_gno: int
    total_gno: int

    # pylint: disable=too-many-arguments
    def __init__(
            self,
            account: str,
            network: str,
            gno_held: int | str,
            lp_gno: int | str,
            univ3_gno: int | str = 0,
            staked_gno: int | str = 0
    ):
        if network == 'mainnet' and int(staked_gno) != 0:
            print(staked_gno)
            raise ValueError(f"{network} does not involve staking.")
        if network == 'gchain' and int(univ3_gno) != 0:
            raise ValueError(f"{network} does not involve UniV3.")
        self.account = account.lower()
        self.gno_held = int(gno_held)
        self.lp_gno = int(lp_gno)
        self.univ3_gno = int(univ3_gno)
        self.staked_gno = int(staked_gno)
        self.network = network
        self.total_gno = self._compute_total()

    def _compute_total(self) -> int:
        """Makes `total` into a computed field."""
        return self.gno_held + self.lp_gno + self.univ3_gno + self.staked_gno

    @classmethod
    def load_from(cls, load_from: File) -> dict[str, VerboseNetworkHolderData]:
        print(f"Loading Network Holder Data from {load_from.name}")
        with open(load_from.filename(), 'r', encoding='utf-8') as holder_file:
            reader = csv.DictReader(holder_file)
            results = {
                row['account']: VerboseNetworkHolderData(
                    account=row['account'],
                    gno_held=row['gno_held'],
                    lp_gno=row['lp_gno'],
                    univ3_gno=row['univ3_gno'],
                    staked_gno=row['staked_gno'],
                    network=row['network'],
                )
                for row in reader
            }
        print(f"Loaded {len(results)} {load_from.name} records")
        return results


def transform_proportions(
        liquidity_proportions: dict[str, list[LiquidityProportion]],
        gno_holders: dict[str, GnoHolder]
) -> defaultdict[str, list[LiquidityPosition]]:
    """
    Transforms LiquidityProportions into LiquidityPosition based on `gno_holders`
    """
    print("Transforming Proportions into Positions")
    lp_holders = defaultdict(list)
    for account, proportions in liquidity_proportions.items():
        for proportion in proportions:
            pool_gno = gno_holders[proportion.pool].amount
            lp_holders[account].append(proportion.to_liquidity_position(pool_gno))
    return lp_holders


@dataclass
class NetworkGnoHoldersBlob:
    """Data class holding all the pieces to build master GNO Holders list"""
    network: str
    gno_holders: dict[str, GnoHolder]
    lp_proportions: dict[str, list[LiquidityProportion]]
    stakers: dict[str, GnoHolder]
    uni_holders: dict[str, GnoHolder]
    lp_holders: dict[str, list[LiquidityPosition]]

    # pylint: disable=too-many-arguments
    def __init__(
            self,
            dune: DuneAnalytics,
            network: str,
            block_number: str,
            load_from: HolderFiles
    ):
        self.network = network
        self.lp_proportions = fetch_lp_holders(
            dune,
            self.network,
            block_number,
            load_from=load_from.lp_holders
        )
        self.gno_holders = fetch_gno_holders(
            dune,
            self.network,
            block_number,
            load_from.gno_holders
        )
        # Initialize empty network specific fields
        self.stakers, self.uni_holders = {}, {}
        if self.network == 'gchain':
            self.stakers = fetch_gno_stakers(
                dune,
                block_number,
                load_from.stakers
            )

        if self.network == 'mainnet':
            # Split the Balancer vault balances:
            gno_in_balancer_pools = balancer_gno(
                dune,
                block_number,
                load_from.balancer_pools
            )
            # We remove the vault GNO holdings from the holders list and replace it
            # with the partitioned individual pool balances
            vault_holding = self.gno_holders.pop(
                '0xba12222222228d8ba445958a75a0704d566bf2c8')
            # The vault should contain exactly the same amount of GNO
            # as the partition made by fetching pool balances.
            balancer_pool_total = sum(p.gno_balance for p in gno_in_balancer_pools)
            assert vault_holding.amount == balancer_pool_total

            # update GNO holders with balancer pool balances
            for balancer_pool in gno_in_balancer_pools:
                self.gno_holders[balancer_pool.pool_address] = GnoHolder(
                    account=balancer_pool.pool_address,
                    amount=balancer_pool.gno_balance
                )

            self.uni_holders = fetch_univ3_gno(
                # Dune expects string, but uni expects int
                block_number=int(block_number),
                token=GNO_TOKEN['mainnet'],
                load_from=load_from.univ3_holders
            )

        # THIS MUST HAPPEN LAST (after gno_holders is finalized)
        self.lp_holders = transform_proportions(self.lp_proportions, self.gno_holders)

    def combine(self, load_from: NetworkFile) -> dict[str, VerboseNetworkHolderData]:
        """
        Fetches and combines GNO holdings, staked GNO and Liquidity Positions
        for `network` at `block_number`.
        """
        try:
            return VerboseNetworkHolderData.load_from(load_from.filename(self.network))
        except FileNotFoundError:
            print(f"file at {load_from.name} not found. Fetching from Dune...")

        account_set = flatten_without_duplicates([
            self.gno_holders.keys(),
            self.lp_holders.keys(),
            self.stakers.keys(),
            self.uni_holders.keys(),
        ])

        combined_data = {}
        for account in account_set:
            lp_positions = self.lp_holders.get(account, [])

            combined_data[account] = VerboseNetworkHolderData(
                account=account,
                network=self.network,
                gno_held=self.gno_holders.get(account, GnoHolder.default()).amount,
                lp_gno=sum(
                    position.gno_amount for position in lp_positions
                ),
                staked_gno=self.stakers.get(account, GnoHolder.default()).amount,
                univ3_gno=self.uni_holders.get(account, GnoHolder.default()).amount,
            )

        print(f"successfully combined {self.network} holder data")
        results = sorted(
            list(combined_data.values()), key=lambda t: (-t.total_gno, t.account)
        )
        write_to_csv(data_list=results, outfile=load_from.filename(self.network))
        return combined_data


@dataclass
class CombinedGnoHolder:
    """
    Combined account of all gno holders over both networks.
    """
    account: str
    mainnet_gno: int
    gchain_gno: int
    total_gno: int

    def __init__(self, account, mainnet_gno: int, gchain_gno: int):
        self.account = account.lower()
        self.mainnet_gno = int(mainnet_gno)
        self.gchain_gno = int(gchain_gno)
        self.total_gno = self.compute_total()

    def compute_total(self) -> int:
        """Makes `total` into a computed field."""
        return self.mainnet_gno + self.gchain_gno

    def to_allocation(self, supply: int) -> Allocation:
        """Transforms combined holder to allocation as proportion of supply"""
        return Allocation(
            account=self.account,
            amount=(GNO_HOLDER_ALLOCATION * self.total_gno) // supply,
        )

    @classmethod
    def load_from(cls, load_from: File) -> list[CombinedGnoHolder]:
        print(f"Loading Combined Holder Data from {load_from.name}")
        with open(load_from.filename(), 'r', encoding='utf-8') as holder_file:
            reader = csv.DictReader(holder_file)
            results = [
                CombinedGnoHolder(
                    account=row['account'],
                    mainnet_gno=row['mainnet_gno'],
                    gchain_gno=row['gchain_gno']
                ) for row in reader
            ]
        print(f"Loaded {len(results)} {load_from.name} records")
        return results


@dataclass
class CombinedGnoHolderBlob:
    """Holds VerboseHolderData for both networks (indexed by account)"""
    mainnet: dict[str, VerboseNetworkHolderData]
    gchain: dict[str, VerboseNetworkHolderData]

    def account_set(self) -> set[str]:
        """Returns complete set of accounts on both networks"""
        return self.mainnet.keys() | self.gchain.keys()

    def build_master_holder_data(
            self,
            min_gno: int,
            excluded_accounts: set[str],
            load_from: File,
    ) -> list[CombinedGnoHolder]:
        """
        Fetches combined GNO holder data over both networks (mainnet and gchain),
        builds a combined summary, writes to file and returns the summary.
        :param min_gno: amounts to exclude from final output.
        :param excluded_accounts: list of accounts to be removed after processing
        :param load_from: File path to existing data set
        :return: combined summary of all GNO holders
        """
        try:
            return CombinedGnoHolder.load_from(load_from)
        except FileNotFoundError:
            print(f"file at {load_from.name} not found. Fetching from Dune...")

        results: list[CombinedGnoHolder] = []
        for account in self.account_set():
            mainnet_holdings = self.mainnet.get(account, None)
            gchain_holdings = self.gchain.get(account, None)
            holder = CombinedGnoHolder(
                account=account,
                mainnet_gno=mainnet_holdings.total_gno if mainnet_holdings else 0,
                gchain_gno=gchain_holdings.total_gno if gchain_holdings else 0,
            )
            # Filtering by min gno and excluded accounts.
            if holder.total_gno >= min_gno and holder.account not in excluded_accounts:
                results.append(holder)

        # Sort by total GNO descending.
        results.sort(key=lambda t: (-t.total_gno, t.account))
        print("successfully built master holder list")
        write_to_csv(data_list=results, outfile=load_from)
        return results


def build_holder_blob(
        dune: DuneAnalytics,
        load_from: HolderFiles,
) -> CombinedGnoHolderBlob:
    """
    Builds combined HoldersBlob for both networks.
    :param dune: open connection to dune
    :param load_from: existing in case you don't want to fetch from scratch
    :return: HoldersBlob
    """
    holder_dict = {}
    for network in ['mainnet', 'gchain']:
        network_blob = NetworkGnoHoldersBlob(
            dune=dune,
            network=network,
            block_number=SNAPSHOT_BLOCK_NUMBER[network],
            load_from=load_from
        )
        print(f"Building Combined Holder Files for {network}")
        combined_result = network_blob.combine(load_from.network_master)

        holder_dict[network] = combined_result
    return CombinedGnoHolderBlob(
        mainnet=holder_dict['mainnet'],
        gchain=holder_dict['gchain']
    )


def generate_combined_holders(
        dune: DuneAnalytics,
        load_from: HolderFiles,
) -> list[CombinedGnoHolder]:
    """
    With dune connection, either fetches or parses holder data and builds
    a complete account of gno holder data
    """
    excluded_accounts = load_excluded_accounts()
    holder_blob = build_holder_blob(dune, load_from)
    return holder_blob.build_master_holder_data(
        min_gno=MIN_GNO,
        excluded_accounts=excluded_accounts,
        load_from=load_from.combined,
    )


def load_excluded_accounts() -> set[str]:
    excluded = set()

    excluded |= File(name='excluded_accounts.csv', path='./data/').get_accounts_from()

    # exclude Binance Accounts
    excluded |= File(name='binance_accounts.csv', path='./data/').get_accounts_from()

    # exclude univ3 pools
    excluded |= set(
        p.address
        for p in src.fetch.univ3_gno.fetch_pools(
            block_number=int(SNAPSHOT_BLOCK_NUMBER['mainnet']),
            token=GNO_TOKEN
        )
    )
    # exclude generic mainnet pools
    excluded |= set(
        p.address
        for p in GenericPool.load_from_file(
            network='mainnet',
            pool_file='./data/generic_pools.csv'
        )
    )
    # exclude generic gchain pools
    excluded |= set(
        p.address
        for p in GenericPool.load_from_file(
            network='gchain',
            pool_file='./data/generic_pools.csv'
        )
    )

    return {Account(a).account for a in excluded}


if __name__ == '__main__':
    dune_connection = DuneAnalytics.new_from_environment()

    generate_combined_holders(
        dune=dune_connection,
        load_from=HolderFiles()
    )
