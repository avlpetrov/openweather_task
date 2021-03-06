clean:
	@rm -rf build dist .eggs *.egg-info
	@rm -rf .benchmarks .coverage coverage.xml htmlcov report.xml .tox
	@find . -type d -name '.mypy_cache' -exec rm -rf {} +
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	@find . -type f -name "*.py[co]" -exec rm -rf {} +

format: clean
	@poetry run black . --exclude migrations

test:
	@DATABASE_URI=postgresql://postgres:postgres@localhost:5432/postgres \
	poetry run pytest -s -v

install:
	@poetry install
	@poetry run pre-commit install

precommit:
	@poetry run pre-commit run --all-files

run:
	@docker-compose up --build

migrate:
	@docker-compose run \
	-e DATABASE_URI=postgresql://postgres:postgres@database:5432/postgres \
	-e PYTHONPATH=. app alembic upgrade head
