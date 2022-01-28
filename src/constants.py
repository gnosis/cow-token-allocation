"""
Reading and parsing Environment variables as global constants.
"""
import os

from enum import Enum

# Defaults here are the first blocks published on Jan 10, 2022 (UTC)
SNAPSHOT_BLOCK_NUMBER = {
    'mainnet': os.environ.get('SNAPSHOT_BLOCK_MAINNET', "13974427"),
    'gchain': os.environ.get('SNAPSHOT_BLOCK_XDAI', "20024195"),
}

FILE_OUT_PATH = os.environ.get('FILE_OUT_PATH', './out')

# Lowest total balance of GNO to be considered eligible for allocation
MIN_GNO = pow(10, 17)

GNO_TOKEN = {
    'mainnet': "0x6810e776880c02933d47db1b9fc05908e5386b96",
    'gchain': "0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb"
}

MILL = pow(10, 6)
WEI_IN_ETH = pow(10, 18)
TEN_PERCENT = 100 * MILL * WEI_IN_ETH

USER_ALLOCATION = {
    'primary': 44 * MILL * WEI_IN_ETH,
    'consolation': 3 * MILL * WEI_IN_ETH,
    'POAP': 3 * MILL * WEI_IN_ETH,
}

GNO_HOLDER_ALLOCATION = 50 * MILL * WEI_IN_ETH
USER_OPTION_SUPPLY = sum(USER_ALLOCATION.values())
ADVISOR_ALLOCATION = 6077382 * WEI_IN_ETH
GNOSIS_DAO_ALLOCATION = TEN_PERCENT
FOUNDING_TEAM_ALLOCATION = 99255952 * WEI_IN_ETH
FUTURE_HIRES_ALLOCATION = 150 * MILL * WEI_IN_ETH - FOUNDING_TEAM_ALLOCATION


class DistributionType(Enum):
    """These are distribution types according to the field in MerkleLeaf"""
    AIRDROP = "Airdrop"
    GNO_OPTION = "Gno Option"
    USER_OPTION = "User Option"
    TEAM = "Team Allocation"
    INVESTOR = "Investor Option"
    ADVISOR = "Advisor Option"


# These are the Distribution categories according to the GIP-13 Forum Post
# https://forum.gnosis.io/t/gip-13-phase-2-cowdao-and-cow-token/2735
TEAM_SHARE = {  # 15%
    DistributionType.ADVISOR: FUTURE_HIRES_ALLOCATION,
    DistributionType.TEAM: FOUNDING_TEAM_ALLOCATION,
}

GNOSIS_DAO_SHARE = {  # 10%
    DistributionType.AIRDROP: GNOSIS_DAO_ALLOCATION // 2,  # Karpatkey Airdrop
    DistributionType.ADVISOR: GNOSIS_DAO_ALLOCATION // 2,  # Vested Unstoppable
}

COWMUNITY_INVESTMENT = {  # 10%
    DistributionType.USER_OPTION: USER_OPTION_SUPPLY,
    DistributionType.GNO_OPTION: GNO_HOLDER_ALLOCATION,
}

COWMUNITY_AIRDROP = {  # 10%
    # Airdrop total is the community investment option total
    DistributionType.AIRDROP: USER_OPTION_SUPPLY + GNO_HOLDER_ALLOCATION
}

COW_ADVISORY = {  # 0.533333333333333%
    DistributionType.ADVISOR: 5333333333333330000000000
}

ANONYMOUS_INVESTMENTS = 1333333333333330000000000
INVESTMENT_ROUND = {  # 10%
    DistributionType.INVESTOR: 100 * MILL * WEI_IN_ETH - ANONYMOUS_INVESTMENTS,
    DistributionType.USER_OPTION: ANONYMOUS_INVESTMENTS
}

assert sum(INVESTMENT_ROUND.values()) == TEN_PERCENT
assert sum(COWMUNITY_INVESTMENT.values()) == TEN_PERCENT
assert sum(GNOSIS_DAO_SHARE.values()) == TEN_PERCENT
assert sum(COWMUNITY_AIRDROP.values()) == TEN_PERCENT
assert sum(TEAM_SHARE.values()) == 150 * MILL * WEI_IN_ETH

ENTIRE_ALLOCATION = [  # 55.533333333333333% of supply
    INVESTMENT_ROUND,  # 10%
    COW_ADVISORY,  # 0.533333333333333%
    COWMUNITY_AIRDROP,  # 10%
    COWMUNITY_INVESTMENT,  # 10%
    GNOSIS_DAO_SHARE,  # 10%
    TEAM_SHARE,  # 15%
]

EXPECTED_TOTAL = 555333333333333330000000000
ALLOCATED_TOTAL = sum(sum(pie_slice.values()) for pie_slice in ENTIRE_ALLOCATION)
assert ALLOCATED_TOTAL == EXPECTED_TOTAL

VOLUME_TIERS = [10 ** 3, 10 ** 4, 5 * 10 ** 4, 10 ** 5, 5 * 10 ** 5, 10 ** 6]
TRADING_TIER_FACTORS = {
    0: 1,
    1: 3,
    2: 4,
    3: 8,
    4: 16,
    5: 28
}
USER_OPTION_TIER_FACTORS = {
    0: 1,
    1: 2,
    2: 5,
    3: 10,
    4: 16,
    5: 24
}
