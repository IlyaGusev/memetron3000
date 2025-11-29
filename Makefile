.PHONY: black style validate test

black:
	black genmeme

validate:
	black genmeme
	flake8 genmeme
	mypy genmeme --strict --explicit-package-bases
