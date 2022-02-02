"""Fetch relevant data and reduce to a token allocation output file"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass

from src.constants import USER_ALLOCATION, SNAPSHOT_BLOCK_NUMBER
from src.dune_analytics import DuneAnalytics
from src.fetch.alpha_traders import fetch_alpha_traders
from src.fetch.combined_holders import load_excluded_accounts
from src.files import AllocationFiles, NetworkFile
from src.models import Account, Allocation, IndexedAllocations
from src.utils.data import dump_results_and_index_by_account, File

ALPHA_TRADER_FACTORS = {
    'mainnet': 8,
    'gchain': 2
}


@dataclass
class TokenAllocation:
    """Simple struct representing the data contains in the poap categories"""
    token_id: int
    factor: int
    event: str

    def allocation_amount_wei(self, total_weight: int) -> int:
        """generates allocation based on supply and total weight"""
        return (self.factor * USER_ALLOCATION['POAP']) // total_weight

    def __str__(self):
        return f"  event:  {self.event}\n" \
               f"  token:  {self.token_id}\n" \
               f"  weight: {self.factor}"


ALPHA_TRADER_ALLOCATION = {
    'mainnet': TokenAllocation(
        token_id=1,  # Doesn't matter, use network id
        factor=16,
        event="Alpha Trader (Mainnet)"
    ),
    'gchain': TokenAllocation(
        token_id=100,  # Doesn't matter, use network id
        factor=4,
        event="Alpha Trader (Gnosis Chain)"
    )

}


class IndexedPoapAllocations:
    """
    Basic storage for the collection of token allocations indexed by account
    """

    def __init__(self):
        self.data = defaultdict(list[TokenAllocation])
        # This is a tally of all allocation factors with multiplicity
        self.total_weight: int = 0
        self.excluded_accounts = {Account(a) for a in load_excluded_accounts()}

    def items(self):
        """returns the items from the inner data field"""
        return self.data.items()

    def get(self, key):
        return self.data.get(key, [])

    def insert_many(
            self,
            accounts: set[Account],
            token: TokenAllocation
    ):
        """inserts token for each account by appending to the data dict"""
        for account in accounts - self.excluded_accounts:
            # key exists because the class is initialized as default dict
            self.data[account.account].append(token)
            self.total_weight += token.factor

    def accounts(self) -> set[str]:
        return set(self.data.keys())

    def populate_alpha_users(
            self,
            dune: DuneAnalytics,
            load_from: NetworkFile
    ):
        """
        Fetches and updates indexed holders with alpha user allocation data.
        This method mutates the data field of self (inserting new entries)
        :param load_from: Network file to load from
        :param dune: an open connection to dune
        """
        for chain in ['mainnet', 'gchain']:
            alphas = fetch_alpha_traders(
                dune,
                network=chain,
                block_number=SNAPSHOT_BLOCK_NUMBER[chain],
                load_from=load_from
            )
            allocation = ALPHA_TRADER_ALLOCATION[chain]
            self.insert_many(alphas, allocation)

    def populate_poap_holders(self, category_file: File):
        """
        Reads the holders list based on tokens declared in category file
        and self updates poap holder allocations
        :param category_file: file to token categories
        """
        tokens = get_poap_tokens(category_file)
        for token_id, token in tokens.items():
            holders = load_poap_holders(token_id)
            self.insert_many(holders, token)
            num_holders = len(holders)
            assert len(
                set(holders)) == num_holders, f"Duplicate Holder token {token_id}!"
            print(f"POAP {token_id} has {num_holders} holders")

    @classmethod
    def load_from(
            cls,
            dune: DuneAnalytics,
            alpha_traders_file: NetworkFile,
            category_file: File
    ) -> IndexedPoapAllocations:
        results = cls()

        # Append Alpha user allocations.
        results.populate_alpha_users(dune, load_from=alpha_traders_file)

        # Append POAP holder allocations.
        results.populate_poap_holders(category_file=category_file)

        return results


def load_poap_holders(token_id: int) -> set[Account]:
    """Loads POAP holders from file."""
    filename = f'./data/poap-holders/token-{token_id}.csv'
    with open(filename, 'r', encoding='utf-8') as file:
        # We instantiate Account and only return the account field
        # to leverage the "checksum" (without having to implement hash)
        return {Account(line) for line in file.read().splitlines()}


def get_poap_tokens(category_file: File) -> dict[int, TokenAllocation]:
    """
    Opens the collection of all POAPs for consideration
    :param category_file: file path to token categories
    :return: collection of TokenAllocation indexed by token id
    """
    with open(category_file.filename(), 'r', encoding='utf-8') as file:
        dict_reader = csv.DictReader(file)
        tokens = {}
        for row in dict_reader:
            token_id = int(row['token_id'])
            tokens[token_id] = TokenAllocation(
                token_id=token_id,
                factor=int(row['factor']),
                event=row['event'],
            )
    return tokens


def derive_allocations(
        dune: DuneAnalytics,
        load_from: AllocationFiles,
) -> IndexedAllocations:
    """
    Main method of this script to derive allocations for alpha trader and poap holders
    :param dune: required to fetch the alpha trader data.
    :param load_from: filepath to existing csv data for POAP allocations
    :return: POAP holder allocations indexed by account.
    """
    try:
        return IndexedAllocations.load_from_file(load_from.poap_allocations)
    except FileNotFoundError:
        print(
            f"POAP Allocation file {load_from.poap_allocations} "
            f"not found, building from scratch"
        )

    indexed_allocations = IndexedPoapAllocations.load_from(
        dune,
        load_from.alpha_traders,
        load_from.poap_categories
    )

    allocations = [
        Allocation(
            account=account,
            amount=sum(
                t.allocation_amount_wei(indexed_allocations.total_weight)
                for t in tokens_held
            )
        )
        for account, tokens_held in indexed_allocations.items()
    ]
    total_allocation = sum(a.amount for a in allocations)
    # Ensures total allocation as close as possible without exceeding.
    assert total_allocation <= USER_ALLOCATION['POAP']
    unallocated = (USER_ALLOCATION['POAP'] - total_allocation) / pow(10, 18)
    print(f"{unallocated} unallocated for poap")

    allocations.sort(key=lambda t: (-t.amount, t.account))
    indexed_allocations = dump_results_and_index_by_account(
        results=allocations,
        file=load_from.poap_allocations
    )
    return IndexedAllocations(indexed_allocations)


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    derive_allocations(dune_connection, AllocationFiles())
