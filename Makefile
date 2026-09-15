.PHONY: backend frontend test seed reset

backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd web && npm run dev -- --host 0.0.0.0 --port 5173

test:
	cd backend && pytest

seed:
	cd backend && python -m app.seed

reset:
	@echo "Demo reset is introduced in a later checkpoint."
