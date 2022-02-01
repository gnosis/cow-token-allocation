"""
Once the complete allocation file has been generated, we split the allocations based
on the following basic conditions:

1. Mainnet Allocation:
    allocation >= `ALLOCATION_SPLIT`
2. Gnosis Chain:
    allocation < `ALLOCATION_SPLIT`

Additionally, since externally owned accounts are cross-network compatible,
but smart contracts (such as Gnosis Safe) are not, we have to investigate
this for each account.

Accounts which are contracts on only one of the two networks will receive their
allocation on the network they exist (regardless of allocation split).

Accounts which are contracts on both networks are treated as a "special case"
we collect this list and parse though all the accounts from the data files generated
throughout the program and partition them by network of eligibility.

If the account is exclusively eligible for allocation on one of the two networks
the allocation is given there.

There was only one cases of a Gnosis Safe contract on both networks that was eligible
for allocation on both networks:

# This is a Safe on both networks with an overlapping set of owner accounts
# (beyond the threshold of 2)
# https://blockscout.com/xdai/mainnet/address/0x365bd827c68D5DE0e2BFA5871dc0ECaAf074d5Ab/read-proxy
# https://etherscan.io/address/0x365bd827c68d5de0e2bfa5871dc0ecaaf074d5ab#readProxyContract
Defined as SPECIAL_CASES here
"""
import os
from dataclasses import dataclass

from src.constants import EXPECTED_TOTAL, ANONYMOUS_INVESTMENTS, WEI_IN_ETH
from src.dune_analytics import DuneAnalytics
from src.fetch.contracts import EvmAccountInfo
from src.files import AllocationFiles
from src.generate.merkle_data import MerkleLeaf, AllocationOption
from src.utils.data import write_to_csv

ALLOCATION_SPLIT = 10000 * 10 ** 18
NODE_URL = {
    'mainnet': os.environ.get('NODE_URL'),
    'gchain': 'https://rpc.gnosischain.com/',
}
# This is a Safe on both networks with an overlapping set of owner accounts
# (beyond the threshold of 2)
# https://blockscout.com/xdai/mainnet/address/0x365bd827c68D5DE0e2BFA5871dc0ECaAf074d5Ab/read-proxy
# https://etherscan.io/address/0x365bd827c68d5de0e2bfa5871dc0ecaaf074d5ab#readProxyContract
MANUAL_CASES = {
    # account -> where the allocation should be directed (based on manual investigation)
    '0x365bd827c68d5de0e2bfa5871dc0ecaaf074d5ab': 'mainnet'
}


def handle_special_considerations(
        special_cases: list[MerkleLeaf],
        mainnet: list[MerkleLeaf],
        gchain: list[MerkleLeaf],
        accounts: dict[str, set[str]],
        manual_cases: dict[str, str],
):
    """
    Special cases are when an account is a smart contract on both networks.
    We fetch the accounts by network (based on all the generated data)
    If the account is eligible for airdrop on both mainnet and gchain
        then we deem this as requiring manual attention
    If the account is only eligible on one of the two networks,
        then it is clear where they should receive their allocation
    Otherwise, we raise a value error.
    """
    mainnet_accounts = accounts['mainnet']
    gchain_accounts = accounts['gchain']
    while special_cases:
        allocation = special_cases.pop()
        account = allocation.Account
        if account in gchain_accounts & mainnet_accounts:
            print(f"Requires manual investigation {allocation}")
            network = manual_cases[account]
            if network == 'mainnet':
                mainnet.append(allocation)
            elif network == 'gchain':
                gchain.append(allocation)
            else:
                raise ValueError(f"unknown manual case value {network}")
        elif account in gchain_accounts:
            gchain.append(allocation)
        elif account in mainnet_accounts:
            mainnet.append(allocation)
        else:
            raise ValueError(f"account {account} should not be a special case!")


@dataclass
class SplitAllocations:
    """Basic class to store the output of split_allocation"""
    mainnet: list[MerkleLeaf]
    gchain: list[MerkleLeaf]

    def get_all_accounts(self) -> set[str]:
        mainnet_accounts = set(a.Account for a in self.mainnet)
        gchain_accounts = set(a.Account for a in self.gchain)
        return mainnet_accounts | gchain_accounts

    def total_allocation_wei(self) -> int:
        mainnet_total = sum(a.total() for a in self.mainnet)
        gchain_total = sum(a.total() for a in self.gchain)
        return mainnet_total + gchain_total

    def total_airdrop(self) -> float:
        mainnet_total = sum(a.Airdrop for a in self.mainnet)
        gchain_total = sum(a.Airdrop for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def total_advisor(self) -> float:
        mainnet_total = sum(a.Advisor for a in self.mainnet)
        gchain_total = sum(a.Advisor for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def total_gno_option(self) -> float:
        mainnet_total = sum(a.GnoOption for a in self.mainnet)
        gchain_total = sum(a.GnoOption for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def total_user_option(self) -> float:
        mainnet_total = sum(a.UserOption for a in self.mainnet)
        gchain_total = sum(a.UserOption for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def total_investor(self) -> float:
        mainnet_total = sum(a.Investor for a in self.mainnet)
        gchain_total = sum(a.Investor for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def total_team(self) -> float:
        mainnet_total = sum(a.Team for a in self.mainnet)
        gchain_total = sum(a.Team for a in self.gchain)
        return (mainnet_total + gchain_total) / WEI_IN_ETH

    def append_options(self, option_type: AllocationOption):
        option_allocations = option_type.load_options()

        if option_type == AllocationOption.TEAM:
            option_recipients = set(option_allocations.keys())
            assert option_recipients.isdisjoint(self.get_all_accounts())

        appendages = sorted(
            [
                MerkleLeaf.from_option(allocation, option_type)
                for allocation in option_allocations.values()
            ],
            key=lambda t: t.sort_order()
        )
        allocation_total = sum(a.total() for a in appendages)
        print(
            f"Appending {len(appendages)} {option_type.name} entries to mainnet "
            f"allocation with a total of {allocation_total / 1e18} tokens"
        )
        self.mainnet += appendages

    def redirect_vesting_contract_allocation(self):
        # This particular source account is a Vesting contract which will not be
        # able to claim. We redirect the allocation to the contract's owner
        # https://etherscan.io/address/0x9ee585a6c270fd8b046a5b2019fdac86544bca61
        redirect_source = "0x9ee585a6c270fd8b046a5b2019fdac86544bca61"
        # https://etherscan.io/address/0x9f7dfab2222a473284205cddf08a677726d786a0
        redirect_dest = "0x9f7dfab2222a473284205cddf08a677726d786a0"

        for allocation in self.mainnet + self.gchain:
            if allocation.Account == redirect_source:
                print(f"Redirecting allocation {allocation} to {redirect_dest}")
                allocation.update_account(redirect_dest)

    def __str__(self):
        mill = pow(10, 6)
        grand_total = self.total_allocation_wei() / WEI_IN_ETH / mill
        #  anonymous investment moved from investor to user option category
        anon_investment = ANONYMOUS_INVESTMENTS / WEI_IN_ETH
        investor_total = (self.total_investor() + anon_investment) / mill
        user_option_total = (self.total_user_option() - anon_investment) / mill

        unallocated = EXPECTED_TOTAL - self.total_allocation_wei()
        return f"======================\n" \
               f"Allocation Counts\n" \
               f"   Mainnet:       {len(self.mainnet)}\n" \
               f"   Gnosis Chain: {len(self.gchain)}\n" \
               f"----------------------\n" \
               f"Category Totals\n" \
               f"   Airdrop:     {self.total_airdrop() / mill:.1f}M\n" \
               f"   Gno Option:   {self.total_gno_option() / mill:.1f}M\n" \
               f"   User Option:  {user_option_total:.1f}M\n" \
               f"   Investor:    {investor_total:.1f}M\n" \
               f"   Advisory:    {self.total_advisor() / mill:.1f}M\n" \
               f"   Team:         {self.total_team() / mill:.1f}M\n" \
               f"----------------------\n" \
               f"Grand Total:    {grand_total:.1f}M\n" \
               f"----------------------\n" \
               f"Unallocated Amount\n" \
               f"        {unallocated} WEI\n" \
               f"======================"


def split_allocations(
        allocations: list[MerkleLeaf],
        known_contracts: dict[str, set[str]],
        accounts: dict[str, set[str]],
) -> SplitAllocations:
    """
    Fetches the allocation file and splits according to
    the criteria involving ALLOCATION_SPLIT and is_contract
    """
    num_allocations = len(allocations)
    mainnet_contracts = known_contracts['mainnet']
    gchain_contracts = known_contracts['gchain']
    overlap = mainnet_contracts & gchain_contracts

    print(f"{len(overlap)} contracts on both networks")

    mainnet, gchain, special_consideration = [], [], []
    while allocations:
        allocation = allocations.pop(0)
        account = allocation.Account
        if account in overlap:
            special_consideration.append(allocation)
            continue
        if allocation.Airdrop >= ALLOCATION_SPLIT:
            if account not in gchain_contracts:
                # Account is EOA or mainnet contract!
                mainnet.append(allocation)
            else:
                gchain.append(allocation)
        else:  # allocation.Airdrop < ALLOCATION_SPLIT
            if account not in mainnet_contracts:
                # Account is EOA or gchain contract!
                gchain.append(allocation)
            else:
                mainnet.append(allocation)

    print(f"handling {len(special_consideration)} special cases")
    handle_special_considerations(
        special_cases=special_consideration,
        mainnet=mainnet,
        gchain=gchain,
        accounts=accounts,
        manual_cases=MANUAL_CASES
    )

    assert len(gchain) == len(set(gchain)), "Duplicate in gchain allocations!"
    assert len(mainnet) == len(set(mainnet)), "Duplicate in mainnet allocations!"
    assert len(gchain) + len(mainnet) == num_allocations

    mainnet.sort(key=lambda t: (-t.Airdrop, t.Account))
    gchain.sort(key=lambda t: (-t.Airdrop, t.Account))
    write_to_csv(
        outfile=AllocationFiles().mainnet_allocation,
        data_list=mainnet
    )
    write_to_csv(
        outfile=AllocationFiles().gchain_allocation,
        data_list=gchain
    )
    return SplitAllocations(mainnet=mainnet, gchain=gchain)


def fetch_and_split_allocations(
        dune: DuneAnalytics
) -> SplitAllocations:
    allocation_files = AllocationFiles()
    fetched_allocations = MerkleLeaf.fetch_or_load_from_file(
        dune,
        allocation_files
    )

    return split_allocations(
        allocations=fetched_allocations,
        known_contracts={
            network: {
                address
                for address, is_contract in
                EvmAccountInfo(
                    node_url=NODE_URL[network],
                    addresses=[a.Account for a in fetched_allocations],
                    network=network
                ).contracts(
                    load_from=AllocationFiles.contracts
                ).items()
                if is_contract
            }
            for network in ['mainnet', 'gchain']
        },
        accounts={
            network: allocation_files.load_all_network_accounts(network)
            for network in ['mainnet', 'gchain']
        },
    )


if __name__ == '__main__':
    dune_connection = DuneAnalytics.new_from_environment()
    fetch_and_split_allocations(dune_connection)
