select source, state, nyc, role, count(*) as postings,
       count(*) filter(where remote='Remote') as remote_postings,
       count(annual_usd) as salary_sample
from {{ ref('int_job_facts') }} where state is not null group by 1,2,3,4
