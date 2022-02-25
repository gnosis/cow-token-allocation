"""
Stores the result of querying entire GNO token holders on both networks into a single file
`data/{network}-lp-holders.csv`
"""
import math
import pprint

from src.dune_analytics import DuneAnalytics


# from src.utils.data import write_to_csv


def fetch_cow_citizens(
        dune: DuneAnalytics,
        investment_threshold: float = 0.8
) -> list[dict]:
    """
    Queries for investors and generates a
    :param dune: open connection to dune analytics
    :param investment_threshold: percentage of exercising dominant investment.
    :return: collection of metadata data related minting of CoW Citizen NFT on `network`
    """
    mainnet_citizens = dune.fetch(
        query_filepath=f"./queries/mainnet_citizens.sql",
        network='mainnet',
        name="M-Citizens",
        parameters=[
            {
                "key": "InvestmentThreshold",
                "type": "number",
                "value": str(investment_threshold)
            }
        ]
    )

    gchain_citizens = dune.fetch(
        query_filepath=f"./queries/gchain_citizens.sql",
        network='gchain',
        name="G-Citizens",
        parameters=[
            {
                "key": "InvestmentThreshold",
                "type": "number",
                "value": str(investment_threshold)
            }
        ]
    )
    citizens = sorted(
        mainnet_citizens + gchain_citizens,
        key=lambda t: t['claim_index']
    )
    assert len(citizens) == len(set(t['claim_index'] for t in citizens))

    results = []

    num_citizens = math.ceil(math.log10(len(citizens)))
    for token_id, citizen in enumerate(citizens):
        token = citizen['token']
        network = citizen['chain']

        results.append({
            "id": token_id,
            "description": f"CoW Citizen - Early investor in the CoW Protocol with {token} on {network}",
            "external_url": "https://citizen.cow.fi/NFT/",
            "image": f"https://cowcitizen.netlify.app/NFT/{token_id}/{token_id}.gif",
            "name": "CoW Citizen - Early Investor",
            "attributes": [
                {
                    "trait_type": "Cow Citizen ID",
                    "value": str(token_id).zfill(num_citizens)
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

    return results


if __name__ == "__main__":
    import json
    dune_connection = DuneAnalytics.new_from_environment()
    citizens = fetch_cow_citizens(dune_connection)
    print("Total Citizens", len(citizens))
    filename = './out/citizens.json'
    print(f"Writing to {filename}")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(citizens, f)
