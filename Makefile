tests:
	@python -c "import pytest" >/dev/null 2>&1 || (echo "error: pytest missing, run 'pip install pytest'\n" && false)
	python -m pytest

.PHONY: tests
