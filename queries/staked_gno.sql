-- For a permanent version of this query please visit: https://dune.xyz/queries/330002
select concat('0x', encode("from", 'hex')) as depositor,
       count(*) * 10 ^ 18                  as staked_gno
from gnosis_chain."SBCDepositContract_evt_DepositEvent" d
         inner join xdai."transactions" t
                    on hash = evt_tx_hash
where evt_block_number < '{{BlockNumber}}'
group by "from"
order by staked_gno desc

