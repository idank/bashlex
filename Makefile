tests:
	@which nosetests >/dev/null 2>&1 || echo "error: nosetests missing, run 'pip install nose'\n"
	nosetests --with-doctest tests/ bashlex/

.PHONY: tests
