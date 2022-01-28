from src.constants import EXPECTED_TOTAL
from src.dune_analytics import DuneAnalytics
from src.fetch.combined_holders import load_excluded_accounts
from src.generate.complete_allocation import generate_complete_allocation

if __name__ == '__main__':
    dune_connection = DuneAnalytics.new_from_environment()
    allocations = generate_complete_allocation(dune_connection)

    excluded_accounts = load_excluded_accounts()
    allocation_accounts = allocations.get_all_accounts()

    # This is the Gnosis DAO safe which was excluded from airdrop
    # allocations entitled an allocation.
    only_exceptions = {
        "0x0da0c3e52c977ed3cbc641ff02dd271c3ed55afe",  # Gnosis DAO Safe
        "0x849d52316331967b6ff1198e5e32a0eb168d039d",  # Gnosis DAO Daughter Safe
    }
    assert excluded_accounts & allocation_accounts == only_exceptions
    unallocated = EXPECTED_TOTAL - allocations.total_allocation_wei()
    assert unallocated == 6900049544, f"unexpected unallocated amount: {unallocated}"
    print(allocations)
    print("Allocation Generation Complete! Have a nice day.")
