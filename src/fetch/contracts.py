"""
Single use EthRPC module for fetching code at address specified
and determining whether the address is a deployed smart contract.
"""
import argparse
from collections import defaultdict

import requests

from src.files import NetworkFile
from src.models import Account
from src.utils.data import File
from src.utils.file import write_to_csv


# pylint: disable=too-few-public-methods
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
        # TODO - could store the results of batch calls in the instance
        #  However this would require self.update_all whenever the addresses change.

    def _get_code_at(self, addresses: list[str]) -> dict[str, str]:
        """
        :return: map {address => byte_code_at_address}
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
                results[addresses[result_dict['id']]] = result_dict['result']
            except KeyError as err:
                raise IOError(
                    f"Request for code at address \"{addresses[result_dict['id']]}\" "
                    f"failed with response {result_dict}"
                ) from err
        return results

    def load_from_file(self, file: File) -> dict[str, bool]:
        """Loads results dict from a file containing known contract addresses"""
        print(f"loading contracts from {file.name}")
        with open(file.filename(), 'r', encoding='utf-8') as txt_file:
            contracts = set(txt_file.read().splitlines())
        return {addr: addr in contracts for addr in self.addresses}

    def batch_call(self, addresses: list[str], func):
        print(f"making batch call for {len(addresses)} addresses on "
              f"{self.network} (this will take a while)...")
        results = {}
        for index in range(0, len(addresses), self.max_batch_size):
            partition = addresses[index:index + self.max_batch_size]
            results |= func(partition)
        return results

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

        batch_results = self.batch_call(self.addresses, self._get_code_at)
        results = {
            account: code != "0x"
            for account, code in batch_results.items()
        }
        confirmed_contracts = sorted(
            [Account(k) for k, v in results.items() if v]
        )
        print(f"found {len(confirmed_contracts)} contracts, writing to file")
        write_to_csv(data_list=confirmed_contracts, outfile=load_file)
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
                account = addresses[result_dict['id']]
                results[account] = int(result_dict['result'], base=16)
            except KeyError as err:
                raise IOError(
                    f"Request for address \"{addresses[result_dict['id']]}\" "
                    f"failed with response {result_dict}"
                ) from err
        return results

    def get_null_balances(self, epsilon=10 ** 16) -> set[str]:
        results = self.batch_call(self.addresses, self._limited_balances)

        null_balances = sorted([Account(k) for k, v in results.items() if v < epsilon])
        print(f"found {len(null_balances)} accounts will zero balance, writing to file")
        balance_file = self.null_balance_file.filename(self.network)
        write_to_csv(data_list=null_balances, outfile=balance_file)
        return set(a.account for a in null_balances)


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
