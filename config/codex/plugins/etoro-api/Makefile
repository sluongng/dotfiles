.PHONY: install-local check

install-local:
	./scripts/install-local.sh

check:
	python3 -m py_compile scripts/etoro_api.py
	python3 scripts/etoro_api.py --help >/dev/null
	python3 scripts/etoro_api.py trade --help >/dev/null
	python3 scripts/etoro_api.py --json doctor --skip-network >/dev/null
	python3 scripts/etoro_api.py --json trade close-position --account demo --position-id 123 --instrument-id 456 >/dev/null
