import collections
import unittest

from src.utils.data import *

Account = collections.namedtuple('Account', 'account value')


class TestUtils(unittest.TestCase):
    def test_flatten_without_duplicates(self):
        self.assertEqual(
            flatten_without_duplicates([{'a', 'b'}, [1, 2]]),
            {'a', 'b', 1, 2}
        )
        self.assertEqual(
            flatten_without_duplicates([('a', 'b'), ['b', 'c'], {'c', 'd'}]),
            {'a', 'b', 'c', 'd'}
        )
        self.assertEqual(
            flatten_without_duplicates([['42'], '42']),
            {'42', '4', '2'}
        )

    def test_index_by_account(self):
        list_struct = [
            Account(account="0x1", value=1),
            Account(account="0x2", value=2),
        ]
        indexed_data = index_by_account(list_struct)
        for element in list_struct:
            self.assertEqual(element, indexed_data[element.account])

        # Duplicating an account key
        list_struct.append(Account(account="0x1", value=3))

        with self.assertRaises(IndexError):
            index_by_account(list_struct)

    def test_index_by_account_with_multiplicity(self):
        list_struct = [
            Account(
                account=f"number {i % 3}",  # Accounts may repeat
                value=i
            )
            for i in range(20)
        ]
        indexed_data = index_by_account_with_multiplicity(list_struct)
        self.assertEqual(len(indexed_data), 3)
        for account, data in indexed_data.items():
            self.assertEqual(
                len([x for x in list_struct if x.account == account]),
                len(data),
                "occurrences of same account must coincide length of transposed data"
            )


if __name__ == '__main__':
    unittest.main()
