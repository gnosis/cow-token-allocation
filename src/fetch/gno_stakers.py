"""
Stores the result of querying entire GNO token holders on both networks into a single file
`data/{network}-lp-holders.csv`
"""

from src.constants import SNAPSHOT_BLOCK_NUMBER
from src.dune_analytics import DuneAnalytics
from src.files import File, HolderFiles
from src.models import GnoHolder
from src.utils.data import dump_results_and_index_by_account


def fetch_gno_stakers(
        dune: DuneAnalytics,
        block_number: str,
        load_from: File,
) -> dict[str, GnoHolder]:
    """
    :param dune: open connection to dune analytics
    :param block_number: str representation of an integer ethereum block number
    :param load_from: File path to load existing data from
    :return: collection of `GnoHolders` at `block_number`
    """
    try:
        return GnoHolder.load_from_file("GNO stakers", load_from)
    except FileNotFoundError:
        print(f"file at {load_from.name} not found. Fetching from Dune")

    data_set = dune.fetch(
        query_filepath="./queries/staked_gno.sql",
        network='gchain',
        name="GNO stakers",
        parameters=[{"key": "BlockNumber", "type": "number", "value": block_number}]
    )
    results = sorted([
        GnoHolder(account=entry['depositor'], amount=entry['staked_gno'])
        for entry in data_set
    ], key=lambda t: (-t.amount, t.account))
    return dump_results_and_index_by_account(
        results=results,
        file=load_from
    )


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    fetch_gno_stakers(
        dune_connection,
        SNAPSHOT_BLOCK_NUMBER['gchain'],
        HolderFiles().stakers
    )
