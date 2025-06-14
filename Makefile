# FinGPT Monorepo Makefile
# Unified commands for managing both frontend and backend

.PHONY: help install install-backend install-frontend build dev clean update test lint

# Default target
help:
	@echo "FinGPT Monorepo Management Commands"
	@echo "==================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install          - Install all dependencies (backend + frontend)"
	@echo "  make install-backend  - Install only backend dependencies"
	@echo "  make install-frontend - Install only frontend dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make dev             - Start development servers (backend + frontend watch)"
	@echo "  make build           - Build frontend for production"
	@echo "  make clean           - Clean build artifacts and caches"
	@echo ""
	@echo "Dependency Management:"
	@echo "  make update          - Update all dependencies to latest versions"
	@echo "  make export-reqs     - Export requirements.txt files from Poetry"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint            - Run linters for both backend and frontend"
	@echo "  make test            - Run all tests"

# Full installation
install:
	@echo "🚀 Installing all dependencies..."
	@python scripts/install_all.py

# Backend only
install-backend:
	@echo "🐍 Installing backend dependencies..."
	cd Main/backend && poetry install
	cd Main/backend && poetry run export-requirements

# Frontend only
install-frontend:
	@echo "🎨 Installing frontend dependencies..."
	cd Main/frontend && npm install

# Build frontend
build:
	@echo "🔨 Building frontend..."
	cd Main/frontend && npm run build:full

# Development mode
dev:
	@echo "🚀 Starting development servers..."
	@python scripts/dev_setup.py

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	# Python
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	# Frontend
	rm -rf Main/frontend/dist
	rm -rf Main/frontend/node_modules/.cache
	# Django
	rm -f Main/backend/db.sqlite3
	rm -f Main/backend/django_debug.log

# Update dependencies
update:
	@echo "📦 Updating all dependencies..."
	cd Main/backend && poetry update
	cd Main/backend && poetry run export-requirements
	cd Main/frontend && npm update

# Export requirements
export-reqs:
	@echo "📋 Exporting requirements files..."
	cd Main/backend && poetry run export-requirements

# Run tests
test:
	@echo "🧪 Running tests..."
	cd Main/backend && python manage.py test
	cd Main/frontend && npm test

# Lint code
lint:
	@echo "🔍 Linting code..."
	# Python linting (if ruff or flake8 is installed)
	cd Main/backend && poetry run ruff check . || echo "Install ruff for Python linting"
	# JavaScript linting
	cd Main/frontend && npm run lint || echo "No lint script found"

# Virtual environment setup
venv:
	@echo "🐍 Setting up virtual environment..."
ifeq ($(OS),Windows_NT)
	python -m venv FinGPTenv
	@echo "✅ Virtual environment created. Activate with: FinGPTenv\Scripts\activate"
else
	python3 -m venv FinGPTenv
	@echo "✅ Virtual environment created. Activate with: source FinGPTenv/bin/activate"
endif

# Quick start for new developers
quickstart: venv
	@echo "🎯 Quick start setup..."
	@echo "1. Activate your virtual environment"
	@echo "2. Run: make install"
	@echo "3. Add your API key to Main/backend/.env"
	@echo "4. Run: make dev"