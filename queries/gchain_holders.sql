-- For a permanent version of this query please visit: https://dune.xyz/queries/335121
-- This contract emits two Transfer events!
with

combined_transfers as (
    select evt_block_time,
           evt_block_number,
           "to",
           "from",
           value
    from gnosis_chain."GnosisToken_evt_Transfer"
    union all
    select evt_block_time,
           evt_block_number,
           "to",
           "from",
           value
    from gnosis_chain."GnosisToken_evt_Transfer0"
),

tally as (
    -- Incoming
    select evt_block_time,
           evt_block_number,
           "to" as account,
           value
    from combined_transfers
    union all
    -- Outgoing
    select evt_block_time,
           evt_block_number,
           "from"     as account,
           -1 * value as value
    from combined_transfers
),

balances as (
    select account,
           sum(value) as amount
    from tally
    where evt_block_number < '{{BlockNumber}}'
    group by account
)

select concat('0x', encode(account, 'hex')) as account,
       amount
from balances
where amount > 0
order by amount desc
