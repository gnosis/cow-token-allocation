"""
Stores the result of querying entire GNO token holders on both networks into files
`data/{network}-gno-holders.csv`
"""

from src.constants import SNAPSHOT_BLOCK_NUMBER
from src.dune_analytics import DuneAnalytics
from src.files import NetworkFile, HolderFiles
from src.models import GnoHolder
from src.utils.data import dump_results_and_index_by_account


def fetch_gno_holders(
        dune: DuneAnalytics,
        network: str,
        block_number: str,
        load_from: NetworkFile
) -> dict[str, GnoHolder]:
    """
    :param dune: open connection to dune analytics
    :param network: should be 'mainnet' or 'gchain'
    :param block_number: str representation of an integer ethereum block number
    :param load_from: File path to load existing data from
    :return: collection of gno holders balances on `network` at `block_number`
    """
    outfile = load_from.filename(network)
    try:
        return GnoHolder.load_from_file("GNO holders", load_file=outfile)
    except FileNotFoundError:
        print(f"file at {outfile.name} not found. Fetching from Dune")

    data_set = dune.fetch(
        query_filepath=f"./queries/{network}_holders.sql",
        network=network,
        name="GNO holders",
        parameters=[{"key": "BlockNumber", "type": "number", "value": block_number}]
    )
    results = sorted([
        GnoHolder(account=entry['account'], amount=entry['amount'])
        for entry in data_set
    ], key=lambda t: (-t.amount, t.account))
    return dump_results_and_index_by_account(
        file=outfile,
        results=results,
    )


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    for chain in ['mainnet', 'gchain']:
        fetch_gno_holders(
            dune_connection,
            chain,
            SNAPSHOT_BLOCK_NUMBER[chain],
            HolderFiles().gno_holders
        )
