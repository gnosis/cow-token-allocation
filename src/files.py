from __future__ import annotations

import csv
import os
from dataclasses import dataclass

from src.constants import FILE_OUT_PATH


@dataclass
class File:
    """Simple structure for declaring and passing around filenames"""
    name: str
    path: str = FILE_OUT_PATH

    def filename(self) -> str:
        """Returns the complete path to file"""
        return os.path.join(self.path, self.name)

    def __str__(self):
        return self.filename()

    def get_accounts_from(self) -> set[str]:
        """
        Fetches accounts column from a given data filename.
        """
        accounts = set()
        with open(self.filename(), 'r', encoding='utf-8') as csv_file:
            dict_reader = csv.DictReader(csv_file)
            for row in dict_reader:
                accounts.add(row['account'])
        return accounts


# TODO - this should really extend and override file,
#  but I need to figure out how to do it right
@dataclass
class NetworkFile:
    name: str
    path: str = FILE_OUT_PATH

    def filename(self, network: str) -> File:
        return File(name=f"{network}-{self.name}", path=self.path)


@dataclass
class OptionsFiles:
    team = File(name='allocations_team.csv', path='./data/')
    investor = File(name='allocations_investor.csv', path='./data/')
    anon = File(name='allocations_anon_investor.csv', path='./data/')
    advisor = File(name='allocations_advisor.csv', path='./data/')
    airdrop = File(name='allocations_daughter_safe.csv', path='./data/')


@dataclass
class HolderFiles:
    univ3_holders = File("mainnet-univ3-holders.csv")
    gno_holders = NetworkFile("gno-holders.csv")
    lp_holders = NetworkFile("lp-holders.csv")
    stakers = File("gchain-gno-stakers.csv")
    balancer_pools = File("mainnet-balancer-gno.csv")
    combined = File("combined-holders.csv")
    network_master = NetworkFile("holders-master.csv")


@dataclass
class TraderFiles:
    """Data structure for different file paths related to trader allocations and data"""
    primary_allocation = File("allocations-trader-primary.csv")
    consolation_allocation = File("allocations-trader-consolation.csv")
    consolation_trader = File("combined-consolation-trader-data.csv")
    primary_trader = File("combined-primary-trader-data.csv")
    traders = NetworkFile("trader-data.csv", path='./data')
    user_options = File("combined-user-options.csv")


@dataclass
class AllocationFiles:
    """Data structure containing file paths for all allocation types"""
    merkle_leaf = File("allocations.csv")
    mainnet_allocation = File("allocations-mainnet.csv")
    gchain_allocation = File("allocations-gchain.csv")
    poap_allocations = File("allocations-poap.csv")
    holder_allocation = File("allocations-holder.csv")
    trader_data: TraderFiles = TraderFiles()
    holder_data: HolderFiles = HolderFiles()
    poap_categories = File(name="token-categories.csv", path="./data/poap-holders/")
    alpha_traders = NetworkFile("alpha-traders.csv")
    contracts = NetworkFile("contracts.txt")

    def load_all_network_accounts(self, network: str) -> set[str]:
        """
        Loads the set of all accounts from all output files per network
        """
        # TODO - probably need to do POAP accounts too -
        #   its unclear what network they should be:
        #   Will have to see if any of them are NOT traders and perhaps add
        #   them to extra special cases.
        network_files = [
            self.alpha_traders,
            self.holder_data.network_master,
            self.trader_data.traders,
        ]
        network_accounts = set()
        for file in network_files:
            network_accounts |= file.filename(network).get_accounts_from()
        if network == 'mainnet':
            network_accounts |= self.holder_data.univ3_holders.get_accounts_from()
        if network == 'gchain':
            network_accounts |= self.holder_data.stakers.get_accounts_from()
        print(f"loaded {len(network_accounts)} {network} accounts")
        return network_accounts
