select
  (select count(*) from {{ ref('stg_current_observations') }}) as staged_count,
  (select count(*) from {{ source('macro_raw','observation_history') }} where valid_to is null) as raw_count
where
  (select count(*) from {{ ref('stg_current_observations') }}) <>
  (select count(*) from {{ source('macro_raw','observation_history') }} where valid_to is null)
