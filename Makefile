.PHONY: install api web build test
install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	npm --prefix frontend ci
api:
	.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
web:
	npm --prefix frontend run dev
build:
	npm --prefix frontend run build
test:
	.venv/bin/python -m pytest -q
	npm --prefix frontend run typecheck
	node --check extension/content.js
	node --check extension/popup.js
