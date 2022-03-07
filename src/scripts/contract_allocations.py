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

    airdrop_total, found = 0, 0
    for alloc in sorted_contract_allocations:
        if alloc.Account in not_wallets:
            # proof that this only affects GNO allocations!
            gno_allocation = alloc.Airdrop + alloc.GnoOption
            assert alloc.total() - gno_allocation == 0
            airdrop_total += alloc.Airdrop
            if found < 3:
                found += 1
                print(
                    f"{found}. {alloc.Account} - {(alloc.Airdrop / 1e24):.3f}M"
                )

    print(f"total {network} (in WEI) {airdrop_total}")
    return airdrop_total


if __name__ == '__main__':
    mainnet_total = non_wallet_allocation(
        network='mainnet', allocation_file=AllocationFiles().mainnet_allocation
    )
    gchain_total = non_wallet_allocation(
        network='gchain', allocation_file=AllocationFiles().gchain_allocation
    )

    print(
        "Grand Total Non Wallet Airdrop Allocation (in WEI)",
        gchain_total + mainnet_total
    )
