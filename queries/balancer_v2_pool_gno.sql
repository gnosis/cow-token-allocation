-- For a permanent version of this query please visit: https://dune.xyz/queries/379900
-- Cross checking this with the vault balance at https://dune.xyz/queries/336910
-- (search for 0xba12222222228d8ba445958a75a0704d566bf2c8)
with

add_removes as (
    select evt_block_number,
           "poolId"                                      as pool_id,
           unnest(tokens)                                as token,
           unnest(deltas) - unnest("protocolFeeAmounts") as delta
    from balancer_v2."Vault_evt_PoolBalanceChanged"
),

swap_ins as (
    select evt_block_number,
           "poolId"   as pool_id,
           "tokenIn"  as token,
           "amountIn" as delta
    from balancer_v2."Vault_evt_Swap"
),

swap_outs as (
    select evt_block_number,
           "poolId"         as pool_id,
           "tokenOut"       as token,
           -1 * "amountOut" as delta
    from balancer_v2."Vault_evt_Swap"
),

all_token_transfers as (
    select *
    from swap_ins
    union all
    select *
    from swap_outs
    union all
    select *
    from add_removes
),

pool_balances as (
    select pool_id,
           token,
           sum(delta) as gno_balance
    from all_token_transfers
    where evt_block_number < '{{BlockNumber}}'
      and token = '\x6810e776880c02933d47db1b9fc05908e5386b96'
    group by pool_id, token
),

pool_token_map as (
    select "poolAddress" as pool_address,
           "poolId"      as pool_id
    from balancer_v2."Vault_evt_PoolRegistered"
)

select concat('0x', encode(pool_address, 'hex')) as pool_address,
       gno_balance
from pool_balances pb
         join pool_token_map ptm
              on pb.pool_id = ptm.pool_id
