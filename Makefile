PYTHON ?= python

.PHONY: quality soda gx test

quality: soda gx

soda:
	$(PYTHON) -m data_quality.cli.run_soda_checks \
		--checks normalized_data enriched_data published_data \
		--fail-on-error

gx:
	$(PYTHON) -m data_quality.cli.run_gx_checks

test:
	$(PYTHON) -m pytest -q