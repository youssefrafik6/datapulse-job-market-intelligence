"""Compare the role-only Ridge baseline with regularized skill tags."""

import argparse
import json
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from datapulse.modeling import FEATURES, metrics, partition
from datapulse.store import query


def split_tags(value):
    return value.split("|") if value else []


def benchmark(path):
    frame = query(
        """select j.job_id, j.company_id, j.role, j.experience, j.state, j.remote, j.annual_usd,
                  coalesce(string_agg(s.skill, '|' order by s.skill), '') as tags
           from jobs j left join job_skills s on j.job_id=s.job_id
           where j.source='zalize' and j.salary_origin='advertised' and j.annual_usd is not null
           group by j.job_id, j.company_id, j.role, j.experience, j.state, j.remote, j.annual_usd
           order by j.job_id""",
        path=path,
    )
    frame[FEATURES] = frame[FEATURES].fillna("Unknown")
    train, validation, test = partition(frame)
    models, scores = {}, {}
    for name, use_skills, alpha in [
        ("Ridge", False, 15),
        ("Skills Ridge 15", True, 15),
        ("Skills Ridge 40", True, 40),
        ("Skills Ridge 100", True, 100),
    ]:
        category_encoder = OneHotEncoder(handle_unknown="ignore", min_frequency=5)
        features = [("categories", category_encoder, FEATURES)]
        if use_skills:
            tags = CountVectorizer(
                tokenizer=split_tags, token_pattern=None, binary=True, min_df=10
            )
            features.append(("skills", tags, "tags"))
        model = make_pipeline(ColumnTransformer(features), Ridge(alpha=alpha))
        model.fit(train, train.annual_usd)
        models[name] = model
        scores[name] = metrics(validation.annual_usd, model.predict(validation))
    selected = min(scores, key=lambda name: scores[name]["mae"])
    return {
        "validation": scores,
        "selected": selected,
        "test": metrics(test.annual_usd, models[selected].predict(test)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.database), indent=2))
