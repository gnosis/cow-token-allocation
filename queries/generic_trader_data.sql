-- For a permanent version of this query please visit:
-- mainnet: https://dune.xyz/queries/344411
-- gchain:  https://dune.xyz/queries/344484
-- In order to get block number, we join the trade view on settlement events.
with

trader_volume AS (
    select trader          as owner,
           min(block_time) as first_trade,
           max(block_time) as last_trade,
           sum(case
                   when buy_token_address in
                        (select contract_address from erc20.stablecoins)
                       and
                        sell_token_address in
                        (select contract_address from erc20.stablecoins)
                       then 0
                   else trade_value_usd
               end)        as non_stable_volume,
           sum(case
                   when buy_token_address in
                        (select contract_address from erc20.stablecoins)
                       and
                        sell_token_address in
                        (select contract_address from erc20.stablecoins)
                       then trade_value_usd
                   else 0
               end)        as stable_volume,
           count(*)        as num_trades
    from gnosis_protocol_v2."view_trades"
             join gnosis_protocol_v2."GPv2Settlement_evt_Settlement"
                  on tx_hash = evt_tx_hash
    where evt_block_number < '{{BlockNumber}}'
    group by owner
),

ranked_traders as (
    select concat('0x', encode(t.owner, 'hex'))       as trader,
           non_stable_volume,
           stable_volume,
           num_trades,
           date(first_trade) as first_trade,
           date(last_trade) as last_trade
    from trader_volume t
    where non_stable_volume + stable_volume > 0
)

select trader,
       (non_stable_volume + '{{StableFactor}}' * stable_volume)::numeric::integer as eligible_volume,
       num_trades,
       first_trade,
       last_trade
from ranked_traders
order by eligible_volume desc
