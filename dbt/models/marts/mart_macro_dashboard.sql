select month,
    max(value) filter(where code='PN38705PM') as cpi_index,
    max(value) filter(where code='PN01271PM') as inflation_mom_pct,
    max(value) filter(where code='PN01273PM') as inflation_yoy_pct,
    max(value) filter(where code='PN01207PM') as exchange_pen_usd,
    max(value) filter(where code='PN01770AM') as gdp_index,
    max(yoy_change_pct) filter(where code='PN01770AM') as gdp_yoy_pct,
    max(value) filter(where code='PN01652XM') as copper_us_cents_lb,
    max(value) filter(where code='PN01654XM') as gold_usd_troy_ounce,
    max(value) filter(where code='PD12301MD') as policy_rate_eom_pct,
    max(value) filter(where code='PD12301MD')
      - max(value) filter(where code='PN01273PM') as policy_minus_inflation_pp
from {{ ref('fct_monthly_observations') }}
group by month
