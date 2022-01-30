from dataclasses import dataclass
from typing import Optional

from src.fetch.contracts import EvmAccountInfo
from src.files import File
from src.models import Account
from src.utils.file import write_to_csv


@dataclass
class NativeTransfer:
    receiver: str
    amount: float
    token_type: str = "native"
    token_address: Optional[str] = None
    id: Optional[int] = None


if __name__ == '__main__':
    transfers = []
    gchain_accounts = Account.load_from(
        load_file=File(name="allocations-gchain.csv", path="./"),
        column_name='Account',
    )
    null_balances = EvmAccountInfo(
        node_url='https://rpc.gnosischain.com/',
        addresses=[a.account for a in gchain_accounts],
        network='gchain'
    ).get_null_balances()
    print(f"Found {len(null_balances)} out of {len(gchain_accounts)} with null balance")
    for account in null_balances:
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
