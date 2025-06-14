# FinGPT Monorepo Setup Guide

This guide explains the unified dependency management system for FinGPT that handles both backend (Python/Poetry) and frontend (Node.js/npm) dependencies.

## Quick Start

### Option 1: Using Make (Recommended)

```bash
# First-time setup
make quickstart  # Creates virtual environment
make install     # Installs all dependencies

# Development
make dev         # Starts both backend and frontend in dev mode
```

### Option 2: Using Poetry Scripts

```bash
# Install Poetry globally
pip install poetry

# From project root
poetry run fingpt-install  # Install everything
poetry run fingpt-dev      # Start development servers
```

### Option 3: Using Python Scripts Directly

```bash
# Create and activate virtual environment
python -m venv FinGPTenv
source FinGPTenv/bin/activate  # On Windows: FinGPTenv\Scripts\activate

# Run installation
python scripts/install_all.py

# Start development
python scripts/dev_setup.py
```

## Available Commands

### Makefile Commands

| Command                 | Description                                   |
|-------------------------|-----------------------------------------------|
| `make install`          | Install all dependencies (backend + frontend) |
| `make install-backend`  | Install only backend dependencies             |
| `make install-frontend` | Install only frontend dependencies            |
| `make dev`              | Start development servers with hot-reloading  |
| `make build`            | Build frontend for production                 |
| `make clean`            | Clean build artifacts and caches              |
| `make update`           | Update all dependencies to latest versions    |
| `make export-reqs`      | Export requirements.txt files from Poetry     |
| `make test`             | Run all tests                                 |
| `make lint`             | Run linters for both backend and frontend     |

### Features

1. **Unified Installation**: Single command installs both Python and Node.js dependencies
2. **Automatic Virtual Environment**: Detects and helps set up Python virtual environment
3. **Poetry Integration**: Uses Poetry for Python dependencies with fallback to pip
4. **Platform Detection**: Automatically handles Windows/Mac/Linux differences
5. **Development Mode**: Runs both servers concurrently with hot-reloading
6. **Dependency Export**: Automatically exports platform-specific requirements.txt files

## Project Structure

```
fingpt_rcos/
├── Makefile                    # Unified command interface
├── pyproject.toml             # Root Poetry configuration
├── scripts/                   # Management scripts
│   ├── install_all.py        # Full installation script
│   └── dev_setup.py          # Development server runner
├── Main/
│   ├── backend/              # Django backend
│   │   ├── pyproject.toml    # Backend-specific Poetry config
│   │   └── manage_deps.py    # Backend dependency helper
│   └── frontend/             # Browser extension
│       └── package.json      # Frontend npm config
└── Requirements/             # Exported pip requirements
    ├── requirements_win.txt  # Windows dependencies
    └── requirements_mac.txt  # macOS dependencies
```

## Manual Dependency Management

### Adding a Python Package

```bash
# Using Poetry (preferred)
cd Main/backend
poetry add package-name
poetry run export-requirements

# Or from root with Make
cd .
make update
```

### Adding a Node.js Package

```bash
cd Main/frontend
npm install package-name --save
```

### Updating All Dependencies

```bash
# From root directory
make update

# Or manually
cd Main/backend && poetry update
cd Main/frontend && npm update
```

## Troubleshooting

### Virtual Environment Issues

If the scripts can't find your virtual environment:

1. Create it manually:
   ```bash
   python -m venv FinGPTenv
   ```

2. Activate it:
   - Windows: `FinGPTenv\Scripts\activate`
   - Mac/Linux: `source FinGPTenv/bin/activate`

3. Run the installation again

### Poetry Not Found

Install Poetry in your virtual environment:
```bash
pip install poetry
```

### Frontend Build Errors

Ensure Node.js 18+ is installed:
```bash
node --version  # Should be 18.x or higher
```

### Backend Server Won't Start

1. Check Python version: `python --version` (should be 3.10+)
2. Ensure `.env` file exists in `Main/backend/` with your API key
3. Check Django is installed: `pip show django`

## Advanced Usage

### Running Specific Components

```bash
# Backend only
make backend

# Frontend build only
make frontend

# Frontend watch mode
cd Main/frontend && npm run watch
```

### Custom Poetry Commands

The root `pyproject.toml` defines custom commands:
- `poetry run fingpt-install`: Full installation
- `poetry run fingpt-dev`: Development mode

### Environment Variables

Create `Main/backend/.env`:
```env
OPENAI_API_KEY=your-openai-api-key
DEBUG=True
```

## Benefits of This Setup

1. **Single Entry Point**: One command installs everything
2. **Consistency**: Same commands work on all platforms
3. **Developer Experience**: Hot-reloading for both frontend and backend
4. **Dependency Tracking**: Poetry lock file ensures reproducible builds
5. **Easy Updates**: Single command updates all dependencies
6. **CI/CD Ready**: Can be easily integrated into automated pipelines