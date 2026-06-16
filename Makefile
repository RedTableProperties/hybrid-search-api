PYTHON ?= python

YELLOW := \033[1;33m
GREEN := \033[0;32m
NC := \033[0m

.PHONY: quality quality-report soda gx test clear-soda-cache

quality: soda gx

quality-report:
	$(PYTHON) data_quality/cli/generate_quality_reports.py

soda:
	$(PYTHON) -m data_quality.cli.run_soda_checks \
		--checks normalized_data enriched_data published_data \
		--fail-on-error

gx:
	$(PYTHON) -m data_quality.cli.run_gx_checks

test:
	$(PYTHON) -m pytest -q

clear-soda-cache:
	@echo -e "$(YELLOW)Clearing Soda Core cache...$(NC)"
	@rm -f soda_results.json
	@rm -rf .soda
	@echo -e "$(GREEN)✅ Soda Core cache cleared.$(NC)"