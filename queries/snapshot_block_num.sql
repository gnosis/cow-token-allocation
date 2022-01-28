-- All our holder queries use strict inequality on the block number,
-- so the snapshot block number is the first block occurring on Jan 10.
-- Existing Queries:
--     - mainnet: https://dune.xyz/queries/342025
--     - xdai: https://dune.xyz/queries/342109
select min("number") as snapshot_block
from {{network}}.blocks
where time > '2022-01-10'
