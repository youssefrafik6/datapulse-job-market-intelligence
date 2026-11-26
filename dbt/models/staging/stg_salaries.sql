select * from {{ source('operational', 'salary_records') }}
