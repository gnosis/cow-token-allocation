"""
BalancerV2 is unlike generic Defi Protocols where the pool token contains
the corresponding assets. This script fetches individual pool balances by general
accounting of events emitted by the Balancer Vault.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass

from src.dune_analytics import DuneAnalytics
from src.utils.data import File, write_to_csv


@dataclass
class BalancerPool:
    """GNO balance corresponding to the Balancer v2 pool at `pool_address`"""
    pool_address: str
    gno_balance: int

    @classmethod
    def load_from(cls, load_file: File) -> list[BalancerPool]:
        """Loads Accounts from filename"""
        print(f"Loading Balancer Pools from {load_file.name}")
        with open(load_file.filename(), 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            results = [
                BalancerPool(
                    pool_address=row['pool_address'],
                    gno_balance=int(row['gno_balance'])
                ) for row in reader
            ]
        print(f"Loaded {len(results)} {load_file.name} records")
        return results


def balancer_gno(
        dune: DuneAnalytics,
        block_number: str,
        load_from: File
) -> list[BalancerPool]:
    """
    Queries Dune Analytics for GNO balance of Balancer V2 Pools at`block_number`
    :return: list of balancer pools with non-zero GNO balance.
    """
    try:
        return BalancerPool.load_from(load_from)
    except FileNotFoundError:
        print(f"File at {load_from.name} not found, fetching from Dune")

    data_set = dune.fetch(
        query_filepath="./queries/balancer_v2_pool_gno.sql",
        network='mainnet',
        name="Balancer Pool GNO",
        parameters=[
            {
                "key": "BlockNumber",
                "type": "number",
                "value": block_number,
            },
        ])
    results = [
        BalancerPool(
            pool_address=entry['pool_address'],
            gno_balance=entry['gno_balance']
        ) for entry in data_set
    ]
    results.sort(key=lambda t: (t.pool_address, -t.gno_balance))
    write_to_csv(
        data_list=results,
        outfile=load_from
    )
    return results
