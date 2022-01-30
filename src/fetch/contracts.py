"""
Single use EthRPC module for fetching code at address specified
and determining whether the address is a deployed smart contract.
"""
import argparse

import requests

# pylint: disable=too-few-public-methods
from src.files import NetworkFile
from src.utils.data import File


class EvmAccountInfo:
    """
    Class consisting of 3 parameters to determine if the addresses are contracts.
    :param max_batch_size: max number of queries to batch into a single rpc call
    :param node_url: Ethereum node url (with api key)
    :param addresses: list of ethereum address (42 character hexadecimal string)
    """

    def __init__(
            self,
            node_url: str,
            addresses: list[str],
            network: str,
            max_batch_size: int = 1000
    ):
        self.max_batch_size = max_batch_size
        self.node_url = node_url
        self.network = network
        # de-duplicate to reduce unnecessary queries
        self.addresses = list(set(addresses))
        self.null_balance_file = NetworkFile("null-balances.csv")

    def _limited_is_contract(self, addresses: list[str]) -> dict[str, bool]:
        """
        :return: map {address => is_contract}
        Example:
        [
            '0x9008D19f58AAbD9eD0D60971565AA8510560ab41',
            '0xa4A6A282A7fC7F939e01D62D884355d79f5046C1',
        ] ->
        {
            '0x9008D19f58AAbD9eD0D60971565AA8510560ab41': True,
            '0xa4A6A282A7fC7F939e01D62D884355d79f5046C1': False,
        }
        """
        if len(addresses) > self.max_batch_size:
            size = len(addresses)
            raise RuntimeError(
                f"request batch too big ({size} > {self.max_batch_size})!"
                f" partition your list and try again"
            )
        request_data = []
        for index, eth_address in enumerate(addresses):
            request_data.append({
                "jsonrpc": "2.0",
                "method": "eth_getCode",
                "params": [eth_address, "latest"],
                "id": index
            })
        response = requests.post(self.node_url, json=request_data)
        results = {}
        for result_dict in response.json():
            try:
                results[addresses[result_dict['id']]] = result_dict['result'] != "0x"
            except KeyError as err:
                raise IOError(
                    f"Request for address \"{addresses[result_dict['id']]}\" "
                    f"failed with response {result_dict}"
                ) from err
        return results

    def load_from_file(self, file: File) -> dict[str, bool]:
        """Loads results dict from a file containing known contract addresses"""
        print(f"Loading Contracts from {file.name}")
        with open(file.filename(), 'r', encoding='utf-8') as txt_file:
            contracts = set(txt_file.read().splitlines())
        return {addr: addr in contracts for addr in self.addresses}

    def contracts(self, load_from: NetworkFile) -> dict[str, bool]:
        """
        Allows us to instantiate the code getter without actually fetching
        results are only fetched upon call to this method.
        """
        load_file = load_from.filename(self.network)
        if load_from is not None:
            try:
                return self.load_from_file(load_file)
            except FileNotFoundError:
                print(f"file at {load_from.name} not found. Fetching from Node")

        addresses = self.addresses
        print(f"Fetching code at {len(addresses)} addresses on "
              f"{self.network} (this will take a while)...")
        results = {}
        for index in range(0, len(addresses), self.max_batch_size):
            partition = addresses[index:index + self.max_batch_size]
            results |= self._limited_is_contract(partition)

        confirmed_contracts = sorted([k for k, v in results.items() if v])
        print(f"found {len(confirmed_contracts)} contracts, writing to file")
        with open(load_file.filename(), 'w', encoding='utf-8') as file:
            file.write('\n'.join(confirmed_contracts))
        return results

    def _limited_balances(self, addresses: list[str]) -> dict[str, int]:
        request_data = []
        for index, eth_address in enumerate(addresses):
            request_data.append({
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [eth_address, "latest"],
                "id": index
            })
        response = requests.post(self.node_url, json=request_data)
        results = {}
        for result_dict in response.json():
            try:
                results[addresses[result_dict['id']]] = int(result_dict['result'], base=16)
            except KeyError as err:
                raise IOError(
                    f"Request for address \"{addresses[result_dict['id']]}\" "
                    f"failed with response {result_dict}"
                ) from err
        return results

    def get_null_balances(self) -> set[str]:
        print(f"Fetching balances at {len(self.addresses)} addresses on "
              f"{self.network} (this may take a while)...")
        results = {}
        for index in range(0, len(self.addresses), self.max_batch_size):
            partition = self.addresses[index:index + self.max_batch_size]
            results |= self._limited_balances(partition)

        null_balances = sorted([k for k, v in results.items() if v == 0])
        print(f"found {len(null_balances)} accounts will zero balance, writing to file")
        balance_file = self.null_balance_file.filename(self.network).filename()
        with open(balance_file, 'w', encoding='utf-8') as file:
            file.write('\n'.join(null_balances))
        return set(null_balances)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Determine if ethereum address is a contract"
    )
    parser.add_argument(
        "--addresses",
        nargs="*",
        help="individual ethereum addresses",
        default=[]
    )
    parser.add_argument(
        "--node-url",
        type=str,
        help="URL (including api key) to an ethereum node",
    )
    parser.add_argument(
        "--request-batch-size",
        type=int,
        help="max number of requests to make at once",
        default=10
    )
    args = parser.parse_args()
    contract_detector = EvmAccountInfo(
        max_batch_size=args.request_batch_size,
        node_url=args.node_url,
        addresses=args.addresses,
        network="mainnet",
    )
    contract_dict = contract_detector.contracts(NetworkFile("contracts.txt"))
    for address, result in contract_dict.items():
        print(f"is_contract({address}): {result}")
