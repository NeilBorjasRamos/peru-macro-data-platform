select code, period, count(*) as versions_observed,
    min(valid_from) as first_observed_at,
    max(valid_from) as latest_change_observed_at
from {{ source('macro_raw', 'observation_history') }}
group by code, period
