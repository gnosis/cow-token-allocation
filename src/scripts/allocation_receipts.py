# pylint: disable=duplicate-code,too-few-public-methods,too-many-arguments
import argparse
from enum import Enum
from typing import Optional

from src.fetch.combined_holders import CombinedGnoHolder
from src.fetch.trader_data import CowSwapTrader
from src.files import File, AllocationFiles
from src.models import Account, IndexedAllocations
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
               f"  trader allocation: {(allocation.amount / 1e18):.3f}"


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
            return "   Total GNO balance < 0.1"
        return f"  mainnet:           {(gno.mainnet_gno / 1e18):.3f}\n" \
               f"  gnosis chain:      {(gno.gchain_gno / 1e18):.3f}\n" \
               f"  total gno:         {(gno.total_gno / 1e18):.3f}\n" \
               f"  holder allocation: {(allocation.amount / 1e18):.3f}"


class PoapDetails:

    def __init__(self, mainnet, gchain, allocations):
        self.mainnet_alphas = set(a.account for a in mainnet)
        self.gchain_alphas = set(a.account for a in gchain)
        self.allocations = allocations

    def account_detail_string(self, account: str) -> str:
        allocation = self.allocations.get(account).amount / 1e18
        return f"  mainnet alpha:        {account in self.mainnet_alphas}\n" \
               f"  gchain alpha:         {account in self.gchain_alphas}\n" \
               f"  community allocation: {allocation:.3f}"


class AllocationDetails:

    def __init__(
            self,
            holder: HolderDetails,
            primary: TraderDetails,
            consolation: TraderDetails,
            raw_trader_data: dict[str, CowSwapTrader],
            poap: PoapDetails,
    ):
        self.holder_data = holder
        self.raw_trader_data = raw_trader_data
        self.primary_trader_data = primary
        self.consolation_trader_data = consolation
        self.poap_data = poap

    def account_detail_string(self, account):
        primary_data = self.primary_trader_data.account_detail_string(account)
        consolation_data = self.consolation_trader_data.account_detail_string(account)
        raw_trader_data = self.raw_trader_data.get(account, None)
        trader_details = "No trading activity prior to snapshot"
        if primary_data is not None:
            trader_details = primary_data
        elif consolation_data is not None:
            trader_details = consolation_data
        elif raw_trader_data is not None:
            trader_details = str(raw_trader_data)

        holder_details = self.holder_data.account_detail_string(account).strip()
        poap_details = self.poap_data.account_detail_string(account).strip()
        return f"==========================================\n" \
               f"Account\n{account}\n" \
               f"------------------------------------------\n" \
               f"GNO Holder Details\n  {holder_details}\n" \
               f"------------------------------------------\n" \
               f"Trader Details\n  {trader_details.strip()}\n" \
               f"------------------------------------------\n" \
               f"Community Details\n  {poap_details}"


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
    raw_trader_data = CowSwapTrader.load_and_merge_network_trader_data(
        mainnet_file=allocation_files.trader_data.traders.filename('mainnet'),
        gchain_file=allocation_files.trader_data.traders.filename('gchain'),
    )
    primary_trader_details = TraderDetails(
        data=CowSwapTrader.load_from(
            load_file=allocation_files.trader_data.primary_trader
        ),
        allocations=IndexedAllocations.load_from_file(
            file=allocation_files.trader_data.primary_allocation
        ),
        allocation_type=AllocationType.PRIMARY
    )
    consolation_details = TraderDetails(
        data=CowSwapTrader.load_from(
            load_file=allocation_files.trader_data.consolation_trader
        ),
        allocations=IndexedAllocations.load_from_file(
            file=allocation_files.trader_data.consolation_allocation
        ),
        allocation_type=AllocationType.CONSOLATION
    )

    # Load POAP Info
    poap_details = PoapDetails(
        # TODO - load gchain alphas
        mainnet=Account.load_from(
            load_file=allocation_files.alpha_traders.filename('mainnet')
        ),
        gchain=Account.load_from(
            load_file=allocation_files.alpha_traders.filename('gchain')
        ),
        allocations=IndexedAllocations.load_from_file(
            file=allocation_files.poap_allocations
        )
    )

    return AllocationDetails(
        holder=holder_details,
        primary=primary_trader_details,
        consolation=consolation_details,
        poap=poap_details,
        raw_trader_data=raw_trader_data
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
