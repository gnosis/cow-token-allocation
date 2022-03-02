import json

from src.dune_analytics import DuneAnalytics
from src.fetch.contracts import EvmAccountInfo
from src.fetch.cow_citizens import fetch_cow_citizens
from src.files import NetworkFile
# This import is fixed in https://github.com/gnosis/cow-token-allocation/pull/9
from src.split_allocation import NODE_URL


def split_citizens(citizens: list[dict]):
    network = 'mainnet'
    account_info = EvmAccountInfo(
        node_url=NODE_URL[network],
        # use lower() because the project uses lower case accounts (needs to be fixed!)
        addresses=[c['wallet'].lower() for c in citizens],
        network=network
    )
    contract_map = account_info.contracts(
        load_from=NetworkFile("checksum-contracts.txt")
    )
    num_citizens = len(citizens)
    mainnet_safes = []
    i = 0
    while i < len(citizens):
        if contract_map[citizens[i]['wallet'].lower()] is True:
            mainnet_safes.append(citizens.pop(i))
        i += 1

    assert num_citizens == len(mainnet_safes) + len(citizens)
    print(f"Found {len(mainnet_safes)} mainnet only citizens")
    mainnet_outfile = './out/mainnet-citizens.json'
    print(f"Writing Mainnet Citizens to {mainnet_outfile}")
    with open(mainnet_outfile, 'w', encoding='utf-8') as file:
        json.dump(mainnet_safes, file, indent=2)

    citizen_outfile = './out/citizens.json'
    print(f"Overwriting {citizen_outfile} without mainnet citizens")
    with open(citizen_outfile, 'w', encoding='utf-8') as file:
        json.dump(citizens, file, indent=2)


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    all_citizens, _ = fetch_cow_citizens(dune_connection)
    split_citizens(all_citizens)
