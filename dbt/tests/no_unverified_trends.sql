select t.source
from {{ ref('mart_job_market_trends') }} t
join {{ ref('stg_data_sources') }} s using(source)
where not s.trend_eligible
