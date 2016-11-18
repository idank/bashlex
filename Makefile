tests:
	@python -c "import nose" >/dev/null 2>&1 || (echo "error: nose missing, run 'pip install nose'\n" && false)
	python -m nose --with-doctest

.PHONY: tests
