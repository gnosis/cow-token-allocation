-- For a permanent version of this query please visit: https://dune.xyz/queries/337740
-- Pool Pairs are fetching from respective protocol contracts (except symmetric which is hard coded at the moment)
with

elk_finance_pairs as (
    select 'Elk Finance' as protocol, pair, evt_block_number
    from elk_finance."ElkFactory_evt_PairCreated"
    where '\x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb' in (token0, token1)
),

honeyswap_pairs as (
    select 'HoneySwap' as protocol, pair, evt_block_number
    from honeyswap_v2."UniswapV2Factory_evt_PairCreated"
    where '\x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb' in (token0, token1)
),

sushiswap_pairs as (
    select 'Sushiswap' as protocol, pair, evt_block_number
    from sushiswap."UniswapV2Factory_evt_PairCreated"
    where '\x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb' in (token0, token1)
),

swapr_pairs as (
    select 'Swapr' as protocol, pair, evt_block_number
    from swapr."DXswapFactory_evt_PairCreated"
    where '\x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb' in (token0, token1)
),

fetched_pairs as (
    select *
    from elk_finance_pairs
    union
    select *
    from honeyswap_pairs
    union
    select *
    from sushiswap_pairs
    union
    select *
    from swapr_pairs
),

-- TODO: if the contracts are ever indexed use them here.
symmetric_pools (protocol, pair) as (
    values ('Symmetric',
            decode('53ed0c2c6bb944d9421528e1abd1e042b330696b', 'hex')),
           ('Symmetric',
            decode('34fa946a20e65cb1ac466275949ba382973fde2b', 'hex')),
           ('Symmetric', decode('a0bec22a7db3a401b782117ae34d725475626fe9', 'hex'))
),

all_pairs as (
    select protocol, pair
    from fetched_pairs
    where evt_block_number < '{{BlockNumber}}'
    union
    select *
    from symmetric_pools
)

select protocol,
       concat('0x', encode(pair, 'hex')) as pool_address
from all_pairs
order by protocol
