select * from {{ source('operational', 'job_postings') }}
