.PHONY: install demo history dashboard api lint test validate transform sql docs docker
install:
	python -m pip install -e '.[dev]'
demo:
	python scripts/ingest.py --source zalize
	python scripts/validate.py
	python scripts/train.py
history:
	python scripts/ingest.py --source luke --output data/processed/luke.duckdb --report results/data_quality_luke.json
dashboard:
	streamlit run dashboard/app.py
api:
	uvicorn api.main:app
lint:
	ruff check .
test:
	pytest -q
validate:
	python scripts/validate.py
transform:
	python scripts/transform.py
sql:
	python scripts/run_sql.py
docs:
	dbt docs generate --project-dir dbt --profiles-dir dbt
docker:
	docker compose up --build
