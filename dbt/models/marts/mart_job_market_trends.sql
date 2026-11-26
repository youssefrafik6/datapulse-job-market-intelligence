with monthly as (
    select source, date_trunc('month', posted_date)::date as posting_month, role, count(*) as postings,
           count(*) filter(where remote='Remote') as remote_postings, count(annual_usd) as salary_sample
    from {{ ref('int_job_facts') }} where trend_eligible and posted_date is not null group by 1,2,3
), prior as (
    select *, lag(posting_month) over(partition by source, role order by posting_month) as previous_month,
           lag(postings) over(partition by source, role order by posting_month) as previous_count
    from monthly
)
select *, case when previous_month = posting_month - interval '1 month' then postings-previous_count end
    as month_over_month_change from prior
