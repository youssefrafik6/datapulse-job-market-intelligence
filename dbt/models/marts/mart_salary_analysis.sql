select source, role, experience, state, remote, count(*) as salary_sample,
       percentile_cont(0.1) within group(order by annual_usd) as p10_usd,
       percentile_cont(0.5) within group(order by annual_usd) as median_usd,
       percentile_cont(0.9) within group(order by annual_usd) as p90_usd
from {{ ref('int_job_facts') }}
where annual_usd is not null and salary_origin = 'advertised'
group by 1,2,3,4,5
