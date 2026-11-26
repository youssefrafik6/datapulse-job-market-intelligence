select source, role, experience, experience_evidence, count(*) as postings,
       count(annual_usd) as salary_sample,
       percentile_cont(0.5) within group(order by annual_usd) as median_usd
from {{ ref('int_job_facts') }} group by 1,2,3,4
