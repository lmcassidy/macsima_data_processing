# MACSima Data Processing Makefile
.PHONY: help test run frontend clean install lint format check-deps

PYTHON ?= python3

# Default target
help: ## Show this help message
	@echo "MACSima Data Processing Commands:"
	@echo "================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Installation and setup
install: ## Install Python dependencies
	$(PYTHON) -m pip install -r requirements.txt

check-deps: ## Check if required dependencies are installed
	@$(PYTHON) -c "import flask, pandas, xlsxwriter; print('✅ All dependencies installed')" || (echo "❌ Missing dependencies. Run 'make install'" && exit 1)

# Testing
test: check-deps ## Run the complete test suite
	pytest -v

test-coverage: check-deps ## Run the complete test suite with coverage
	pytest --cov=src --cov=app --cov-report=html --cov-report=term

# Data processing
run: check-deps ## Run parser on sample dataset (uses data/data\ MR.json)
	@echo "🔄 Processing sample dataset..."
	cd src && python macsima_parser.py "../data/data MR.json"
	@echo "✅ Processing complete! Check src/output/ for results"

run-all-samples: check-deps ## Process all JSON files in data/ directory
	@echo "🔄 Processing all sample datasets..."
	@for json_file in data/*.json; do \
		if [ -f "$$json_file" ]; then \
			echo "Processing: $$json_file"; \
			cd src && python macsima_parser.py "../$$json_file" && cd ..; \
		fi \
	done
	@echo "✅ All processing complete! Check src/output/ for results"

# Web interface
frontend: check-deps ## Start the Flask web UI locally
	@echo "🚀 Starting MACSima Parser web interface..."
	@echo "🌐 Open http://localhost:5001 in your browser"
	@echo "⏹️  Press Ctrl+C to stop"
	@echo "ℹ️  Using port 5001 to avoid conflicts with AirPlay Receiver"
	$(PYTHON) -c "import app; app.app.run(debug=True, host='0.0.0.0', port=5001)"

frontend-prod: check-deps ## Start Flask web UI in production mode with gunicorn
	@echo "🚀 Starting MACSima Parser web interface (production)..."
	@echo "🌐 Open http://localhost:8000 in your browser"
	gunicorn -w 4 -b 0.0.0.0:8000 app:app

# Code quality
lint: check-deps ## Run code linting (if available)
	@command -v flake8 >/dev/null 2>&1 && flake8 src/ app.py || echo "⚠️  flake8 not installed. Install with: pip install flake8"
	@command -v pylint >/dev/null 2>&1 && pylint src/macsima_parser.py app.py || echo "⚠️  pylint not installed. Install with: pip install pylint"

format: ## Format code (if black is available)
	@command -v black >/dev/null 2>&1 && black src/ app.py || echo "⚠️  black not installed. Install with: pip install black"

# Cleanup
clean: ## Clean up generated files
	@echo "🧹 Cleaning up..."
	rm -rf src/output/*.xlsx
	rm -rf data/*.xlsx
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf src/__pycache__
	rm -rf __pycache__
	rm -rf .coverage
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "✅ Cleanup complete"

# Development helpers
dev-setup: install ## Complete development setup
	@echo "🛠️  Setting up development environment..."
	@$(PYTHON) -m pip --version >/dev/null 2>&1 || (echo "❌ pip not found. Please install Python first." && exit 1)
	$(PYTHON) -m pip install -r requirements-dev.txt
	@echo "✅ Development setup complete!"
	@echo "💡 Try: make test, make run, or make frontend"

status: ## Show project status
	@echo "📊 MACSima Data Processing Status"
	@echo "================================"
	@echo "📁 Project directory: $(PWD)"
	@echo "🐍 Python version: $$($(PYTHON) --version 2>/dev/null || echo 'Not found')"
	@echo "📦 Dependencies:"
	@$(PYTHON) -c "import flask, pandas, xlsxwriter; print('  ✅ Flask, Pandas, xlsxwriter')" 2>/dev/null || echo "  ❌ Missing core dependencies"
	@echo "📄 Sample data files: $$(ls -1 data/*.json 2>/dev/null | wc -l | tr -d ' ') JSON file(s)"
	@echo "🧪 Test files: $$(find src -name '*test*.py' | wc -l | tr -d ' ') test file(s)"
	@echo "🌐 Web interface: app.py"

# Quick demo
demo: check-deps ## Run a quick demo (process sample data and show results)
	@echo "🎯 Running MACSima Parser Demo"
	@echo "=============================="
	@echo "1️⃣  Running tests..."
	@make test --no-print-directory
	@echo ""
	@echo "2️⃣  Processing sample data..."
	@make run --no-print-directory
	@echo ""
	@echo "3️⃣  Demo complete! 🎉"
	@echo "💡 Next steps:"
	@echo "   • Run 'make frontend' to try the web interface"
	@echo "   • Check src/output/ for generated Excel files"
	@echo "   • Upload your own JSON files via the web UI"
