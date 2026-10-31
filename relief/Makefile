PY ?= python
.PHONY: setup check test serve web web-dev eval demo user
setup:
	$(PY) -m pip install -e ".[dev]" && cd frontend && npm install
check:
	$(PY) scripts/ollama_check.py
test:
	$(PY) -m pytest
web:
	cd frontend && npm run build
serve:
	$(PY) -m uvicorn relief.app.api:create_app --factory --host $${RELIEF_API_HOST:-127.0.0.1} --port $${RELIEF_API_PORT:-8000}
web-dev:
	cd frontend && npm run dev
user:
	$(PY) -m relief.app.cli create-user --email $(EMAIL) --name "$(NAME)" --role $(ROLE)
eval:
	$(PY) -m relief.eval.run_eval
demo:
	$(PY) -m relief.agent.run fixtures/case_referral_input.json --no-llm --approve
