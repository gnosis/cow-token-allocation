"""
A simple use case of the [Blockscout API](https://blockscout.com/xdai/mainnet/api-docs)
"""
import os
import sys

import requests

BASE_URL = 'https://blockscout.com/xdai/mainnet/api'


def fetch_holders(token) -> list[dict]:
    """
    :param: token - the ethereum address of an erc20 token
    returns: a list of {token} holders taking the form { 'address': str, value: int }
    Note that values returned are in WEI.
    """
    offset = 5000
    page = 1
    query_parameters = {
        'module': 'token',
        'action': 'getTokenHolders',
        'contractaddress': token,
        'page': page,
        'offset': offset,
    }
    if os.environ['BLOCKSCOUT_API_KEY']:
        query_parameters['apikey'] = os.environ['BLOCKSCOUT_API_KEY']
    print(f"Querying Blockscout API for {token} holders...")
    results = []
    while True:
        response = requests.get(BASE_URL, params=query_parameters)
        if not response.ok:
            sys.exit(f"Failed Request with status code {response.status_code}")

        new_content = response.json()['result']
        results += new_content
        if len(new_content) < offset:
            # We have fetched the last page!
            print("Blockscout query complete!")
            return results
        query_parameters['page'] += 1
