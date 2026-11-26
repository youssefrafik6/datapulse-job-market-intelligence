with totals as (select source, role, count(*) as postings from {{ ref('int_job_facts') }} group by 1,2),
mentions as (select j.source, j.role, k.skill, count(*) as mentions from {{ ref('int_job_facts') }} j
             join {{ ref('stg_job_skills') }} k using(job_id) group by 1,2,3)
select m.*, t.postings, m.mentions::numeric/t.postings as posting_share,
       dense_rank() over(partition by m.source,m.role order by m.mentions desc) as skill_rank
from mentions m join totals t using(source, role)
