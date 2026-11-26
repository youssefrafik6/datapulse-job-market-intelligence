select * from {{ source('operational', 'data_sources') }}
