-- 01. Top five skills per role and source (ties retained).
with mentions as (
    select j.source, j.role, s.skill, count(*) as n from jobs j join job_skills s using(job_id) group by 1,2,3
), ranks as (
    select *, dense_rank() over(partition by source,role order by n desc) as rank from mentions
)
select * from ranks where rank<=5 order by source, role, rank, skill;

-- 02. Median advertised salary by experience signal.
select source, experience, count(annual_usd) as sample,
    percentile_cont(.5) within group(order by annual_usd) as median_usd
from jobs where annual_usd is not null group by 1,2 order by 1,4 desc;

-- 03. Highest-paying role groups with at least 30 disclosed salaries.
with pay as (
    select source, role, count(*) as sample, percentile_cont(.5) within group(order by annual_usd) as median_usd
    from jobs where annual_usd is not null group by 1,2 having count(*)>=30
)
select *, rank() over(partition by source order by median_usd desc) as pay_rank from pay;

-- 04. Advertised salary by state.
select source, state, count(*) as sample, percentile_cont(.5) within group(order by annual_usd) as median_usd
from jobs where annual_usd is not null and state is not null group by 1,2 order by 1,3 desc;

-- 05. Remote share uses all role postings, including unspecified status.
select source, role, count(*) as sample, 1.0*count(*) filter(where remote='Remote')/count(*) as remote_share
from jobs group by 1,2 order by 1,4 desc;

-- 06. Skill frequency by state, relative to all state postings.
with totals as (select source,state,count(*) as n from jobs where state is not null group by 1,2)
select j.source,j.state,k.skill,count(*) as mentions,1.0*count(*)/max(t.n) as share
from jobs j join job_skills k using(job_id) join totals t using(source,state)
group by 1,2,3 order by 1,2,4 desc;

-- 07. Early-career mentions separated by evidence type.
select j.source,j.role,j.experience_evidence,k.skill,count(*) as mentions
from jobs j join job_skills k using(job_id)
where experience='Entry' or experience_evidence='early-career title signal'
group by 1,2,3,4 order by 1,2,3,5 desc;

-- 08. Salary association relative to the same source and role. Association is descriptive.
with baseline as (select source,role,avg(annual_usd) as role_mean_usd
    from jobs where annual_usd is not null group by 1,2)
select j.source,j.role,k.skill,count(*) as sample,avg(j.annual_usd) as mean_usd,
    avg(j.annual_usd)-max(b.role_mean_usd) as difference_vs_role_mean
from jobs j join job_skills k using(job_id) join baseline b using(source,role)
where annual_usd is not null group by 1,2,3 having count(*)>=30 order by 6 desc;

-- 09. Employer concentration per source, excluding missing employer labels.
with counts as (select source,company_id,min(company) as company,count(*) as postings
                from jobs where company_id is not null group by 1,2)
select *, 1.0*postings/sum(postings) over(partition by source) as source_share
from counts order by source,postings desc limit 100;

-- 10. Genuine posting-month counts for trend-eligible sources.
select source,cast(date_trunc('month',posted_date) as date) as month,count(*) as postings
from jobs where trend_eligible and posted_date is not null group by 1,2 order by 1,2;

-- 11. Skill co-occurrence with Jaccard overlap and a minimum count of 15.
with counts as (
    select j.source,k.skill,count(*) as n from jobs j join job_skills k using(job_id) group by 1,2
), pairs as (
    select j.source,a.skill as skill_a,b.skill as skill_b,count(*) as together
    from jobs j join job_skills a using(job_id) join job_skills b on a.job_id=b.job_id and a.skill<b.skill
    group by 1,2,3 having count(*)>=15
)
select p.*,1.0*together/(a.n+b.n-together) as jaccard from pairs p
join counts a on p.source=a.source and p.skill_a=a.skill
join counts b on p.source=b.source and p.skill_b=b.skill order by 5 desc limit 100;

-- 12. Salary coverage and distributions by source.
select source,count(*) as postings,count(annual_usd) as salary_sample,
    percentile_cont(.1) within group(order by annual_usd) as p10,
    percentile_cont(.25) within group(order by annual_usd) as p25,
    percentile_cont(.5) within group(order by annual_usd) as p50,
    percentile_cont(.75) within group(order by annual_usd) as p75,
    percentile_cont(.9) within group(order by annual_usd) as p90
from jobs group by 1;

-- 13. Exact recognized skill stacks, limited to jobs with more than one tracked skill.
with stacks as (
    select j.source,j.role,j.job_id,string_agg(k.skill,', ' order by k.skill) as stack
    from jobs j join job_skills k using(job_id) group by 1,2,3 having count(*)>1
)
select source,role,stack,count(*) as postings from stacks group by 1,2,3
order by 4 desc,1,2,3 limit 100;

-- 14. Mutually exclusive regional buckets. Remote is considered only outside the three named states.
with regions as (
    select source,role,case when nyc then 'NYC' when state='NY' then 'Other NY'
           when state='CT' then 'Connecticut' when state='MA' then 'Massachusetts'
           when remote='Remote' then 'Other remote U.S.' else 'Other U.S.' end as region
    from jobs
)
select source,region,role,count(*) as postings from regions group by 1,2,3 order by 1,2,4 desc;

-- 15. Coverage audit by source.
select source,count(*) as postings,count(*) filter(where quality_status='flagged') as flagged,
    count(state) as known_state,count(posted_date) as dated,count(annual_usd) as salary_covered,
    count(*) filter(where skill_evidence<>'none') as skill_covered
from jobs group by 1 order by 1;
