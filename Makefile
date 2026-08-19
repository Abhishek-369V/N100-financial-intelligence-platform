.PHONY: load ratios test report dashboard api clean

load:
	python src/etl/loader.py

test:
	pytest tests/ -v --cov=src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf output/*.csv