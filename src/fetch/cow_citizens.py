"""
Stores the resulting NFT metadata of CoW Citizens on both networks `out/citizens.json`
"""
from __future__ import annotations

import json
import math

from web3 import Web3

from src.dune_analytics import DuneAnalytics


def fetch_cow_citizens(
        dune: DuneAnalytics,
        investment_threshold: float = 0.8
) -> (list[dict], list[dict]):
    """
    Queries for investors and generates a
    :param dune: open connection to dune analytics
    :param investment_threshold: percentage of exercising dominant investment.
    :return: collection of metadata related to minting of CoW Citizen NFT on `network`
    """
    dune_citizens = []
    query_file = "./queries/generic_citizens.sql"
    for network in ['mainnet', 'gchain']:
        dune_citizens.extend(dune.fetch(
            query_filepath=query_file,
            network=network,
            name="CoW Citizens",
            parameters=[
                {
                    "key": "InvestmentThreshold",
                    "type": "number",
                    "value": str(investment_threshold)
                },
                {
                    "key": "ChainName",
                    "type": "text",
                    "value": "Ethereum" if network == 'mainnet' else 'Gnosis Chain'
                },
                {
                    "key": "UserOptionToken",
                    "type": "text",
                    "value": "ETH" if network == 'mainnet' else 'xDAI'
                }
            ]
        ))

    dune_citizens.sort(key=lambda t: t['claim_index'])
    # The following assertion implies that there was no collision of
    # claim_index after merging the two result files
    assert len(dune_citizens) == len(set(t['claim_index'] for t in dune_citizens))

    citizens, nfts = [], []
    citizen_number_pad_length = math.ceil(math.log10(len(dune_citizens)))
    for token_id, citizen in enumerate(dune_citizens):
        token = citizen['token']
        network = citizen['chain']
        description = f"CoW Citizen - " \
                      f"Early investor in the CoW Protocol with {token} on {network}"
        citizens.append({
            "wallet": Web3.toChecksumAddress(citizen['wallet']),
            "tokenID": token_id,
        })
        nfts.append({
            "id": token_id,
            "description": description,
            "external_url": "https://citizen.cow.fi/NFT/",
            "image": f"https://cowcitizen.netlify.app/NFT/{token_id}/{token_id}.gif",
            "name": "CoW Citizen - Early Investor",
            "attributes": [
                {
                    "trait_type": "Cow Citizen ID",
                    "value": str(token_id).zfill(citizen_number_pad_length)
                },
                {
                    "trait_type": "Investment token",
                    "value": token
                },
                {
                    "trait_type": "Investment network",
                    "value": network
                }
            ]
        })

    citizen_outfile = './out/citizens.json'
    nft_outfile = './out/nfts.json'
    print(f"Writing Citizens to {citizen_outfile}")
    with open(citizen_outfile, 'w', encoding='utf-8') as file:
        json.dump(citizens, file, indent=2)

    print(f"Writing NFT metadata to {nft_outfile}")
    with open(nft_outfile, 'w', encoding='utf-8') as file:
        json.dump(nfts, file, indent=2)

    return citizens, nfts


if __name__ == "__main__":
    dune_connection = DuneAnalytics.new_from_environment()
    fetch_cow_citizens(dune_connection)
