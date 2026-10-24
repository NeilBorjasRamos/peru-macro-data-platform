with ranked as (
    select *,
        date_trunc('month', period)::date as month,
        row_number() over (
            partition by code, date_trunc('month', period)
            order by period desc
        ) as recency
    from {{ ref('stg_current_observations') }}
    -- Last daily non-null observation of its own month; never carry across months.
    where frequency = 'M' or value is not null
),
monthly as (
    select code, month, period as source_period, value, name, unit, observed_since
    from ranked
    where recency = 1
)
select current.*,
    current.code || ':' || current.month::text as monthly_id,
    case when current.unit not like 'percent%' and previous.value <> 0
        then 100 * (current.value / previous.value - 1) end as yoy_change_pct
from monthly current
left join monthly previous
  on previous.code = current.code
 and previous.month = (current.month - interval '1 year')::date
