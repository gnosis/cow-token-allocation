"""
Stores the result of querying trader data on each network into respectively named files
`data/{network}-lp-holders.csv`
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from src.constants import VOLUME_TIERS, TRADING_TIER_FACTORS, SNAPSHOT_BLOCK_NUMBER, \
    USER_OPTION_TIER_FACTORS
from src.dune_analytics import DuneAnalytics
from src.fetch.combined_holders import load_excluded_accounts
from src.files import NetworkFile, TraderFiles, File
from src.models import Account, Allocation
from src.utils.data import dump_results_and_index_by_account, write_to_csv


@dataclass
class DuneTradeParameters:
    """Parameters passed into the dune query at ./queries/generic_trader_data.sql"""
    # These all have to be string because of how dune accepts parameters
    primary_min_trades: int
    consolation_min_trades: int
    min_volume: float
    days_between: int
    # This is a string because it is passed into the SQL query
    stable_factor: str

    # pylint: disable=too-many-arguments
    def __init__(self, primary_trades, consolation_trades, volume, days, stable_factor):
        self.primary_min_trades = int(primary_trades)
        self.consolation_min_trades = int(consolation_trades)
        self.min_volume = float(volume)
        self.days_between = int(days)
        self.stable_factor = str(stable_factor)


# These default values are the finalized values to be used.
TRADER_PARAMETERS = DuneTradeParameters(
    primary_trades=os.environ.get('PRIMARY_MIN_TRADES', 3),
    consolation_trades=os.environ.get('CONSOLATION_MIN_TRADES', 5),
    volume=os.environ.get('TRADER_MIN_VOLUME', 1000),
    days=os.environ.get('TRADER_MIN_DAYS', 14),
    stable_factor=os.environ.get('STABLE_FACTOR', 0.1),
)


# pylint: disable=too-few-public-methods
class AllocationTiers:
    """
    Class containing allocation tier info for dataset. Used mostly for
    printing and to avoid re-evaluation of total_weight every time its needed.
    """

    def __init__(self, tier_counts: dict[int]):
        self.tier_counts = tier_counts
        self.primary_total_weight = sum(
            factor * tier_counts[tier]
            for tier, factor in TRADING_TIER_FACTORS.items()
        )
        self.user_option_weight = sum(
            factor * tier_counts[tier]
            for tier, factor in USER_OPTION_TIER_FACTORS.items()
        )

    def __str__(self):
        results = ""
        for i, value in enumerate(VOLUME_TIERS):
            count = self.tier_counts[i]
            if i < len(VOLUME_TIERS) - 1:
                start = value // 10 ** 3
                end = VOLUME_TIERS[i + 1] // 10 ** 3
                results += f"Tier {i} (between {start}K and {end}K): {count}\n"
            else:
                results += f"Tier {i} (above {value // 10 ** 6}M): {count}\n"

        results += "----------------------------------\n"
        results += "\n".join([
            "Total Weights:",
            f"   Primary Trader: {self.user_option_weight}",
            f"   User Option: {self.primary_total_weight}",
        ])
        return results


@dataclass
class CowSwapTrader(Account):
    """Trader Data associated with `account`"""
    eligible_volume: int
    num_trades: int
    # Number of days between trader's first and last trade
    first_trade: date
    last_trade: date
    allocation_tier: int = -1

    # pylint: disable=too-many-arguments
    def __init__(
            self,
            account: str,
            eligible_volume: int,
            num_trades: int,
            first_trade: date,
            last_trade: date,
    ):
        Account.__init__(self, account)
        self.eligible_volume = eligible_volume
        self.num_trades = int(num_trades)
        self.first_trade = first_trade
        self.last_trade = last_trade
        self.allocation_tier = self._compute_allocation_tier()

    @classmethod
    def load_from_file(
            cls,
            load_file: File,
    ) -> dict[str, CowSwapTrader]:
        """Loads liquidity proportions from filename"""
        print(f"Loading Trader Data from {load_file.name}")
        results = {}
        with open(load_file.filename(), 'r', encoding='utf-8') as file:
            dict_reader = csv.DictReader(file)
            for row in dict_reader:
                account = row['account']
                results[account] = cls(
                    account=account,
                    eligible_volume=int(row['eligible_volume']),
                    num_trades=int(row['num_trades']),
                    first_trade=datetime.strptime(row['first_trade'],
                                                  "%Y-%m-%d").date(),
                    last_trade=datetime.strptime(row['last_trade'], "%Y-%m-%d").date(),
                )
        print(f"Loaded {len(results)} trader records")
        return results

    def _compute_allocation_tier(self) -> int:
        if self.eligible_volume < VOLUME_TIERS[0]:
            return -1
        for i in range(len(VOLUME_TIERS) - 1):
            if VOLUME_TIERS[i] <= self.eligible_volume < VOLUME_TIERS[i + 1]:
                return i
        return len(VOLUME_TIERS) - 1

    def days_between_first_and_last(self):
        """Number of days between first and last trade"""
        return (self.last_trade - self.first_trade).days

    def merge(self, other: CowSwapTrader) -> CowSwapTrader:
        """
        Combines the volume, num trades and updates the first and last trade
        between two entries for the same account.
        Used to merge gchain and mainnet trader data.
        """
        assert self.account == other.account, "Can't merge different traders!"

        return CowSwapTrader(
            account=self.account,
            eligible_volume=self.eligible_volume + other.eligible_volume,
            num_trades=self.num_trades + other.num_trades,
            first_trade=min(self.first_trade, other.first_trade),
            last_trade=max(self.last_trade, other.last_trade)
        )

    def is_eligible(self) -> bool:
        """
        :return: True if record meets eligibility criteria defined by TRADER_PARAMETERS.
        """
        eligibility_criteria = [
            self.eligible_volume >= TRADER_PARAMETERS.min_volume,
            self.num_trades >= TRADER_PARAMETERS.primary_min_trades,
            self.days_between_first_and_last() >= TRADER_PARAMETERS.days_between,
        ]
        if all(eligibility_criteria) and self.allocation_tier not in TRADING_TIER_FACTORS:
            raise ValueError(
                "Trader meets eligibility criteria, but has invalid allocation tier!"
            )
        return all(eligibility_criteria)

    def to_user_option(
            self,
            total_weight: int,
            supply: int
    ) -> Allocation:
        """
        Converts Trader to User Option based on their allocation factor
        """
        assert self.is_eligible(), f"{self} not eligible for primary allocation"
        # KeyError not possible here because above assertion ensures key exists.
        allocation_factor = USER_OPTION_TIER_FACTORS[self.allocation_tier]
        return Allocation(
            account=self.account,
            amount=(supply * allocation_factor) // total_weight,
        )

    def to_primary_allocation(
            self,
            total_weight: int,
            supply: int
    ) -> Allocation:
        """
        Converts Trader to Primary Allocation based on their allocation factor
        """
        assert self.is_eligible(), f"{self} not eligible for primary allocation"
        # KeyError not possible here because above assertion ensures key exists.
        allocation_factor = TRADING_TIER_FACTORS[self.allocation_tier]
        return Allocation(
            account=self.account,
            amount=(supply * allocation_factor) // total_weight,
        )

    def to_consolation_allocation(
            self, num_recipients: int,
            supply: int
    ) -> Allocation:
        """
        Converts Trader to Consolation Allocation number of recipients and total supply
        """
        assert not self.is_eligible(), f"{self} not eligible for consolation allocation"
        return Allocation(
            account=self.account,
            amount=supply // num_recipients,
        )


def fetch_trader_data(
        dune: DuneAnalytics,
        network: str,
        block_number: str,
        load_from: NetworkFile,
) -> dict[str, CowSwapTrader]:
    """
    :param dune: open connection to dune analytics
    :param network: should be 'mainnet' or 'gchain'
    :param block_number: str representation of an integer ethereum block number
    :param load_from: File to load from (todo - load from).
    :return: collection of `CowSwapTrader` on `network` at `block_number`
    """
    network_file = load_from.filename(network)
    try:
        return CowSwapTrader.load_from_file(network_file)
    except FileNotFoundError:
        print(f"file at {network_file.name} not found. Fetching from Dune")

    # Need to implement load from.
    data_set = dune.fetch(
        query_filepath="./queries/generic_trader_data.sql",
        network=network,
        name="trader data",
        parameters=[
            {
                "key": "BlockNumber",
                "type": "number",
                "value": block_number,
            },
            {
                "key": "StableFactor",
                "type": "number",
                "value": TRADER_PARAMETERS.stable_factor,
            },
        ]
    )
    results = sorted([
        CowSwapTrader(
            account=entry['trader'],
            eligible_volume=int(entry['eligible_volume']),
            num_trades=int(entry['num_trades']),
            first_trade=datetime.strptime(entry['first_trade'], "%Y-%m-%d").date(),
            last_trade=datetime.strptime(entry['last_trade'], "%Y-%m-%d").date(),
        ) for entry in data_set
    ], key=lambda t: (-t.eligible_volume, t.account))
    return dump_results_and_index_by_account(
        file=load_from.filename(network),
        results=results
    )


@dataclass
class EligibleTraderData:
    """Blob of Trader Data sufficient to generate Allocations"""
    primary_tier_total: int
    user_option_tier_total: int
    primary_traders: list[CowSwapTrader]
    consolation_traders: list[CowSwapTrader]


def fetch_combined(
        dune: DuneAnalytics,
        load_from: TraderFiles,
) -> EligibleTraderData:
    """Fetches trader data for both networks and combines them."""
    network_results = {}
    account_set = set()
    for chain in ['mainnet', 'gchain']:
        network_results[chain] = fetch_trader_data(
            dune=dune,
            network=chain,
            block_number=SNAPSHOT_BLOCK_NUMBER[chain],
            load_from=load_from.traders
        )
        account_set |= set(network_results[chain].keys())

    primary, consolation, tier_counts = [], [], defaultdict(int)
    excluded_accounts = load_excluded_accounts()
    for account in account_set - excluded_accounts:
        mainnet_entry = network_results['mainnet'].pop(account, None)
        gchain_entry = network_results['gchain'].pop(account, None)

        if mainnet_entry is not None and gchain_entry is not None:
            user_entry = mainnet_entry.merge(gchain_entry)
        elif mainnet_entry is not None:
            user_entry = mainnet_entry
        elif gchain_entry is not None:
            user_entry = gchain_entry
        else:
            # Should never happen (account set is the union of the two dicts)
            raise KeyError(f"Account {account} missing from both networks!")

        if user_entry.is_eligible():
            tier_counts[user_entry.allocation_tier] += 1
            primary.append(user_entry)
        else:
            consolation_criteria = [
                user_entry.eligible_volume >= TRADER_PARAMETERS.min_volume,
                user_entry.num_trades >= TRADER_PARAMETERS.consolation_min_trades
            ]
            if any(consolation_criteria):
                consolation.append(user_entry)

    allocation_tiers = AllocationTiers(tier_counts)
    print(f"Tier Count for this dataset\n{allocation_tiers}")
    write_to_csv(
        data_list=sorted(primary, key=lambda t: (-t.eligible_volume, t.account)),
        outfile=load_from.primary_trader
    )
    write_to_csv(
        data_list=sorted(consolation, key=lambda t: (-t.eligible_volume, t.account)),
        outfile=load_from.consolation_trader
    )
    return EligibleTraderData(
        primary_tier_total=allocation_tiers.primary_total_weight,
        user_option_tier_total=allocation_tiers.user_option_weight,
        primary_traders=primary,
        consolation_traders=consolation
    )


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    fetch_combined(dune_connection, TraderFiles())
