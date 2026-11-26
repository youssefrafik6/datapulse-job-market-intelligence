select source, role, remote, count(*) as postings,
       count(*)::numeric / sum(count(*)) over(partition by source, role) as role_share
from {{ ref('int_job_facts') }} group by 1,2,3
