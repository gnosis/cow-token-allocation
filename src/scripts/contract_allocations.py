from src.constants import NODE_URL
from src.fetch.contracts import EvmAccountInfo
from src.files import AllocationFiles, NetworkFile, File
from src.generate.merkle_data import MerkleLeaf


def non_wallet_allocation(network: str, allocation_file: File) -> int:
    allocations = MerkleLeaf.load_from(allocation_file)
    account_info = EvmAccountInfo(
        node_url=NODE_URL[network],
        addresses=[a.Account for a in allocations],
        network=network
    )
    contracts = account_info.contracts(load_from=NetworkFile("contracts.txt"))
    not_wallets = account_info.get_non_wallets(
        [c for c, is_contract in contracts.items() if is_contract]
    )
    print(
        f"found {len(not_wallets)} contract allocations to non-wallets on {network}.\n"
        f"printing Top 3"
    )
    sorted_contract_allocations = sorted([
        a for a in allocations
        if contracts[a.Account] is True
    ], key=lambda t: t.Airdrop, reverse=True)

    allocation_total, found = 0, 0
    for allocation in sorted_contract_allocations:
        if allocation.Account in not_wallets:
            gno_allocation = allocation.Airdrop + allocation.GnoOption
            # proof that this only affects GNO allocations!
            assert allocation.total() - gno_allocation == 0
            allocation_total += allocation.Airdrop + allocation.GnoOption
            if found < 3:
                found += 1
                print(
                    f"{found}. {allocation.Account} - {(gno_allocation / 1e24):.3f}M"
                )

    print(f"total {network} ~{(allocation_total / 1e24):.2f}M")
    return allocation_total


if __name__ == '__main__':
    mainnet_total = non_wallet_allocation(
        network='mainnet', allocation_file=AllocationFiles().mainnet_allocation
    )
    gchain_total = non_wallet_allocation(
        network='gchain', allocation_file=AllocationFiles().gchain_allocation
    )

    print("Total Non Contract Allocation (in WEI)", gchain_total + mainnet_total)
