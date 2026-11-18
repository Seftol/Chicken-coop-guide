.PHONY: build test check preview

build:
	python3 scripts/build.py

test:
	python3 -m unittest discover -s tests -v

check: build test
	python3 scripts/linkcheck.py

preview: build
	python3 scripts/preview.py
