.PHONY: install dev dev-be dev-fe test test-be test-fe test-e2e build clean lint

# Install all dependencies
install:
	uv sync
	cd configforge-web && npm ci

# Start both frontend and backend
dev:
	@echo "Starting backend and frontend..."
	@make dev-be & make dev-fe

# Start backend only
dev-be:
	uv run uvicorn configforge.server:app --reload --port 8000

# Start frontend only
dev-fe:
	cd configforge-web && npm run dev

# Run all tests
test: test-be test-fe

# Run backend tests
test-be:
	uv run pytest configforge/tests/ -x -q
	uv run pytest src/tests/ -x -q

# Run frontend tests
test-fe:
	cd configforge-web && npx vitest run

# Run E2E tests
test-e2e:
	cd configforge-web && npx playwright test

# Build Docker image
build:
	docker build -t configforge .

# Clean temporary files and caches
clean:
	rm -rf tmp/uploads/* tmp/logs/* __pycache__ .pytest_cache
	cd configforge-web && rm -rf dist node_modules/.vite

# Lint and type check
lint:
	cd configforge-web && npx vue-tsc --noEmit
