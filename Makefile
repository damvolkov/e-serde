.PHONY: build-native build-yaml build-toml build-ini clean test

build-native:
	@echo "Building all native crates..."
	cargo build --release -p e-loader-yaml -p e-loader-toml -p e-loader-ini

build-yaml:
	@echo "Building YAML crate..."
	cargo build --release -p e-loader-yaml

build-toml:
	@echo "Building TOML crate..."
	cargo build --release -p e-loader-toml

build-ini:
	@echo "Building INI crate..."
	cargo build --release -p e-loader-ini

clean:
	@echo "Cleaning builds..."
	cargo clean
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

test:
	@echo "Running all tests..."
	pytest tests/

test-native:
	@echo "Running native codec tests..."
	pytest tests/unit/crates/