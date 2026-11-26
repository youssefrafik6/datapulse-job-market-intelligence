select job_id
from {{ ref('int_job_facts') }}
where annual_usd is not null and
    (annual_usd <= 0 or salary_origin <> 'advertised'
     or annual_low > annual_usd or annual_high < annual_usd)
