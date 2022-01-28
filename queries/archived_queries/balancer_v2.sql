-- For a permanent version of this query please visit: https://dune.xyz/queries/342439
-- There are only two relevant Balancer Pools involving GNO these are captured in the pool addresses constants here
--      GNO:WETH 0xf4c0dd9b82da36c07605df83c8a416f11724d88b
--      GNO:Mixed 0x148ce9b50be946a96e94a4f5479b771bab9b1c59
--      Please refer to Project README for more details
--      https://github.com/gnosis/cow-airdrop#liquidity-providers
with

lp_transfers as (
    select evt_block_number, "to" as account, value
    from balancer_v2."WeightedPool_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
    union
    select evt_block_number,
           "from" as account,
           -1 * value
    from balancer_v2."WeightedPool_evt_Transfer"
    where contract_address = replace('{{PoolAddress}}', '0x', '\x')::bytea
),

lp_holder_balances as (
    select account,
           sum(value) as lp_amount
    from lp_transfers
    where evt_block_number < '{{BlockNumber}}'
    group by account
)

select *
from lp_holder_balances
where lp_amount > 0
order by lp_amount desc
