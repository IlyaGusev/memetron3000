.PHONY: black validate

black:
	uv run black genmeme

validate:
	uv run black genmeme
	uv run flake8 genmeme
	uv run mypy genmeme --strict --explicit-package-bases
