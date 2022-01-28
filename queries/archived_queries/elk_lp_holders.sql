-- For a permanent version of this query please visit: https://dune.xyz/queries/337770
-- There is only one eligible Elk Pool so we hard code the staking contract for the following pool address.
-- Pool Address: 0x24a208cf21e043090b0dbec71f43f51f2fde7619
-- Staking Contract: 0x5894386ba883c4b6c4a404fa64ea7471b8aede0c
with

pool_constants (pool_address, staking_contract) as (
    values (decode('24a208cf21e043090b0dbec71f43f51f2fde7619', 'hex'),
            decode('5894386ba883c4b6c4a404fa64ea7471b8aede0c', 'hex'))
),

lp_transfers as (
    select evt_block_number, "to" as account, value
    from elk_finance."ElkPair_evt_Transfer"
    where contract_address = (select pool_address from pool_constants)
    union
    select evt_block_number, "from" as account, -1 * value
    from elk_finance."ElkPair_evt_Transfer"
    where contract_address = (select pool_address from pool_constants)
),

lp_holder_balances as (
    select account,
           sum(value) as unstaked_lp
    from lp_transfers
    where evt_block_number < '{{BlockNumber}}'
    group by account
),

lp_holder_unstaked as (
    select *
    from lp_holder_balances
    where unstaked_lp >= 0 -- Exclude Burned tokens (zero address)
      and account != (select staking_contract from pool_constants) --! Staking Contract.
),

staker_balances as (
    select evt_block_number, "from" as staker, amount / 10 ^ 18 as lp_staked
    from elf_finance."StakingRewards_evt_Staked"
             join xdai.transactions
                  on evt_tx_hash = hash
    union
    select evt_block_number, "from" as staker, -1 * amount / 10 ^ 18 as lp_staked
    from elf_finance."StakingRewards_evt_Withdrawn"
             join xdai.transactions
                  on evt_tx_hash = hash
),

lp_holder_staked as (
    select staker, sum(lp_staked) as staked_lp
    from staker_balances
    where evt_block_number < '{{BlockNumber}}'
    group by staker
),

results as (
    select account,
           unstaked_lp                                               as unstaked,
           case when staked_lp is not null then staked_lp else 0 end as staked
    from lp_holder_unstaked
             left outer join lp_holder_staked
                             on staker = account
)

select concat('0x', encode(account, 'hex')) as account,
       unstaked,
       staked,
       (unstaked + staked)                  as lp_balance
from results
where staked + unstaked > 0 -- Exclude those with 0 lp_balance
order by lp_balance desc
