with mentions as (
    select j.source, j.role, j.job_id, k.skill from {{ ref('int_job_facts') }} j join {{ ref('stg_job_skills') }} k using(job_id)
), frequency as (
    select source, role, skill, count(*) as uses from mentions group by 1,2,3
), pairs as (
    select a.source, a.role, a.skill as skill_a, b.skill as skill_b, count(*) as together
    from mentions a join mentions b on a.job_id=b.job_id and a.skill<b.skill
    group by 1,2,3,4 having count(*) >= 5
)
select p.*, together::numeric/(a.uses+b.uses-together) as jaccard
from pairs p join frequency a on (p.source,p.role,p.skill_a)=(a.source,a.role,a.skill)
join frequency b on (p.source,p.role,p.skill_b)=(b.source,b.role,b.skill)
