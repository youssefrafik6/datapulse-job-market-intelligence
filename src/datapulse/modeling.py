"""Three-way evaluation of advertised USD midpoints with held-out uncertainty."""
import json
import os
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    mean_absolute_error,
    median_absolute_error,
    r2_score,
    root_mean_squared_error,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from datapulse.store import query

FEATURES = ["role", "experience", "state", "remote"]
ARTIFACT = Path("results/salary_model.joblib")
METRICS = Path("results/model_metrics.json")
SEED = 42


def metrics(y, predicted):
    return {"sample": len(y), "mae": mean_absolute_error(y, predicted),
            "rmse": root_mean_squared_error(y, predicted), "r2": r2_score(y, predicted),
            "median_absolute_error": median_absolute_error(y, predicted)}


def partition(frame):
    # An active snapshot cannot support a temporal holdout with missing/censored dates.
    # Employer groups keep same-employer postings out of each independent split.
    groups = frame.company_id.fillna(frame.job_id)
    train_val, test = next(GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=SEED)
                           .split(frame, groups=groups))
    train, val = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
                      .split(frame.iloc[train_val], groups=groups.iloc[train_val]))
    return frame.iloc[train_val[train]], frame.iloc[train_val[val]], frame.iloc[test]


def train(path=None, artifact=ARTIFACT, results=METRICS):
    frame = query("""select job_id, company_id, role, experience, state, remote, annual_usd
                     from jobs where salary_origin='advertised' and annual_usd is not null
                     and source='zalize' order by job_id""", path=path)
    if len(frame) < 200 or frame.company_id.fillna(frame.job_id).nunique() < 10:
        raise ValueError("Need at least 200 eligible salaries and 10 employer groups")
    frame[FEATURES] = frame[FEATURES].fillna("Unknown")
    train_set, validation, test = partition(frame)
    if min(map(len, (train_set, validation, test))) < 20:
        raise ValueError("Too few records in at least one employer-grouped partition")
    candidates = {
        "Median baseline": DummyRegressor(strategy="median"),
        "Ridge": Ridge(alpha=15),
        "Random forest": RandomForestRegressor(n_estimators=150, min_samples_leaf=12,
                                               max_features=0.8, n_jobs=2, random_state=SEED),
    }
    fitted = {}
    validation_scores = {}
    for name, estimator in candidates.items():
        pipeline = make_pipeline(
            ColumnTransformer([("category", OneHotEncoder(handle_unknown="ignore", min_frequency=5), FEATURES)]),
            estimator,
        )
        pipeline.fit(train_set[FEATURES], train_set.annual_usd)
        fitted[name] = pipeline
        validation_scores[name] = metrics(validation.annual_usd, pipeline.predict(validation[FEATURES]))
    selected = min(validation_scores, key=lambda name: validation_scores[name]["mae"])
    model = fitted[selected]
    residuals = abs(validation.annual_usd - model.predict(validation[FEATURES]))
    k = min(len(residuals) - 1, int(np.ceil((len(residuals) + 1) * .9)) - 1)
    radius = float(np.sort(residuals)[k])
    predicted = model.predict(test[FEATURES])
    errors = test.assign(error=abs(test.annual_usd - predicted), band=pd.cut(
        test.annual_usd, [0, 100000, 150000, 200000, np.inf],
        labels=["Under $100k", "$100k–$150k", "$150k–$200k", "Over $200k"],
    ))
    by_segment = {}
    for field in ["role", "experience", "state", "band"]:
        grouped = errors.groupby(field, observed=True).error.agg(sample="size", mae="mean")
        by_segment[field] = grouped[grouped["sample"] >= 15].round(2).to_dict(orient="index")
    importance = permutation_importance(model, validation[FEATURES], validation.annual_usd,
                                        scoring="neg_mean_absolute_error", n_repeats=5, random_state=SEED)
    report = {
        "source": "zalize", "target": "normalized advertised annual USD midpoint",
        "split": "Employer-disjoint training, validation and test groups",
        "train_rows": len(train_set), "validation_rows": len(validation), "test_rows": len(test),
        "selected": selected, "validation": validation_scores, "test": metrics(test.annual_usd, predicted),
        "test_median_baseline": metrics(test.annual_usd, fitted["Median baseline"].predict(test[FEATURES])),
        "interval_radius_usd": radius, "interval_target": .90,
        "test_interval_coverage": float(np.mean(errors.error <= radius)),
        "mae_by_segment": by_segment, "validation_permutation_mae_increase": dict(zip(
            FEATURES, map(float, importance.importances_mean), strict=True)),
    }
    results.parent.mkdir(parents=True, exist_ok=True)
    pending = artifact.with_suffix(".tmp")
    joblib.dump({"pipeline": model, "report": report, "options": {
        feature: sorted(map(str, train_set[feature].unique())) for feature in FEATURES}}, pending)
    os.replace(pending, artifact)
    results.write_text(json.dumps(report, indent=2) + "\n")
    return report


def load(artifact=ARTIFACT):
    return joblib.load(artifact)


def predict(bundle, features):
    unsupported = [key for key in FEATURES if features[key] not in bundle["options"][key]]
    if unsupported:
        raise ValueError(f"Unsupported categories for {', '.join(unsupported)}")
    value = max(0.0, float(bundle["pipeline"].predict(pd.DataFrame([features]))[0]))
    radius = bundle["report"]["interval_radius_usd"]
    return {"prediction_usd": round(value), "lower_usd": round(max(0, value - radius)),
            "upper_usd": round(value + radius), "empirical_test_coverage": bundle["report"]["test_interval_coverage"],
            "model": bundle["report"]["selected"],
            "validation_feature_importance": bundle["report"]["validation_permutation_mae_increase"]}
