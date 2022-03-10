from dataclasses import dataclass
from typing import Optional

from src.fetch.contracts import EvmAccountInfo
from src.files import File, NetworkFile
from src.models import Account
from src.utils.file import write_to_csv


@dataclass
class NativeTransfer:
    receiver: str
    amount: float
    token_type: str = "native"
    token_address: Optional[str] = None
    token_id: Optional[int] = None


if __name__ == '__main__':
    transfers = []
    gchain_accounts = Account.load_from(
        load_file=File(name="allocations-gchain.csv", path="./"),
        column_name='Account',
    )
    accounts = [a.account for a in gchain_accounts]
    account_info = EvmAccountInfo(
        node_url='https://rpc.gnosischain.com/',
        addresses=accounts,
        network='gchain'
    )
    null_balances = account_info.get_null_balances()
    print(f"Found {len(null_balances)} out of {len(gchain_accounts)} with null balance")
    account_info.addresses = null_balances
    contracts = account_info.contracts(load_from=NetworkFile("contracts.txt"))
    externally_owned_accounts = set(accounts) - contracts
    print(f"Creating transfer file with "
          f"{len(null_balances & externally_owned_accounts)} recipients")
    for account in null_balances & externally_owned_accounts:
        transfers.append(
            NativeTransfer(
                receiver=account,
                amount=0.1
            )
        )

    write_to_csv(
        data_list=transfers,
        outfile=File(name="gchain-transfers.csv")
    )
