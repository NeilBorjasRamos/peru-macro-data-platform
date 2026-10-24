select h.code, h.period, h.value, h.valid_from as observed_since,
    s.name, s.frequency, s.unit, s.aggregation,
    h.code || ':' || h.period::text as observation_id
from {{ source('macro_raw', 'observation_history') }} h
join {{ source('macro_raw', 'series') }} s using(code)
where h.valid_to is null
