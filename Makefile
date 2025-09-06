.PHONY: help install dev-install run test lint clean docker-build docker-run

# Default target
help: ## Show this help message
	@echo "AEIOU Development Makefile"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	cd sidecar && pip install -r requirements.txt

dev-install: ## Install development dependencies
	cd sidecar && pip install -r requirements.txt -r requirements-dev.txt
	pre-commit install

# Development
run: ## Run the sidecar service
	cd sidecar && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run-dev: ## Run in development mode with auto-reload
	cd sidecar && python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

# Testing
test: ## Run all tests
	cd sidecar && python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term

test-unit: ## Run unit tests only
	cd sidecar && python -m pytest tests/ -v -k "not integration"

test-integration: ## Run integration tests only
	cd sidecar && python -m pytest tests/ -v -k integration

test-coverage: ## Run tests with coverage report
	cd sidecar && python -m pytest tests/ -v --cov=app --cov-report=html
	@echo "Coverage report generated in sidecar/htmlcov/index.html"

# Code Quality
lint: ## Run all linting tools
	cd sidecar && python -m flake8 app/ tests/
	cd sidecar && python -m black --check app/ tests/
	cd sidecar && python -m isort --check-only app/ tests/
	cd nvim && lua-format -i lua/aeiou/*.lua  # If lua-format is available

format: ## Auto-format code
	cd sidecar && python -m black app/ tests/
	cd sidecar && python -m isort app/ tests/
	cd nvim && lua-format -i lua/aeiou/*.lua  # If lua-format is available

type-check: ## Run type checking
	cd sidecar && python -m mypy app/ --ignore-missing-imports

# Documentation
docs: ## Generate documentation
	cd sidecar && python -m pdoc app/ -o docs/
	cd nvim && lua-doc -d docs/ lua/aeiou/*.lua  # If lua-doc is available

# Database
db-init: ## Initialize the database
	cd sidecar && python -c "from app.memory_store import MemoryStore; MemoryStore()"

db-cleanup: ## Clean up expired database entries
	cd sidecar && python -c "from app.memory_store import MemoryStore; ms = MemoryStore(); ms.cleanup_expired()"

# Docker
docker-build: ## Build Docker image
	docker build -t aeiou-sidecar .

docker-run: ## Run in Docker container
	docker run -p 8000:8000 -e OPENAI_API_KEY=$(OPENAI_API_KEY) aeiou-sidecar

# Neovim Plugin
nvim-install: ## Install Neovim plugin (for development)
	@echo "Copy nvim/lua/aeiou/ to your Neovim runtime path"
	@echo "Example: cp -r nvim/lua/aeiou/ ~/.local/share/nvim/site/pack/aeiou/start/"

nvim-test: ## Run Neovim plugin tests
	cd nvim && lua run.lua

# Cleanup
clean: ## Clean up generated files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name ".coverage" -delete

clean-all: clean ## Clean all including databases and logs
	find . -name "*.db" -delete
	find . -name "*.log" -delete
	find . -type d -name logs -exec rm -rf {} +

# Health checks
health: ## Check service health
	curl -s http://127.0.0.1:8000/health | jq .

status: ## Show system status
	@echo "=== AEIOU Status ==="
	@echo "Sidecar: $$(curl -s http://127.0.0.1:8000/health | jq -r '.status // "down"')"
	@echo "Database: $$(cd sidecar && python -c "from app.memory_store import MemoryStore; ms = MemoryStore(); print(f'{len(ms.get_stats())} tables')" 2>/dev/null || echo "error")"
	@echo "Neovim: $$(pgrep -f nvim | wc -l) instances"

# Development workflow
dev: dev-install ## Set up development environment
	@echo "Development environment ready!"
	@echo "Run 'make run' to start the sidecar"
	@echo "Run 'make test' to run tests"

# CI/CD simulation
ci: lint type-check test ## Run CI pipeline locally
	@echo "CI pipeline completed successfully!"

# Release
release: clean test lint ## Prepare for release
	@echo "Ready for release!"

# Utility
shell: ## Start Python shell with app context
	cd sidecar && python -c "from app.main import app; from app.memory_store import MemoryStore; print('AEIOU shell ready')"

logs: ## Show recent logs
	tail -f sidecar/*.log 2>/dev/null || echo "No log files found"
