# Table of Contents

1. [Introduction](#introduction)
2. [Allocations](#allocations)
    1. [Allocation Splitting](#allocation-splitting)
3. [GNO Holders](#gno-token-holders)
    1. [Mainnet](#mainnet)
        1. [Raw Balances](#mainnet-holders)
        2. [Liquidity Providers](#mainnet-liquidity-providers)
    2. [Gnosis Chain](#gnosis-chain)
        1. [Raw Balances](#gnosis-chain-holders)
        2. [Liquidity Providers](#gnosis-chain-liquidity-providers)
        3. [Staked GNO](#staked-gno)
4. [CowSwap Users](#cowswap-users)
    1. [Primary Trader Allocation](#primary-trader-allocation)
    2. [Consolation Trader Allocation](#consolation-trader-allocation)
    3. [Community Allocation](#community)
5. [Dev Guide: Installation and Usage](#dev-guide-installation--usage)

# Introduction

This repository contains a collection of scripts and tools used to fetch deterministic
dataset pertaining to CoW Token airdrop. According to the announcement in
this [Gnosis Forum Post](https://forum.gnosis.io/t/gno-utility-and-value-proposition/2344)
the airdrop will be made to GNO holders on Mainnet and Gnosis Chain (formerly xDai)
including consideration of the following liquidity pools:

- Balancer V2 (Mainnet)
- Uniswap V3 (Mainnet)
- HoneySwap (Gnosis Chain)
- Symmetric (Gnosis Chain)
- SushiSwap (Gnosis Chain)
- Elk (Gnosis Chain)
- Swapr (Gnosis Chain)

Note that all our holder queries use strict inequality on the block number, so the
snapshot block number is the first block occurring on Jan 10. These
are [13974427](https://dune.xyz/queries/342025) on mainnet
and [20024195](https://dune.xyz/queries/342109) on gnosis chain. Relevant
query [here](./queries/snapshot_block_num.sql).

Note that we have excluded pools within these protocols containing a total of < 1 GNO
and user accounts having a GNO balance < 0.1 at the time of the snapshot.

To, briefly summarize the approach we;

1. Fetch Mainnet & Gnosis Chain GNO Token Holders at specific block
2. Fetch LP holders (specifically % of the total supply they own)
3. Fetch UniswapV3 Holders (specifically how much GNO)
4. Fetch Gnosis Chain Depositors
5. Compute GNO holdings of LP providers based on share % in correspondence with the
   Pool's holdings (from step 1)
6. Combine all of these values together to generate combined (Mainnet and GnosisChain
   CSV) representing total GNO holdings across all eligible platforms.
7. Fetch and merge trader data from both networks
8. Filter the combined Trader data by the eligibility criteria
   outlined [below](#cowswap-users)
9. Transform the holder and user data into allocations in their respective categories.
10. Merge allocations into a combined, universal allocation list.
11. The allocations are then split across both networks based loosely on the criteria
    that Allocations with an Airdrop claim less than 10K vCoW tokens will be eligible
    for claim on Gnosis Chain. Above 10K claims are on Mainnet. Note that we can only
    perform this splitting criteria to Externally owned accounts (since smart contracts
    such as Gnosis Safe are not "multi-network compatible").
12. As a final step, we append Advisor, Investor and Team allocations to the bottom of
    the mainnet allocation file.

Resulting allocation files have the following columns:

```
[ Account | Airdrop | GnoOption | UserOption | Investor | Team | Advisor ]
```

The allocation files are committed to this repo and can be viewed here:

- [Mainnet Allocations](allocations-mainnet.csv)
- [Gnosis Chain Allocations](allocations-gchain.csv)

# Allocations

An Allocation (represented in the project as a `MerkleLeaf`), attributed to each
eligible account, consists of several categories briefly define here (some of which will
be elaborated upon in their own section):

1. Airdrop: Consists of the combined sum of allocations for GNO holders and CoWSwap
   Users (outlined below)
2. GNO Option: Constructed from GNO holder data. Represents amount of vCoW that can be
   purchased with GNO.
3. User Option: Constructed from Primary Trader data (a sub-category of CoWSwap Users).
   Represents amount of vCoW that can be purchased with ETH/XDAI. Note that while 45M
   tokens we allocated for primary trader airdrop, 50M were allocated to the user option
   with different weight factors for each trading volume tier.
4. Investor: Represents amount of vCoW that can be purchased with USDC
5. Team: Represents a 4 year linearly vested entitlement of tokens for team members.
6. Advisor: Allocation attributed to advisors.

Each of the last 3 categories were appended to the end of mainnet allocation file after
all the holder and user data was compiled.

## Allocation Splitting

Allocations were split over two networks (Mainnet and Gnosis Chain) based on the
following criteria:

1. Mainnet Allocation:
   allocation >= `ALLOCATION_SPLIT`
2. Gnosis Chain:
   allocation < `ALLOCATION_SPLIT`

where `ALLOCATION_SPLIT = 10K token units`

Additionally, since externally owned accounts are cross-network compatible, but smart
contracts (such as Gnosis Safe) are not, we have to investigate this for each account.

Accounts which are contracts on only one of the two networks will receive their
allocation on the network they exist (regardless of allocation split).

Accounts which are contracts on both networks are treated as a "special case"
we collect this list and parse through all the accounts from the data files generated
throughout the program and partition them by network of eligibility.

If the account is exclusively eligible for allocation on one of the two networks the
allocation is given there.

There was only one case of a Gnosis Safe contract on both networks that was eligible for
allocation on both networks:

This is a Safe on both networks with an overlapping set of owner accounts (beyond the
signing threshold of 2)

- [mainnet](https://blockscout.com/xdai/mainnet/address/0x365bd827c68D5DE0e2BFA5871dc0ECaAf074d5Ab/read-proxy)
- [gchain](https://etherscan.io/address/0x365bd827c68d5de0e2bfa5871dc0ecaaf074d5ab#readProxyContract)

The total allocations to each category are

```
======================
Allocation Counts
   Mainnet:       1470
   Gnosis Chain: 42568
----------------------
Category Totals
   Airdrop:     150.0M
   GNO Option:   50.0M
   User Option:  50.0M
   Investor:    100.0M
   Advisory:    106.1M
   Team:         99.3M
----------------------
Grand Total:    555.3M
======================
```

# GNO Token Holders

## Mainnet

### Mainnet Holders

The goal of this snapshot is to deterministically and reproducibly fetch the GNO token
holders on both networks at a specific time. For this we use Dune
Analytics `erc20.view_token_balances_daily` table on Mainnet.

For reference, non-deterministic (i.e. current) token balances on each network can be
found
on [Etherscan](https://etherscan.io/token/0x6810e776880c02933d47db1b9fc05908e5386b96#balances)
.

Deterministically,

[Mainnet Holders Query Jan 10, 2022](https://dune.xyz/queries/336910)

which returns csv with columns `[ account | amount ]`.

Query [here](/queries/mainnet_holders.sql)

### Mainnet Liquidity Providers

1. **Balancer v2:** `https://app.balancer.fi/#/pool/<PoolId>`
    - [GNO/ETH:0xf4c0dd9b82da36c07605df83c8a416f11724d88b000200000000000000000026](https://app.balancer.fi/#/pool/0xf4c0dd9b82da36c07605df83c8a416f11724d88b000200000000000000000026)
        - [holders](https://etherscan.io/token/0xf4c0dd9b82da36c07605df83c8a416f11724d88b#balances)
        - [Deterministic Holders](https://dune.xyz/queries/330799?PoolAddress=0xf4c0dd9b82da36c07605df83c8a416f11724d88b)
    - [GNO/MIXED:0x148ce9b50be946a96e94a4f5479b771bab9b1c59000100000000000000000054](https://app.balancer.fi/#/pool/0x148ce9b50be946a96e94a4f5479b771bab9b1c59000100000000000000000054)
        - [holders](https://etherscan.io/token/0x148ce9b50be946a96e94a4f5479b771bab9b1c59#balances)
        - [Deterministic Holders](https://dune.xyz/queries/330799?PoolAddress=0x148ce9b50be946a96e94a4f5479b771bab9b1c59)

The query for balancer holders is also in this repo
at [./queries/generic_lp_holders.sql](./queries/generic_lp_holders.sql).

For an account of the GNO balances corresponding to each Balancer Pool at the time of
the snapshot, please visit [here](https://dune.xyz/queries/379900).

2. **Uniswap v3:** `https://info.uniswap.org/#/pools/<PoolAddress>`
    - [Pools Involving GNO](https://dune.xyz/queries/330336)
      with [query](./queries/uniswapv3_eligible_pools.sql)
    - [GNO/WETH(0.3%):0xf56d08221b5942c428acc5de8f78489a97fc5599](https://etherscan.io/token/0xf56d08221b5942c428acc5de8f78489a97fc5599)
    - [GNO:WETH(1%):0xa46466ad5507be77ff5abdc27df9dfeda9bd7aee](https://etherscan.io/token/0xa46466ad5507be77ff5abdc27df9dfeda9bd7aee)
    - [GNO:STAKE](https://info.uniswap.org/#/pools/0x7b24f3f2c6fc51ca67c91bcdfeb07bc75249fd1d)

For current individual pool positions visit `https://app.uniswap.org/#/pool/<TokenId>`

Deterministically, GNO balances corresponding to holder positions were computed using
their [SubGraph](https://thegraph.com/hosted-service/subgraph/uniswap/uniswap-v3)
along with code [here](./src/fetch/univ3_gno.py) adapted from their SDK.

3. **SushiSwap:** `https://analytics.sushi.com/pairs/<PoolAddress>`
    - [GNO/ETH:0x41328fdba556c8c969418ccccb077b7b8d932aa5](https://analytics.sushi.com/pairs/0x41328fdba556c8c969418ccccb077b7b8d932aa5)
        - [holders](https://etherscan.io/token/0x41328fdba556c8c969418ccccb077b7b8d932aa5#balances)
        - [Deterministic Holders](https://dune.xyz/queries/330799?PoolAddress=0x41328fdba556c8c969418ccccb077b7b8d932aa5)

## Gnosis Chain

### Gnosis Chain Holders

The balances view does not exist in Dune on `gnosischain`, so we rely on event
accounting of the token contract available in the `gnosis.GnosisToken` table.

[Gnosis Chain](https://blockscout.com/xdai/mainnet/token/0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb/token-holders)

The Gnosis Chain Holders can also be retrieved in JSON format via the
Blockscout [API Request](https://blockscout.com/xdai/mainnet/api?module=token&action=getTokenHolders&contractaddress=0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb&page=1&offset=10000)

Deterministically, this [Gnosis Chain Holders Query](https://dune.xyz/queries/335121)
will become "static" as of the snapshot date. The query is also available within this
repo at [/queries/gchain_holders.sql](/queries/gchain_holders.sql)

### Gnosis Chain Liquidity Providers

A [complete query](/queries/gchain_pools.sql) for all eligible liquidity sources on
Gnosis Chain. This is also available in [Dune](https://dune.xyz/queries/337740), but
only those with GNO balance > 1 at the time of snapshot are considered eligible.

1. **HoneySwap:** `https://info.honeyswap.org/#/pair/<PoolAddress>`
    - [Pairs involving GNO](https://dune.xyz/queries/334572)
    - [GNO/xDai:0x321704900d52f44180068caa73778d5cd60695a6](https://info.honeyswap.org/#/pair/0x321704900d52f44180068caa73778d5cd60695a6)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x321704900D52F44180068cAA73778d5cD60695A6/token-holders)
        - [Snapshot](https://dune.xyz/queries/334458?PoolAddress=0x321704900d52f44180068caa73778d5cd60695a6)
    - [GNO/WETH](https://info.honeyswap.org/#/pair/0x28dbd35fd79f48bfa9444d330d14683e7101d817)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x28dbd35fd79f48bfa9444d330d14683e7101d817/token-holders)
        - [Snapshot](https://dune.xyz/queries/334458?PoolAddress=0x28dbd35fd79f48bfa9444d330d14683e7101d817)
    - [GNO/CURVE](https://info.honeyswap.org/#/pair/0xac16c751f4C719a7ad54081A32AB0488B56F0ef4)
        - [holders](https://blockscout.com/xdai/mainnet/token/0xac16c751f4C719a7ad54081A32AB0488B56F0ef4/token-holders)
        - [Snapshot](https://dune.xyz/queries/334458?PoolAddress=0xac16c751f4C719a7ad54081A32AB0488B56F0ef4)

2. **Symmetric:** `https://xdai-pools.symmetric.exchange/#/pool/<PoolAddress>`
    - [GNO/SYM:0x53ed0c2c6bb944d9421528e1abd1e042b330696b](https://xdai-pools.symmetric.exchange/#/pool/0x53ed0c2c6bb944d9421528e1abd1e042b330696b)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x53ED0C2C6bB944D9421528E1ABD1e042B330696b/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x53ED0C2C6bB944D9421528E1ABD1e042B330696b&StakingContract=0x)
    - [GNO/AGVE:0x34fa946a20e65cb1ac466275949ba382973fde2b](https://xdai-pools.symmetric.exchange/#/pool/0x34fa946a20e65cb1ac466275949ba382973fde2b)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x34fa946a20e65cb1ac466275949ba382973fde2b/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x34fa946a20e65cb1ac466275949ba382973fde2b&StakingContract=0x)
    - [GNO/OTHERS](https://xdai-pools.symmetric.exchange/#/pool/0xa0bec22a7db3a401b782117ae34d725475626fe9)

3. **SushiSwap:** `https://analytics-xdai.sushi.com/pairs/<PoolAddress>`
    - [GNO/xDai:0x0f9d54d9ee044220a3925f9b97509811924fd269](https://analytics-xdai.sushi.com/pairs/0x0f9d54d9ee044220a3925f9b97509811924fd269)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x0f9d54d9ee044220a3925f9b97509811924fd269/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x0f9d54d9ee044220a3925f9b97509811924fd269&StakingContract=0xdDCbf776dF3dE60163066A5ddDF2277cB445E0F3)
    - [GNO/WETH:0x15f9eedeebd121fbb238a8a0cae38f4b4a07a585](https://analytics-xdai.sushi.com/pairs/0x15f9eedeebd121fbb238a8a0cae38f4b4a07a585)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x15f9eedeebd121fbb238a8a0cae38f4b4a07a585/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x15f9eedeebd121fbb238a8a0cae38f4b4a07a585&StakingContract=0x)
    - **Excluded Pools (< 1 GNO)**
        - [GNO/USDC](https://analytics-xdai.sushi.com/pairs/0xe9ad744f00f9c3c2458271b7b9f30cce36b74776)
        - [GNO/STAKE](https://analytics-xdai.sushi.com/pairs/0xdc3c9ff23305d7020ea50bb3ba334b2ff750b30d)
        - [GNO/CURVE](https://analytics-xdai.sushi.com/pairs/0xd77c13d58fc67da84f3b440ce42a802d905ec6a0)

4. **Elk:** `https://xdai-info.elk.finance/pair/<PoolAddress>`

    - [GNO/ELK:0x24a208cf21e043090b0dbec71f43f51f2fde7619](https://xdai-info.elk.finance/pair/0x24a208cf21e043090b0dbec71f43f51f2fde7619)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x24a208cf21e043090b0dbec71f43f51f2fde7619/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x24a208cf21e043090b0dbec71f43f51f2fde7619&StakingContract=0x5894386ba883c4b6c4a404fa64ea7471b8aede0c)
    - **Excluded Pool**
        - [GNO/xDai](https://xdai-info.elk.finance/pair/0x969f959731a8851cd0f4ef8e8fc9376091814100)

5. **Swapr:** `https://dxstats.eth.link/#/pair/<PoolAddress>`

    - [GNO/WETH:0x5fCA4cBdC182e40aeFBCb91AFBDE7AD8d3Dc18a8](https://dxstats.eth.link/#/pair/0x5fCA4cBdC182e40aeFBCb91AFBDE7AD8d3Dc18a8)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x5fCA4cBdC182e40aeFBCb91AFBDE7AD8d3Dc18a8/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x5fCA4cBdC182e40aeFBCb91AFBDE7AD8d3Dc18a8&StakingContract=0x)
    - [GNO/xDAI:0xd7b118271b1b7d26c9e044fc927ca31dccb22a5a](https://dxstats.eth.link/#/pair/0xd7b118271b1b7d26c9e044fc927ca31dccb22a5a)
        - [holders](https://blockscout.com/xdai/mainnet/token/0xd7b118271b1b7d26c9e044fc927ca31dccb22a5a/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0xd7b118271b1b7d26c9e044fc927ca31dccb22a5a&StakingContract=0x9f2EFFE1a170c0E69D71D31fe6eD45B0daC8F978)
    - [GNO/STAKE:0x70dd56a095df9e6735173a65b87e7c1a17bc5ec2](https://dxstats.eth.link/#/pair/0x70dd56a095df9e6735173a65b87e7c1a17bc5ec2)
        - [holders](https://blockscout.com/xdai/mainnet/token/0x70dd56a095df9e6735173a65b87e7c1a17bc5ec2/token-holders)
        - [Snapshot](https://dune.xyz/queries/343077?PoolAddress=0x70dd56a095df9e6735173a65b87e7c1a17bc5ec2&StakingContract=0x1627C902Aa93c938eb9F34143B262690f2C2Ef25)

### Staked GNO

The set of depositors and number of deposits (up until the snapshot deadline) are
fetched via Dune
Analytics [https://dune.xyz/queries/330002](https://dune.xyz/queries/330002) and in this
repo [./queries/staked_gno.sql](./queries/staked_gno.sql). Note that the number of
deposits corresponds directly to the integer number of GNO staked.

# CowSwap Users

The funds allocated to users make a combined total of 50M tokens (5% of the supply).
This allocation has been split up into three categories:

1. Primary Trader: users (a.k.a. traders) satisfying _all_ of the criteria outlined
   below
2. Consolation Trader: users who were not eligible for primary allocation, but do
   satisfy the eligible volume criteria below
3. Community: This category includes both of POAP holders and a special allocation to
   our alpha contract traders.

The 50M tokens has been partitioned as (44M, 3M, 3M) into each of the above three
categories respectively.

We elaborate on each of the three categories in their own sections below.

Users, aka those who have traded on the platform, are entitled to an airdrop based on
the following parameters:

1. **Eligible Trading Volume:** A weighted sum of the total USD value of all non-stable
   and stable trades. Everyone who has a total of at least `V` is considered.
   Concretely, that
   is ```eligible_volume = non_stable_volume + StableFactor * stable_volume```
   where `stable_volume` is the trading volume for trades between stable coins
   and `non_stable_volume` is the volume of all others.

2. **Stable Factor** A factor `S` used to lower the weight of stable to stable trading
   volume

3. **Number of Trades:** All users having made at least `T` trades.

4. **Days Between:** All users having traded at least `D` apart.

## Primary Trader Allocation

Users satisfying _all_ of the above criteria have been included in this list.

The parameters used for primary allocation both networks are

```
V - 1000 USD
S - 0.1
T - 3 trades
D - 14 days between first and last trade
```

The primary trading allocation has been distributed to users with weight factors
according to the following eligible volume tiers

| Tier |   Eligible Volume   | Weight Factor |
|------|:-------------------:|--------------:|
| 5    |       \>= 1M        |            28 |
| 4    |  \>= 500K and < 1M  |            16 |
| 3    | \>= 100K and < 500K |             8 |
| 2    | \>= 50K  and < 100K |             4 |
| 1    | \>= 10K  and < 50K  |             3 |
| 0    | \>= 1K   and < 10K  |             1 |

Please refer to
[src/constants.py](https://github.com/gnosis/cow-airdrop/blob/93a9e9c2f5e10834522ded8a62f61312319ecc2d/src/constants.py#L24-L42)
where all of these parameters are defined in the code.

## Consolation Trader Allocation

Users not meeting the Primary criteria, but satisfying either

1. The eligible volume condition (i.e. at least 1000 USD in eligible trading volume) OR
2. Having made at least 5 trades.

There are no weight factors assigned to this category, the 3M tokens has been
distributed equally to each of the eligible recipients.

### Trader Data Queries

The Dune query used for both networks is available in this repo
at [./queries/generic_trader_data.sql](./queries/generic_trader_data.sql). For
convenience, the permanent fixtures for each network are also available in the Dune
interface at

- mainnet: [https://dune.xyz/queries/344411](https://dune.xyz/queries/344411)
- gchain: [https://dune.xyz/queries/344484](https://dune.xyz/queries/344484)

## Community

1. Retained Alpha Traders: Anyone who traded on **both** the alpha (unaudited) version
   of the contract, and the version 1 deployment. The weight factor attributed to this
   category (for each network) is outlined along with POAP holders in the table below
   Dune Query for this is [here](queries/generic_alpha_beta_traders.sql) and a permanent
   version is available at

- mainnet: [https://dune.xyz/queries/356227](https://dune.xyz/queries/356227)
- gchain:  [https://dune.xyz/queries/356237](https://dune.xyz/queries/356237)

2. POAP Holders: The following table outlines the considered POAPs for this allocation
   along with their weight factors

For a full list of POAP weight factors
see [here](./data/poap-holders/token-categories.csv).

| Event                                                         |                                                                                                      Token ID(s)                                                                                                       | Weight Factor |
|---------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|--------------:|
| Kaffeekränzchen low attendance                                |    [4437](data/poap-holders/token-4437.csv), [4813](data/poap-holders/token-4813.csv), [5182](data/poap-holders/token-5182.csv), [6457](data/poap-holders/token-6457.csv), [6887](data/poap-holders/token-6887.csv)    |             4 |
| Kaffeekränzchen medium attendance                             |                                                                   [7330](data/poap-holders/token-7330.csv), [8092](data/poap-holders/token-8092.csv)                                                                   |             2 |
| Kaffeekränzchen high attendance                               |                                                                                        [8824](data/poap-holders/token-8824.csv)                                                                                        |             1 |
| Kaffeekränzchen challenge winners                             |                     [13346](data/poap-holders/token-13346.csv), [15296](data/poap-holders/token-15296.csv), [15739](data/poap-holders/token-15739.csv), [21839](data/poap-holders/token-21839.csv)                     |            20 |
| UX Research Participants                                      |                                                                                       [11743](data/poap-holders/token-11743.csv)                                                                                       |            40 |
| Squid                                                         |                                                                                       [15311](data/poap-holders/token-15311.csv)                                                                                       |            20 |
| CowStars                                                      | [6739](data/poap-holders/token-6739.csv), [9533](data/poap-holders/token-9533.csv), [12654](data/poap-holders/token-12654.csv), [18465](data/poap-holders/token-18465.csv), [22201](data/poap-holders/token-22201.csv) |           100 |
| SCdeploymentMainnet                                           |                                                                                        [6102](data/poap-holders/token-6102.csv)                                                                                        |             2 |
| SCdeploymentGnoChain                                          |                                                                                        [6103](data/poap-holders/token-6103.csv)                                                                                        |             2 |
| Picasso Winners                                               |                                                                                       [12420](data/poap-holders/token-12420.csv)                                                                                       |           100 |
| [AlphaUsersRetainedMainnet](https://dune.xyz/queries/356227)  |                                                                                                          N/A                                                                                                           |            16 |
| [AlphaUsersRetainedGnoChain](https://dune.xyz/queries/356237) |                                                                                                          N/A                                                                                                           |             4 |

Unfortunately, due to an exploit in the POAP.xyz we were not able to automatically
recover the correct POAP token holders, so we have fallen back on our own, internal,
hard coded list of eligible token recipients.

For further details on the dates and names of specific event tokens please refer to our
token data files [here](data/poap-holders/token-categories.csv)

# Dev Guide: Installation & Usage

```shell
python3 -m venv env
source ./env/bin/activate
pip install -r requirements.txt
cp .env.sample .env
source .env
```

Fill out your Dune credentials in the `.env` file. The Dune user and password are
straight-forward login credentials to Dune Analytics. The `DUNE_QUERY_ID` is an integer
id found in the URL of a query when saved in the Dune interface. This should be created
beforehand, but the same query id can be used everywhere throughout the program (as long
as it is owned by the account corresponding to the user credentials provided).

The other necessary environment variable is `NODE_URL`. This should be the entire URL
with API key. Something like

```shell
NODE_URL = https://mainnet.infura.io/v3/XXXYOURXXXXXXAPIXXXXXXKEYXXXXXXX
```

To generate the entire allocation from scratch run

```shell
python -m src.main
```

**NOTE** Entire allocation generation from scratch takes about 15 minutes.

_DISCLAIMER_ Due to reliance on a non-deterministic price feed in the trader query we
are experiencing infinitesimal difference from one run to the next. While the results
will turn out marginally different the allocation files are not yet deterministic. We
are working toward fixing this, but will rely on the committed file here at the time of
deployment even if this non-determinism has not been resolved.

### Verifying results

If you generate the output files yourself, you can compare the output files with:

```shell
$ diff out/allocations-mainnet.csv allocations-mainnet.csv 
$ diff out/allocations-gchain.csv allocations-gchain.csv 
```

Note that every file in this repo runs as a standalone script for its intended purpose.
For example, to fetch GNO token holders run

```shell
python -m src.fetch.gno_holders
```

or to generate sub allocations (e.g. `holder`, `poap`, `trader`) run

```shell
python -m src.generate.{name}_allocation
```

This program writes files to CSV as it goes. By default, data is loaded from file when
available.

This will write two files into the `data/` directory. Namely

```
mainnet-gno-holders.csv
gchain-gno-holders.csv
```

To fetch LP token holder results run

```shell
python -m src.fetch_lp_holders
```

which will result in files `./out/{network}-lp-holders.csv`.
