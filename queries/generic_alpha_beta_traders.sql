-- For a permanent version of this query please visit:
-- mainnet: https://dune.xyz/queries/356227
-- gchain:  https://dune.xyz/queries/356237
with

alpha_traders as (
    select distinct(owner) as trader
    from gnosis_protocol_v2."GPv2Settlement_evt_Trade"
         -- This is the alpha contract address.
    where contract_address = '\x3328f5f2cecaf00a2443082b657cedeaf70bfaef'
      and evt_block_number < '{{BlockNumber}}'
),

beta_traders as (
    select distinct(owner) as trader
    from gnosis_protocol_v2."GPv2Settlement_evt_Trade"
         -- This is the officially released v1.0 contract address.
    where contract_address = '\x9008d19f58aabd9ed0d60971565aa8510560ab41'
      and evt_block_number < '{{BlockNumber}}'
)

select concat('0x', encode(trader, 'hex')) as trader
from (
    select *
    from alpha_traders
    intersect
    select *
    from beta_traders
) as _
