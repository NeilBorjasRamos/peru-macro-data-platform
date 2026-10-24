select a.code,a.period
from {{ source('macro_raw','observation_history') }} a
join {{ source('macro_raw','observation_history') }} b
  on a.code=b.code and a.period=b.period and a.valid_from<b.valid_from
where a.valid_to is null or b.valid_from<a.valid_to
