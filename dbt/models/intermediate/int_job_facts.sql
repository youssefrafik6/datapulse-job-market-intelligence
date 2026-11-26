select j.*, t.title, t.role, t.candidates, c.company, c.company_size,
       l.location, l.city, l.state, coalesce(l.nyc, false) as nyc, s.annual_low, s.annual_high,
       s.annual_usd, s.salary_origin, d.trend_eligible
from {{ ref('stg_job_postings') }} j
join {{ ref('stg_job_titles') }} t using(title_id)
join {{ ref('stg_data_sources') }} d using(source)
left join {{ ref('stg_companies') }} c using(company_id)
left join {{ ref('stg_locations') }} l using(location_id)
left join {{ ref('stg_salaries') }} s using(job_id)
