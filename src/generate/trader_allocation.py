"""Generates Trader Allocations (Primary and Consolation) from trader Data"""
from __future__ import annotations

from dataclasses import dataclass

from src.constants import USER_ALLOCATION, USER_OPTION_SUPPLY
from src.dune_analytics import DuneAnalytics
from src.fetch import trader_data
from src.files import TraderFiles
from src.models import IndexedAllocations, Allocation
from src.utils.data import dump_results_and_index_by_account


@dataclass
class TraderAllocations:
    """Data structure holding both types of Trader Allocation"""
    primary: IndexedAllocations
    consolation: IndexedAllocations
    user_options: IndexedAllocations


def assert_and_log(
        allocations: list[Allocation],
        name: str,
        supply: int,
):
    total = sum(p.amount for p in allocations)
    assert total <= supply

    unallocated = (supply - total) / pow(10, 18)
    print(f"{unallocated} unallocated {name}")


def derive_allocations(
        dune: DuneAnalytics,
        load_from: TraderFiles
) -> TraderAllocations:
    """
    Uses dune connection to fetch combined trader data and generates allocations
    """
    try:
        return TraderAllocations(
            primary=IndexedAllocations.load_from_file(load_from.primary_allocation),
            consolation=IndexedAllocations.load_from_file(
                load_from.consolation_allocation
            ),
            user_options=IndexedAllocations.load_from_file(load_from.user_options)
        )
    except FileNotFoundError:
        print(
            f"one of {load_from.primary_allocation} or "
            f"{load_from.consolation_allocation} not found: Fetching from dune..."
        )

    eligible_trader_data = trader_data.fetch_combined(dune, load_from)

    # Primary Trader Airdrop Allocations
    primary_allocations = [
        trader.to_primary_allocation(
            supply=USER_ALLOCATION['primary'],
            total_weight=eligible_trader_data.primary_tier_total
        )
        for trader in eligible_trader_data.primary_traders
    ]

    assert_and_log(
        allocations=primary_allocations,
        name="primary",
        supply=USER_ALLOCATION['primary']
    )

    # Consolations Trader Airdrop allocations
    num_consolation_prizes = len(eligible_trader_data.consolation_traders)
    consolation_allocations = [
        trader.to_consolation_allocation(
            supply=USER_ALLOCATION['consolation'],
            num_recipients=num_consolation_prizes,
        )
        for trader in eligible_trader_data.consolation_traders
    ]
    assert_and_log(
        allocations=consolation_allocations,
        name="consolation",
        supply=USER_ALLOCATION['consolation']
    )

    # User Option allocations
    user_options = [
        trader.to_user_option(
            supply=USER_OPTION_SUPPLY,
            total_weight=eligible_trader_data.user_option_tier_total
        )
        for trader in eligible_trader_data.primary_traders
    ]
    assert_and_log(
        allocations=user_options,
        name="User Options",
        supply=USER_OPTION_SUPPLY,
    )

    # Write results of both to separate files.
    primary_allocations.sort(key=lambda t: (-t.amount, t.account))
    indexed_primary = dump_results_and_index_by_account(
        results=primary_allocations,
        file=load_from.primary_allocation
    )
    # we only sort by account here because consolation amounts are all the same.
    consolation_allocations.sort(key=lambda a: a.account)
    indexed_consolation = dump_results_and_index_by_account(
        results=consolation_allocations,
        file=load_from.consolation_allocation
    )
    indexed_user_options = dump_results_and_index_by_account(
        results=sorted(user_options, key=lambda t: (-t.amount, t.account)),
        file=load_from.user_options
    )
    return TraderAllocations(
        primary=IndexedAllocations(indexed_primary),
        consolation=IndexedAllocations(indexed_consolation),
        user_options=IndexedAllocations(indexed_user_options),
    )


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    derive_allocations(dune_connection, TraderFiles())
