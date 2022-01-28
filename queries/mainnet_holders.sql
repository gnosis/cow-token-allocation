-- For a permanent version of this query please visit: https://dune.xyz/queries/336910
-- We tally up the incoming and outgoing transfers from each account.
with

sourced_transfers as (
    -- Incoming
    select evt_tx_hash,
           evt_block_time,
           evt_block_number,
           "to" as account,
           value
    from gnosis."GnosisToken_evt_Transfer"
    union all
    -- Outgoing
    select evt_tx_hash,
           evt_block_time,
           evt_block_number,
           "from"     as account,
           -1 * value as value
    from gnosis."GnosisToken_evt_Transfer"
),

balances as (
    select account,
           sum(value) as amount
    from sourced_transfers
    where evt_block_number < '{{BlockNumber}}'
    group by account
)

select concat('0x', encode(account, 'hex')) as account,
       amount
from balances
where amount > 0
order by amount desc
