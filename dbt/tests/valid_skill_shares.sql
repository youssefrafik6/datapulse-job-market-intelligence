select source, role, skill
from {{ ref('mart_skill_demand') }}
where posting_share <= 0 or posting_share > 1
