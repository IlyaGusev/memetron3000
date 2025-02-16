.PHONY: black style validate test

black:
	black .

validate:
	black .
	flake8 .
	mypy . --strict --explicit-package-bases
