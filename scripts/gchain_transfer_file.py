from dataclasses import dataclass
from typing import Optional

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
    for account in gchain_accounts:
        transfers.append(
            NativeTransfer(
                receiver=account.account,
                amount=0.1
            )
        )

    write_to_csv(
        data_list=transfers,
        outfile=File(name="gchain-transfers.csv")
    )
