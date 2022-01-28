-- For a permanent version of this query please visit: https://dune.xyz/queries/330336
select concat('0x', encode(pool, 'hex')) as pool
from uniswap_v3."Factory_evt_PoolCreated"
where '\x6810e776880c02933d47db1b9fc05908e5386b96' in (token0, token1)
  and evt_block_number < '{{BlockNumber}}'
