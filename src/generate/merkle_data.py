"""
Constructs a complete allocation file to be consumed by the
token contract deployment script.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum

from src.dune_analytics import DuneAnalytics
from src.files import AllocationFiles, OptionsFiles
from src.generate.holder_allocation import derive_allocations as get_holder_allocations
from src.generate.poap_allocation import derive_allocations as get_poap_allocations
from src.generate.trader_allocation import derive_allocations as get_trader_allocations
from src.models import Allocation, IndexedAllocations
from src.utils.data import write_to_csv, flatten_without_duplicates, File


class AllocationOption(Enum):
    TEAM = "Team Allocation"
    INVESTOR = "Investor Option"
    ANON_INVESTOR = "Anon Investor"
    ADVISOR = "Advisor Option"
    AIRDROP = "Airdrop"

    def load_options(self) -> IndexedAllocations:
        if self == AllocationOption.TEAM:
            return IndexedAllocations.load_from_file(OptionsFiles.team)
        if self == AllocationOption.INVESTOR:
            return IndexedAllocations.load_from_file(OptionsFiles.investor)
        if self == AllocationOption.ANON_INVESTOR:
            return IndexedAllocations.load_from_file(OptionsFiles.anon)
        if self == AllocationOption.ADVISOR:
            return IndexedAllocations.load_from_file(OptionsFiles.advisor)
        if self == AllocationOption.AIRDROP:
            return IndexedAllocations.load_from_file(OptionsFiles.airdrop)
        raise NotImplementedError(f"Option type: {self} - Coming soon!")


# pylint: disable=invalid-name
@dataclass
class MerkleLeaf:
    """Columns of the generated CSV output for final allocation"""
    Account: str
    Airdrop: int
    GnoOption: int
    UserOption: int
    Investor: int
    Team: int
    Advisor: int

    def total(self):
        return self.Airdrop + self.GnoOption + self.UserOption + \
               self.Team + self.Advisor + self.Investor

    @classmethod
    def from_option(cls, allocation: Allocation, option: AllocationOption):
        return cls(
            Account=allocation.account,
            Airdrop=allocation.amount if option == AllocationOption.AIRDROP else 0,
            GnoOption=0,
            UserOption=allocation.amount if option == AllocationOption.ANON_INVESTOR else 0,
            Investor=allocation.amount if option == AllocationOption.INVESTOR else 0,
            Team=allocation.amount if option == AllocationOption.TEAM else 0,
            Advisor=allocation.amount if option == AllocationOption.ADVISOR else 0,
        )

    def update_account(self, updated_account):
        self.Account = updated_account

    @classmethod
    # pylint: disable=too-many-arguments
    def from_mixed_allocations(
            cls,
            trader_primary: Allocation,
            trader_consolation: Allocation,
            holder_allocation: Allocation,
            poap_allocation: Allocation,
            user_option: Allocation
    ) -> MerkleLeaf:
        """
        Given various other allocations, the fields are populated as functions of these
        """
        account_set = {
            trader_primary.account,
            trader_consolation.account,
            holder_allocation.account,
            poap_allocation.account,
            user_option.account
        }
        assert len(account_set) == 1
        account = account_set.pop()
        airdrop_allocations = [
            holder_allocation,
            trader_primary,
            poap_allocation,
            trader_consolation
        ]
        return cls(
            Account=account,
            Airdrop=sum(t.amount for t in airdrop_allocations),
            GnoOption=holder_allocation.amount,
            UserOption=user_option.amount,
            Investor=0,
            Team=0,
            Advisor=0
        )

    def sort_order(self):
        return (
            -self.Airdrop,
            -self.GnoOption,
            -self.UserOption,
            -self.Investor,
            -self.Team,
            -self.Advisor,
            self.Account
        )

    def __str__(self):
        return f"{self.Account}: {self.Airdrop / 10 ** 18}"

    def __hash__(self):
        return self.Account.__hash__()

    @classmethod
    def fetch(
            cls,
            dune: DuneAnalytics,
            allocation_files: AllocationFiles
    ) -> list[MerkleLeaf]:
        """
        This method goes one level down to fetch the individual allocation components
        needed to build a MerkleLeaf
        :param dune: Open Dune connection (used to fetch - if necessary)
        :param allocation_files: file locations of existing data - if available)
        :return: Merkle Leaves corresponding to allocation data
        """
        trader_allocations = get_trader_allocations(
            dune,
            load_from=allocation_files.trader_data
        )
        combined_allocations = MerkleLeaf.build_from(
            trader_primary=trader_allocations.primary,
            trader_consolation=trader_allocations.consolation,
            poap_options=get_poap_allocations(dune, load_from=allocation_files),
            gno_options=get_holder_allocations(dune, load_from=allocation_files),
            user_options=trader_allocations.user_options,
        )
        combined_allocations.sort(key=lambda a: (-a.Airdrop, a.Account))
        write_to_csv(
            data_list=combined_allocations,
            outfile=allocation_files.merkle_leaf
        )
        return combined_allocations

    @classmethod
    def load_from(cls, load_file: File) -> list[MerkleLeaf]:
        """Loads MerkleLeafs from specified file, raises if not successful"""
        with open(load_file.filename(), 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return [
                cls(
                    Account=row['Account'],
                    GnoOption=int(row['GnoOption']),
                    UserOption=int(row['UserOption']),
                    Airdrop=int(row['Airdrop']),
                    Investor=int(row['Investor']),
                    Team=int(row['Team']),
                    Advisor=int(row['Advisor']),
                )
                for row in reader
            ]

    @classmethod
    def fetch_or_load_from_file(
            cls,
            dune: DuneAnalytics,
            load_from: AllocationFiles
    ) -> list[MerkleLeaf]:
        """
        Loads AirdropAllocation from file when provided. Otherwise, builds it.
        """
        try:
            return MerkleLeaf.load_from(load_from.merkle_leaf)
        except FileNotFoundError:
            print(
                f"file at {load_from.merkle_leaf.name} not found, fetching from Dune..."
            )

        return cls.fetch(dune, load_from)

    # pylint: disable=too-many-arguments
    @classmethod
    def build_from(
            cls,
            trader_primary: IndexedAllocations,
            trader_consolation: IndexedAllocations,
            poap_options: IndexedAllocations,
            gno_options: IndexedAllocations,
            user_options: IndexedAllocations,
    ) -> list[MerkleLeaf]:
        """Builds airdrop allocation from all allocation types."""
        assert set(trader_primary.keys()).isdisjoint(set(trader_consolation.keys()))

        account_set = flatten_without_duplicates([
            gno_options.keys(),
            user_options.keys(),
            trader_primary.keys(),
            trader_consolation.keys(),
            poap_options.keys(),
        ])

        allocations = []
        for account in account_set:
            allocations.append(
                cls.from_mixed_allocations(
                    trader_primary=trader_primary.get(account),
                    trader_consolation=trader_consolation.get(account),
                    holder_allocation=gno_options.get(account),
                    poap_allocation=poap_options.get(account),
                    user_option=user_options.get(account),
                )
            )
        return allocations


if __name__ == '__main__':
    dune_connection = DuneAnalytics.new_from_environment()
    MerkleLeaf.fetch(dune_connection, AllocationFiles())
