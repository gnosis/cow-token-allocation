-- For a permanent version of this query please visit: https://dune.xyz/queries/334458
-- Mint and Burn methods emit Transfer Events so they need not be considered.
with

incomming_transfers as (
    select evt_block_time, "to" as account, value
    from honeyswap_v2."UniswapV2Pair_evt_Transfer"
    where contract_address = REPLACE('{{PoolAddress}}', '0x', '\x')::bytea
),

outgoing_transfers as (
    select evt_block_time, "from" as account, -1 * value
    from honeyswap_v2."UniswapV2Pair_evt_Transfer"
    where contract_address = REPLACE('{{PoolAddress}}', '0x', '\x')::bytea
),

tally as (
    select *
    from incomming_transfers
    union
    select *
    from outgoing_transfers
),

results as (
    select account, sum(value) as amount
    from tally
    where evt_block_time < '{{Date}}'
    group by account
)

select *
from results
where amount > 0 --! Exclude burn address and former holders who have exited.
order by amount desc
