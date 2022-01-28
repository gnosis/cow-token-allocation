"""
Derives Holder allocations from GNO holder data
"""
from __future__ import annotations

from src.constants import GNO_HOLDER_ALLOCATION
from src.dune_analytics import DuneAnalytics
from src.fetch.combined_holders import generate_combined_holders
from src.files import AllocationFiles
from src.models import IndexedAllocations
from src.utils.data import dump_results_and_index_by_account


def derive_allocations(
        dune: DuneAnalytics,
        load_from: AllocationFiles
) -> IndexedAllocations:
    """
    Generates combined holder data and transforms it into Allocation
    """
    try:
        return IndexedAllocations.load_from_file(load_from.holder_allocation)
    except FileNotFoundError:
        print(f"file {load_from.holder_allocation} not found, fetching from Dune")

    combined_holders = generate_combined_holders(dune, load_from.holder_data)

    eligible_supply = sum(holder.total_gno for holder in combined_holders)
    allocations = [holder.to_allocation(eligible_supply) for holder in combined_holders]

    total_allocated = sum(h.amount for h in allocations)
    assert total_allocated <= GNO_HOLDER_ALLOCATION
    unallocated = (GNO_HOLDER_ALLOCATION - total_allocated) / pow(10, 18)
    print(f"{unallocated} unallocated holder tokens")

    allocations.sort(key=lambda t: (-t.amount, t.account))
    indexed_allocations = dump_results_and_index_by_account(
        results=allocations,
        file=load_from.holder_allocation
    )
    return IndexedAllocations(indexed_allocations)


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    derive_allocations(
        dune=dune_connection,
        load_from=AllocationFiles()
    )
