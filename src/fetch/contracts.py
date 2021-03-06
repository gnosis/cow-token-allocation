"""
Single use EthRPC module for fetching code at address specified
and determining whether the address is a deployed smart contract.
"""
import argparse
import csv
from collections import defaultdict
from typing import Callable, TypeVar

import requests

from src.contract_bytecode import WALLET_BYTECODE, NOT_WALLET_BYTECODE, \
    UNVERIFIED_BYTECODE
from src.files import NetworkFile
from src.models import Account
from src.utils.data import File
from src.utils.file import write_to_csv

# pylint: disable=invalid-name
V = TypeVar('V', int, str)

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

    @staticmethod
    def load_from_file(file: File) -> set:
        """Loads results dict from a file containing known contract addresses"""
        print(f"loading contracts from {file.name}")
        with open(file.filename(), 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            return set(row['account'] for row in reader)


    def batch_call(
            self,
            addresses: list[str],
            func: Callable[[list[str]], dict[str, V]]
    ) -> dict[str, V]:
        print(f"making batch call for {len(addresses)} addresses on "
              f"{self.network} (this will take a while)...")
        results = {}
        for index in range(0, len(addresses), self.max_batch_size):
            partition = addresses[index:index + self.max_batch_size]
            results |= func(partition)
        return results

    def contracts(self, load_from: NetworkFile) -> set[str]:
        """
        Allows us to instantiate the code getter without actually fetching
        results are only fetched upon call to this method.
        """
        load_file = load_from.filename(self.network)
        if load_from is not None:
            try:
                return self.load_from_file(load_file)
            except FileNotFoundError:
                print(f"file at {load_file} not found. Fetching from Node")

        batch_results = self.batch_call(self.addresses, self._get_code_at)
        results = {
            account for account, code in batch_results.items()
            if code != "0x"
        }
        print(f"found {len(results)} contracts, writing to file")
        write_to_csv(
            data_list=sorted([Account(k) for k in results]),
            outfile=load_file
        )
        return results

    def get_non_wallets(self, contracts: set[str]) -> set[str]:
        code_at = self.batch_call(
            addresses=list(contracts),
            func=self._get_code_at
        )
        collector = defaultdict(list)
        for account, code in code_at.items():
            collector[code].append(account)

        wallets = set()
        for byte_code, accounts in collector.items():
            if byte_code in WALLET_BYTECODE | UNVERIFIED_BYTECODE:
                # Can't be certain if unverified code is a wallet, so assume it is.
                wallets |= set(accounts)
            elif byte_code in NOT_WALLET_BYTECODE:
                pass
            else:
                # We should never reach this!
                raise RuntimeError(
                    f"Unclassified Contract Bytecode:\n"
                    f"{byte_code}\n"
                    f"example address: {accounts[0]}"
                )

        print(f"found {len(wallets)} wallet contracts on {self.network}")
        return set(contracts) - wallets

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
    smart_contracts = contract_detector.contracts(NetworkFile("contracts.txt"))
    for address in args.addresses:
        print(f"is_contract({address}): {address in smart_contracts}")
