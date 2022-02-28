"""
Stores the resulting NFT metadata of CoW Citizens on both networks `out/citizens.json`
"""
from __future__ import annotations

import math

from src.dune_analytics import DuneAnalytics


def fetch_cow_citizens(
        dune: DuneAnalytics,
        investment_threshold: float = 0.8
) -> (list[dict], list[dict]):
    """
    Queries for investors and generates a
    :param dune: open connection to dune analytics
    :param investment_threshold: percentage of exercising dominant investment.
    :return: collection of metadata data related minting of CoW Citizen NFT on `network`
    """
    dune_citizens = []
    for network in ['mainnet', 'gchain']:
        citizens.extend(dune.fetch(
            query_filepath=f"./queries/{network}_citizens.sql",
            network=network,
            name="CoW Citizens",
            parameters=[
                {
                    "key": "InvestmentThreshold",
                    "type": "number",
                    "value": str(investment_threshold)
                }
            ]
        ))

    dune_citizens.sort(key=lambda t: t['claim_index'])
    # The following assertion implies that there was no collision of
    # claim_index after merging the two result files
    assert len(dune_citizens) == len(set(t['claim_index'] for t in dune_citizens))

    nft_metadata = []

    citizen_number_pad_length = math.ceil(math.log10(len(citizens)))
    for token_id, citizen in enumerate(dune_citizens):
        token = citizen['token']
        network = citizen['chain']
        description = f"CoW Citizen - " \
                      f"Early investor in the CoW Protocol with {token} on {network}"
        nft_metadata.append({
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

    return citizens, nft_metadata


if __name__ == "__main__":
    import json

    dune_connection = DuneAnalytics.new_from_environment()
    citizens, nfts = fetch_cow_citizens(dune_connection)
    print("Total Citizens", len(nfts))
    OUTFILE = './out/citizens.json'
    print(f"Writing to {OUTFILE}")
    with open(OUTFILE, 'w', encoding='utf-8') as f:
        json.dump(nfts, f, indent=2)
