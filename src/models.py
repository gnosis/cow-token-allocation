"""Base Data Models used throughout the project"""
from __future__ import annotations

import csv
from dataclasses import dataclass

from src.utils.data import File


@dataclass
class Account:
    """Ethereum Account"""
    account: str

    def __init__(self, account: str):
        # TODO - replace with checksum address
        self.account = account.lower()

    def __hash__(self):
        return self.account.__hash__()

    @classmethod
    def load_from(cls, load_file: File, column_name: str = "account") -> set[Account]:
        """Loads Accounts from filename"""
        print(f"Loading Accounts from {load_file.name}")
        with open(load_file.filename(), 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            results = {
                Account(row[column_name]) for row in reader
            }
        print(f"Loaded {len(results)} {load_file.name} records")
        return results


@dataclass
class GnoHolder(Account):
    """Amount of GNO held by `account`"""
    amount: int

    def __init__(self, account: str, amount):
        Account.__init__(self, account)
        self.amount = int(amount)

    @classmethod
    def default(cls) -> GnoHolder:
        """Empty constructor"""
        return GnoHolder(account="", amount=0)

    @classmethod
    def load_from_file(cls, name: str, load_file: File) -> dict[str, GnoHolder]:
        """Loads Stakers from filename"""
        print(f"Loading {name} from {load_file.name}")
        with open(load_file.filename(), 'r', encoding='utf-8') as holder_file:
            reader = csv.DictReader(holder_file)
            results = {
                row['account']: GnoHolder(account=row['account'], amount=row['amount'])
                for row in reader
            }
        print(f"Loaded {len(results)} {name} records")
        return results


@dataclass
class Allocation(Account):
    """Allocation assigned to account"""
    amount: int

    def __init__(self, account: str, amount):
        Account.__init__(self, account)
        self.amount = int(amount)

    @classmethod
    def zero(cls, account: str) -> Allocation:
        """zero allocation for account"""
        return cls(account, "0")


class IndexedAllocations:
    """Data structure for the type dict[str, Allocation]"""

    def __init__(self, data: dict[str, Allocation]):
        self.data = data

    def __or__(self, other):
        inner = self.data | other.data
        return IndexedAllocations(inner)

    @classmethod
    def load_from_file(cls, file: File) -> IndexedAllocations:
        """
        :param file: file where allocations are stored
        :return: allocations indexed by account
        """
        allocations = {}
        with open(file.filename(), 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            row_count = 0
            for row in reader:
                row_count += 1
                account = row['account']
                allocations[account] = Allocation(
                    account=account,
                    amount=row['amount'],
                )

        # No duplicate entries!
        assert row_count == len(allocations), "Duplicate allocation record!"
        return cls(allocations)

    def keys(self):
        """returns inner dict keys"""
        return self.data.keys()

    def get(self, key: str):
        """same as dict.get, returning default on KeyError"""
        return self.data.get(key, Allocation.zero(key))

    def values(self):
        return self.data.values()
