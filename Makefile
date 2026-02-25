run:
	uv run python -m stj_scraper.scraper --numero $(PROCESSO)

test:
	uv run pytest -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f data/stj.db
	rm -f logs/scraper.log
