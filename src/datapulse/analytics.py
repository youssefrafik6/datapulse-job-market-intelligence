"""Query the normalized store with bounded filters shared by both interfaces."""
from dataclasses import dataclass
from datetime import date

from datapulse.store import query

GROUPS = {"role", "title", "experience", "state", "company_size", "remote", "company", "location"}


@dataclass
class Filters:
    source: str | None = None
    role: str | None = None
    experience: str | None = None
    state: str | None = None
    remote: str | None = None
    start: date | None = None
    end: date | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    salary_floor: int | None = None
    skill: str | None = None
    region: str | None = None
    early: bool = False

    def sql(self):
        predicates = []
        args = {}
        for field in ("source", "role", "experience", "state", "remote"):
            value = getattr(self, field)
            if value:
                predicates.append(f"j.{field} = :{field}")
                args[field] = value
        for field in ("title", "company", "location"):
            value = getattr(self, field)
            if value:
                predicates.append(f"strpos(lower(j.{field}), :{field}) > 0")
                args[field] = value.lower()
        for field, condition in {
            "start": "j.posted_date >= :start", "end": "j.posted_date <= :end",
            "salary_floor": "j.annual_usd >= :salary_floor",
            "skill": "exists(select 1 from job_skills fs where fs.job_id=j.job_id and fs.skill=:skill)",
        }.items():
            value = getattr(self, field)
            if value is not None:
                predicates.append(condition)
                args[field] = value
        if self.region == "New York City":
            predicates.append("j.nyc")
        if self.region == "Remote U.S.":
            predicates.append("j.remote = 'Remote'")
        if self.early:
            predicates.append("(j.experience = 'Entry' or j.experience_evidence = 'early-career title signal')")
        return " and ".join(predicates) or "true", args


@dataclass
class Analytics:
    filters: Filters
    path: object = None

    def run(self, sql, **extra):
        condition, args = self.filters.sql()
        return query(f"with cohort as (select j.* from jobs j where {condition}) {sql}",
                     {**args, **extra}, self.path)

    def summary(self):
        return self.run("""
            select count(*) as postings, count(distinct company_id) as companies,
            count(distinct location_id) as locations, count(distinct state) as states,
            count(*) filter(where remote='Remote') as remote_jobs,
            count(annual_usd) filter(where salary_origin='advertised') as salary_jobs, min(posted_date) as first_posted,
            max(posted_date) as last_posted, max(last_observed_at) as last_observed,
            max(ingested_at) as last_ingested from cohort""")

    def breakdown(self, key, limit=20):
        if key not in GROUPS:
            raise ValueError("Unsupported dimension")
        return self.run(f"""select {key} as segment, count(*) as postings from cohort
                            where {key} is not null group by 1 order by 2 desc, 1 limit :lim""", lim=limit)

    def salary(self, key, limit=30):
        if key not in GROUPS:
            raise ValueError("Unsupported dimension")
        return self.run(f"""select {key} as segment, count(*) as sample,
                            percentile_cont(0.1) within group(order by annual_usd) as p10,
                            percentile_cont(0.5) within group(order by annual_usd) as median,
                            percentile_cont(0.9) within group(order by annual_usd) as p90,
                            min(annual_low) as lowest_advertised, max(annual_high) as highest_advertised
                            from cohort where salary_origin='advertised' and annual_usd is not null
                            and {key} is not null
                            group by 1 order by 2 desc, 1 limit :lim""", lim=limit)

    def salary_sample(self):
        return self.run("""select role, experience, annual_usd from cohort
                           where salary_origin='advertised' and annual_usd is not null
                           order by md5(job_id), job_id limit 10000""")

    def skill_demand(self, group="role", limit=25, skill=None):
        if group not in {*GROUPS, "salary_band"}:
            raise ValueError("Unsupported skill dimension")
        segment = ("case when annual_usd < 100000 then 'Under $100k' "
                   "when annual_usd < 150000 then '$100k–$149k' when annual_usd is not null then '$150k+' end"
                   if group == "salary_band" else group)
        return self.run(f""", segments as (select job_id, {segment} as segment from cohort),
            counts as (select segment, count(*) as sample from segments group by 1),
            mentions as (select s.segment, k.skill, count(*) as mentions from segments s
                         join job_skills k on s.job_id=k.job_id
                         where (:chosen='' or k.skill=:chosen) group by 1,2)
            select m.*, c.sample, 1.0*m.mentions/c.sample as share from mentions m
            join counts c on m.segment=c.segment order by mentions desc, segment, skill limit :lim""",
                        chosen=skill or "", lim=limit)

    def skills(self, limit=20):
        return self.run("""select s.skill, count(*) as mentions,
                          1.0*count(*)/(select count(*) from cohort) as share
                          from cohort j join job_skills s on j.job_id=s.job_id group by 1
                          order by 2 desc, 1 limit :lim""", lim=limit)

    def pairs(self, limit=40, min_support=5):
        return self.run(""", mentions as (
              select s.skill, s.job_id from job_skills s join cohort j on j.job_id=s.job_id
            ), frequencies as (select skill, count(*) as n from mentions group by 1),
            pairs as (select a.skill as skill_a, b.skill as skill_b, count(*) as together
                      from mentions a join mentions b on a.job_id=b.job_id and a.skill<b.skill
                      group by 1,2 having count(*) >= :support)
            select p.*, 1.0*together/(a.n+b.n-together) as jaccard,
                1.0*together*(select count(*) from cohort)/(1.0*a.n*b.n) as lift
            from pairs p join frequencies a on p.skill_a=a.skill join frequencies b on p.skill_b=b.skill
            order by jaccard desc, together desc, skill_a, skill_b limit :lim""", lim=limit, support=min_support)

    def trends(self, dimension="role", skill=None):
        if dimension not in {"role", "state", "remote"}:
            raise ValueError("Unsupported trend dimension")
        return self.run(f"""select cast(date_trunc('month', posted_date) as date) as month,
                     {dimension} as segment, count(*) as postings, count(annual_usd) as salary_sample,
                     percentile_cont(0.5) within group(order by annual_usd) as median_usd
            from cohort j
            where trend_eligible and posted_date is not null and {dimension} is not null
            and (:chosen='' or exists(select 1 from job_skills s where s.job_id=j.job_id and s.skill=:chosen))
            group by 1,2 order by 1,2""", chosen=skill or "")

    def jobs(self, limit=100, offset=0):
        return self.run("""select j.job_id, title, role, company, location, state, experience, remote, posted_date,
                            annual_low, annual_high, annual_usd, salary_origin, source, source_url,
                            (select string_agg(skill, ', ' order by skill) from job_skills s where s.job_id=j.job_id) as skills
                        from (select * from cohort order by posted_date desc nulls last, job_id
                              limit :lim offset :off) j
                        order by posted_date desc nulls last, job_id""", lim=limit, off=offset)
