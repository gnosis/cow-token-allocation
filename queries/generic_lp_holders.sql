-- For a permanent versions of this query please visit
-- mainnet: https://dune.xyz/queries/346982
-- gchain:  https://dune.xyz/queries/343077
--
-- Works for generic pools such as HoneySwap, Swapr, SushiSwap, Symmetric & Balancer V2
-- (with and without staking).
-- Our definition of "generic" is essentially everything except UniV3. More concretely,
-- any platform in which the pool itself is also an ERC20 contract whose circulating
-- supply corresponds directly to the contract's token balance.
-- Use 0x for pools without staking.
------- Gnosis Chain
-- SWAPR
-- (0x5fCA4cBdC182e40aeFBCb91AFBDE7AD8d3Dc18a8, 0x)
-- (0xD7b118271B1B7d26C9e044Fc927CA31DccB22a5a, 0x9f2EFFE1a170c0E69D71D31fe6eD45B0daC8F978)
-- (0x70DD56a095df9E6735173A65B87e7c1A17Bc5ec2, 0x1627C902Aa93c938eb9F34143B262690f2C2Ef25)
-- SUSHI
-- (0x0f9d54d9ee044220a3925f9b97509811924fd269, 0xdDCbf776dF3dE60163066A5ddDF2277cB445E0F3)
-- (0x15f9eedeebd121fbb238a8a0cae38f4b4a07a585, 0x)
-- HONEY: More efficient query - https://dune.xyz/queries/334458
-- (0x321704900d52f44180068caa73778d5cd60695a6, 0x)
-- (0x28dbd35fd79f48bfa9444d330d14683e7101d817, 0x)
-- (0xac16c751f4c719a7ad54081a32ab0488b56f0ef4, 0x)
-- ELK: Seems to disagree by three accounts with - https://dune.xyz/queries/337770
-- (0x24a208cf21e043090b0dbec71f43f51f2fde7619, 0x5894386ba883c4b6c4a404fa64ea7471b8aede0c)
-- Symmetric
-- (0x53ed0c2c6bb944d9421528e1abd1e042b330696b,0x)
-- (0x34fa946a20e65cb1ac466275949ba382973fde2b,0x)
-------- Mainnet
-- Balancer V2
-- (0xf4c0dd9b82da36c07605df83c8a416f11724d88b, 0x)
-- (0x148ce9b50be946a96e94a4f5479b771bab9b1c59, 0x)
-- SushiSwap
-- (0x41328fdba556c8c969418ccccb077b7b8d932aa5, 0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd)
with

lp_transfers as (
    select evt_block_number, "to" as account, value as amount
    from erc20."ERC20_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
    union
    select evt_block_number, "from" as account, -1 * value as amount
    from erc20."ERC20_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
),

lp_holder_balances as (
    select account, sum(amount) as unstaked
    from lp_transfers
    where evt_block_number < '{{BlockNumber}}'
    group by account
),

unstaked_lp_holders as (
    select *
    from lp_holder_balances
    where account not in (
                          '\x0000000000000000000000000000000000000000', -- Zero Address
                          replace('{{StakingContract}}', '0x', '\x')::bytea
        )
),

staking_transfers as (
    select evt_block_number, "from" as account, value as amount
    from erc20."ERC20_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
      and "to" = replace('{{StakingContract}}', '0x', '\x')::bytea
    union
    select evt_block_number, "to" as account, -1 * value as amount
    from erc20."ERC20_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
      and "from" = replace('{{StakingContract}}', '0x', '\x')::bytea
),

pre_staked_balances as (
    select account, sum(amount) as staked
    from staking_transfers
    where evt_block_number < '{{BlockNumber}}'
    group by account
),

staked_lp_holders as (
    select account, staked
    from pre_staked_balances
),

results as (
    select coalesce(u.account, s.account) as account,
           coalesce(unstaked, 0)          as unstaked,
           coalesce(staked, 0)            as staked
    from unstaked_lp_holders u
             full outer join staked_lp_holders s
                             on u.account = s.account
)

select concat('0x', encode(account, 'hex')) as account,
       unstaked,
       staked,
       (unstaked + staked)                  as lp_balance
from results
where staked + unstaked != 0 -- Exclude those with 0 lp_balance
order by lp_balance desc
