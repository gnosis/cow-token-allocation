"""
Stores the result of querying entire GNO token holders on both networks into a single file
`data/{network}-lp-holders.csv`
"""

from src.constants import SNAPSHOT_BLOCK_NUMBER
from src.dune_analytics import DuneAnalytics
from src.files import NetworkFile, AllocationFiles
from src.models import Account
from src.utils.data import write_to_csv


def fetch_alpha_traders(
        dune: DuneAnalytics,
        network: str,
        block_number: str,
        load_from: NetworkFile,
) -> set[Account]:
    """
    :param dune: open connection to dune analytics
    :param block_number: str representation of an integer ethereum block number
    :param network: 'gchain' or 'mainnet'
    :param load_from: base file to load from, note that network is prepended to the filename
    :return: collection of Trader accounts who have used both versions of the contract.
    """
    outfile = load_from.filename(network)
    try:
        return Account.load_from(outfile)
    except FileNotFoundError:
        print(f"File at {outfile.name} not found, fetching from Dune")

    data_set = dune.fetch(
        query_filepath="./queries/generic_alpha_beta_traders.sql",
        network=network,
        name="Alpha Traders",
        parameters=[{"key": "BlockNumber", "type": "number", "value": block_number}]
    )
    results = sorted([
        Account(entry['trader']) for entry in data_set
    ], key=lambda t: t.account)
    write_to_csv(data_list=results, outfile=outfile)
    return set(results)


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    for chain in ['mainnet', 'gchain']:
        alphas = fetch_alpha_traders(
            dune_connection,
            network=chain,
            block_number=SNAPSHOT_BLOCK_NUMBER[chain],
            load_from=AllocationFiles().alpha_traders
        )
        print(alphas)
