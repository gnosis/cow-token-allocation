# pylint: disable=duplicate-code,too-few-public-methods,too-many-arguments
import argparse
from enum import Enum
from typing import Optional

from src.dune_analytics import DuneAnalytics
from src.fetch.combined_holders import CombinedGnoHolder
from src.fetch.trader_data import CowSwapTrader
from src.files import File, AllocationFiles
from src.generate.merkle_data import MerkleLeaf
from src.generate.poap_allocation import IndexedPoapAllocations
from src.models import Account, IndexedAllocations, Allocation
from src.utils.data import index_by_account


class AllocationType(Enum):
    PRIMARY = 'Primary'
    CONSOLATION = 'Consolation'


class TraderDetails:

    def __init__(
            self,
            data: dict[str, CowSwapTrader],
            allocations: IndexedAllocations,
            allocation_type: AllocationType,
    ):
        self.data = data
        self.allocations = allocations
        self.allocation_type = allocation_type

    def account_detail_string(self, account: str) -> Optional[str]:
        trader_activity = self.data.get(account)
        if trader_activity is None:
            return None
        allocation = self.allocations.get(account)
        return f"{trader_activity}\n" \
               f"------------------------------------------\n" \
               f"  allocation type:   {self.allocation_type.value}\n" \
               f"  trader allocation:" \
               f"                {(allocation.amount / 1e18):.3f}"


class VerboseTraderDetails:
    def __init__(
            self,
            primary: TraderDetails,
            consolation: TraderDetails,
            raw_trader_data: dict[str, CowSwapTrader],
    ):
        self.primary = primary
        self.consolation = consolation
        self.raw_trader_data = raw_trader_data


class HolderDetails:
    def __init__(
            self,
            data: dict[str, CombinedGnoHolder],
            allocations: IndexedAllocations
    ):
        self.holder_data = data
        self.allocations = allocations

    def account_detail_string(self, account: str) -> str:
        gno = self.holder_data.get(
            account,
            CombinedGnoHolder.zero_for_account(account)
        )
        allocation = self.allocations.get(account)
        if gno.total_gno < 0.1:
            results = "   Total GNO balance < 0.1\n"
        else:
            results = f"  mainnet:           {(gno.mainnet_gno / 1e18):.3f}\n" \
                      f"  gnosis chain:      {(gno.gchain_gno / 1e18):.3f}\n" \
                      f"  total gno:         {(gno.total_gno / 1e18):.3f}\n"
        return results + f"  holder allocation:" \
                         f"                 {(allocation.amount / 1e18):.3f}"


class PoapDetails:

    def __init__(self, poap_allocations, allocations):
        self.poaps = poap_allocations
        self.allocations = allocations

    def account_detail_string(self, account: str) -> str:
        total_allocation = self.allocations.get(account).amount / 1e18
        individual_allocations = [
            str(poap_allocation)
            for poap_allocation in self.poaps.get(account)
        ]
        results = "  -----\n"
        if not individual_allocations:
            results += "  None\n"
        else:
            list_string = "\n  -----\n".join(individual_allocations)
            results += f"  {list_string.strip()}\n"
        return results + f"  -----\n" \
                         f"  community allocation:" \
                         f"              {total_allocation:.3f}"


class AllocationDetails:

    def __init__(
            self,
            holder: HolderDetails,
            trader: VerboseTraderDetails,
            poap: PoapDetails,
            allocation_totals: IndexedAllocations
    ):
        self.holder_data = holder
        self.trader_data = trader
        self.poap_data = poap
        self.total_allocation = allocation_totals

    def account_detail_string(self, account):
        primary_data = self.trader_data.primary.account_detail_string(account)
        consolation_data = self.trader_data.consolation.account_detail_string(account)
        raw_trader_data = self.trader_data.raw_trader_data.get(account, None)
        trader_details = "No trading activity prior to snapshot"
        if primary_data is not None:
            trader_details = primary_data
        elif consolation_data is not None:
            trader_details = consolation_data
        elif raw_trader_data is not None:
            trader_details = str(raw_trader_data)

        holder_details = self.holder_data.account_detail_string(account).strip()
        poap_details = self.poap_data.account_detail_string(account).strip()
        total_allocation = self.total_allocation.get(account).amount / 1e18
        return f"==========================================\n" \
               f"Account\n{account}\n" \
               f"------------------------------------------\n" \
               f"GNO Holder Details\n  {holder_details}\n" \
               f"------------------------------------------\n" \
               f"Trader Details\n  {trader_details.strip()}\n" \
               f"------------------------------------------\n" \
               f"Community Details (POAPs Held)\n  {poap_details}\n" \
               f"------------------------------------------\n" \
               f"Total Allocation                   {total_allocation:.3f}"


def load_all_data_from_out(allocation_files: AllocationFiles) -> AllocationDetails:
    # Load Holder Info
    holder_details = HolderDetails(
        data=index_by_account(
            CombinedGnoHolder.load_from(
                load_from=allocation_files.holder_data.combined
            )
        ),
        allocations=IndexedAllocations.load_from_file(
            file=allocation_files.holder_allocation
        )
    )

    # Load Trader Info
    trader_details = VerboseTraderDetails(
        raw_trader_data=CowSwapTrader.load_and_merge_network_trader_data(
            mainnet_file=allocation_files.trader_data.traders.filename('mainnet'),
            gchain_file=allocation_files.trader_data.traders.filename('gchain'),
        ),
        primary=TraderDetails(
            data=CowSwapTrader.load_from_file(
                load_file=allocation_files.trader_data.primary_trader
            ),
            allocations=IndexedAllocations.load_from_file(
                file=allocation_files.trader_data.primary_allocation
            ),
            allocation_type=AllocationType.PRIMARY
        ),
        consolation=TraderDetails(
            data=CowSwapTrader.load_from_file(
                load_file=allocation_files.trader_data.consolation_trader
            ),
            allocations=IndexedAllocations.load_from_file(
                file=allocation_files.trader_data.consolation_allocation
            ),
            allocation_type=AllocationType.CONSOLATION
        ),
    )

    # Load POAP holder allocations.
    poap_details = PoapDetails(
        poap_allocations=IndexedPoapAllocations.load_from(
            DuneAnalytics('', '', 0),  # This is a dummy dune instance.
            allocation_files.alpha_traders,
            allocation_files.poap_categories
        ),
        allocations=IndexedAllocations.load_from_file(
            file=allocation_files.poap_allocations
        )
    )
    merkle_leaves = MerkleLeaf.load_from(allocation_files.merkle_leaf)

    return AllocationDetails(
        holder=holder_details,
        trader=trader_details,
        poap=poap_details,
        allocation_totals=IndexedAllocations({
            leaf.Account: Allocation(leaf.Account, leaf.Airdrop)
            for leaf in merkle_leaves
        })
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Fetch Allocation Receipts for a list of accounts"
    )
    parser.add_argument(
        "--account-file",
        type=str,
        help="file containing ethereum addresses",
    )
    args = parser.parse_args()
    # Load all Data related to allocations and where they were derived from

    allocation_details = load_all_data_from_out(AllocationFiles())
    path, filename = args.account_file.rsplit('/', 1)
    accounts = sorted(
        Account.load_from(File(name=filename, path=path)),
        key=lambda t: t.account
    )

    receipts = [allocation_details.account_detail_string(a.account) for a in accounts]
    for receipt in receipts:
        print(receipt)
