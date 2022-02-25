with
-- For a permanent version of this query please visit: https://dune.xyz/queries/453088
investment_claims as (
    select concat('0x', encode(claimant, 'hex'))   as claimant,
           sum(case when "claimType" = 1 then "claimedAmount" else 0 end)                                  as gno_option_claimed,
           sum(case when "claimType" = 2 then "claimedAmount" else 0 end)                                  as user_option_claimed,
           sum(case when "claimType" = 1 then "claimableAmount" end)                                       as claimable_gno_option,
           sum(case when "claimType" = 2 then "claimableAmount" end)                                       as claimable_user_option,
           -- claim indices are constructed of block_time * 10^5 + evt_index (giving a unique ordering on the time of investment)
           -- Note that event indices for this table are all strictly less than 10^5 (cf https://dune.xyz/queries/453401)
           sum(case when "claimType" = 1 then EXTRACT(EPOCH FROM evt_block_time) * 10 ^ 5 + evt_index end) as gno_claim_index,
           sum(case when "claimType" = 2 then EXTRACT(EPOCH FROM evt_block_time) * 10 ^ 5 + evt_index end) as user_claim_index
    from cow_protocol."CowProtocolVirtualToken_evt_Claimed"
    group by claimant
),

independent_investments_exercised as (
    select claimant,
           gno_claim_index,
           user_claim_index,
           case
               when claimable_gno_option is not null then gno_option_claimed / claimable_gno_option
           end                                                                                           as gno_option_exercised,
           case
               when claimable_user_option is not null then user_option_claimed / claimable_user_option
           end                                                                                           as user_option_exercised,
           case
               when greatest(gno_option_claimed, user_option_claimed) = gno_option_claimed then 'GNO'
               when greatest(gno_option_claimed, user_option_claimed) = user_option_claimed then 'xDAI'
           end                                                                                           as dominant_claim
    from investment_claims
    where gno_option_claimed + user_option_claimed > 0 --! Exclude all candidates who did not invest at all or were not eligible
),

exercised_investments as (
    select claimant,
           case
               when dominant_claim = 'GNO' then gno_option_exercised
               when dominant_claim = 'xDAI' then user_option_exercised
               end as investment_exercised,
           case
               when dominant_claim = 'GNO' then gno_claim_index
               when dominant_claim = 'xDAI' then user_claim_index
               end as claim_index,
           dominant_claim
    from independent_investments_exercised o
)

select claimant       as "wallet",
       claim_index,
       dominant_claim as token,
       'Gnosis Chain' as chain
from exercised_investments
where investment_exercised >= '{{InvestmentThreshold}}'
