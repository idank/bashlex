tests:
	@which nosetests 2>&1 >/dev/null || echo "error: nosetests missing, run 'pip install nose'\n"
	nosetests --with-doctest tests/ bashlex/

.PHONY: tests
