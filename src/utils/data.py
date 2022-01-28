"""
Generic utilities used throughout the project for opening, reading and writing files.
Also contains a few methods for data manipulation
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from src.files import File
from src.utils.file import write_to_csv


def dump_results_and_index_by_account(results: list, file: File) -> dict:
    """Combines logic of writing to csv and returning indexed data set"""
    write_to_csv(data_list=results, outfile=file)
    return index_by_account(results)


def index_by_account(data_list: list[Any]) -> dict[str, Any]:
    """
    :param data_list: list of Account structures (i.e. those having account field).
    :return: mapping of Account structures by account
    """
    results = {}
    for entry in data_list:
        if entry.account not in results:
            results[entry.account] = entry
        else:
            raise IndexError(f"Attempting to index by non-unique entry \"{entry}\"")
    return results


def index_by_account_with_multiplicity(
        data_list: list[Any]
) -> dict[str, list[Any]]:
    """
    :param data_list: list of Account structures (i.e. those having account field).
    :return: mapping { account => List[Account] } of Accounts having the same key
    """
    results = defaultdict(list)
    for entry in data_list:
        results[entry.account].append(entry)
    return results


def flatten_without_duplicates(iterables: list) -> set:
    """
    returns the collection of all unique elements in list (to depth of 1).
    :param iterables: list of anything which can be cast as set
    :return: set of all entries
    """
    results = set()
    for iterable in iterables:
        results = results.union(set(iterable))
    return results
