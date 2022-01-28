from src.dune_analytics import DuneAnalytics
from src.files import AllocationFiles
from src.generate.merkle_data import AllocationOption
from src.split_allocation import SplitAllocations, fetch_and_split_allocations
from src.utils.data import write_to_csv


def generate_complete_allocation(
        dune: DuneAnalytics
) -> SplitAllocations:
    allocations = fetch_and_split_allocations(dune)

    for option in AllocationOption:
        allocations.append_options(option_type=option)

    allocations.redirect_vesting_contract_allocation()

    print("Overwriting mainnet allocation file with updated entries")
    write_to_csv(
        outfile=AllocationFiles().mainnet_allocation,
        data_list=allocations.mainnet
    )
    return allocations


if __name__ == '__main__':
    dune_connection = DuneAnalytics.new_from_environment()
    generate_complete_allocation(dune_connection)
