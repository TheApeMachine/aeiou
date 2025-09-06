# Contributing to AEIOU

Thank you for your interest in contributing to AEIOU! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Community](#community)

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Getting Started

### Prerequisites

- **Python**: 3.10 or higher
- **Neovim**: 0.8 or higher
- **Git**: 2.30 or higher
- **Make**: For using the development Makefile

### Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/aeiou.git`
3. Set up development environment: `./scripts/setup_dev.sh`
4. Start developing!

## Development Setup

### Automated Setup

Run the development setup script:

```bash
./scripts/setup_dev.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Initialize the database
- Set up pre-commit hooks
- Create Neovim plugin symlinks

### Manual Setup

If you prefer manual setup:

```bash
# Python environment
cd sidecar
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Database initialization
python -c "from app.memory_store import MemoryStore; MemoryStore()"

# Pre-commit hooks
pre-commit install

# Neovim plugin (for development)
mkdir -p ~/.local/share/nvim/site/pack/aeiou/start
ln -s $(pwd)/nvim ~/.local/share/nvim/site/pack/aeiou/start/
```

## Development Workflow

### 1. Choose an Issue

- Check the [issue tracker](https://github.com/theapemachine/aeiou/issues) for open issues
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Write tests first (TDD approach)
- Follow the coding standards
- Keep commits atomic and well-described
- Test your changes thoroughly

### 4. Run Tests

```bash
make test              # Run all tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests
make test-coverage     # Run with coverage report
```

### 5. Update Documentation

- Update README.md if needed
- Update help files in `nvim/doc/`
- Add docstrings to new functions
- Update this CONTRIBUTING.md if processes change

### 6. Submit a Pull Request

- Ensure all tests pass
- Update CHANGELOG.md if applicable
- Write a clear PR description
- Reference any related issues

## Coding Standards

### Python (Sidecar)

- **Style**: Follow PEP 8
- **Formatting**: Use Black for consistent formatting
- **Imports**: Use isort for import organization
- **Type Hints**: Use type hints for all function parameters and return values
- **Docstrings**: Use Google-style docstrings
- **Linting**: Code must pass flake8 checks

```python
def process_data(data: Dict[str, Any], config: Optional[Config] = None) -> ProcessedData:
    """Process input data according to configuration.

    Args:
        data: Raw input data to process
        config: Optional processing configuration

    Returns:
        Processed data object

    Raises:
        ProcessingError: If data cannot be processed
    """
    pass
```

### Lua (Neovim Plugin)

- **Style**: Follow the [Lua Style Guide](https://github.com/Olivine-Labs/lua-style-guide)
- **Formatting**: Use consistent indentation (2 spaces)
- **Naming**: Use snake_case for functions and variables
- **Documentation**: Use Vim help format for documentation

```lua
--- Process user input
--- @param input string: User input to process
--- @param options table: Processing options
--- @return table: Processed result
function M.process_input(input, options)
  -- Implementation here
end
```

### Git Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Testing
- `chore`: Maintenance

Examples:
```
feat(ui): add dark mode toggle
fix(api): handle null response from provider
docs(readme): update installation instructions
```

## Testing

### Test Structure

```
sidecar/tests/
├── test_*.py          # Unit tests
├── test_integration.py # Integration tests
└── fixtures/          # Test data

nvim/tests/
├── test_*.lua         # Lua tests
└── fixtures/          # Test data
```

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# With coverage
make test-coverage

# Neovim tests
make nvim-test
```

### Writing Tests

**Python Tests:**
```python
import pytest
from app.example import ExampleClass

class TestExampleClass:
    def test_example_function(self):
        example = ExampleClass()
        result = example.process("input")
        assert result == "expected_output"

    @pytest.mark.asyncio
    async def test_async_function(self):
        # Test async functions
        pass
```

**Lua Tests:**
```lua
local example = require('aeiou.example')

-- Test basic functionality
local result = example.process("input")
assert(result == "expected_output", "Function should return expected output")

print('OK: test_example.lua')
```

## Documentation

### Code Documentation

- **Python**: Use Google-style docstrings
- **Lua**: Use Vim help format in comments
- **API**: Document all public functions and classes

### User Documentation

- Update `nvim/README.md` for user-facing changes
- Update `nvim/doc/aeiou.txt` for Vim help
- Keep examples current and tested

### API Documentation

Generate API docs:

```bash
make docs  # Generate Python docs
```

## Submitting Changes

### Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** your changes
4. **Test** thoroughly
5. **Update** documentation
6. **Commit** with clear messages
7. **Push** to your fork
8. **Create** a Pull Request

### PR Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes without discussion
- [ ] PR description clearly explains changes
- [ ] Related issues referenced

### Review Process

1. Automated checks run (CI/CD)
2. Code review by maintainers
3. Discussion and feedback
4. Approval and merge

## Community

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/theapemachine/aeiou/issues)
- **Discussions**: [GitHub Discussions](https://github.com/theapemachine/aeiou/discussions)
- **Discord**: Join our community Discord

### Recognition

Contributors are recognized in:
- CHANGELOG.md for significant changes
- GitHub's contributor insights
- Release notes

### Governance

- **Maintainers**: Core team responsible for releases and major decisions
- **Contributors**: Community members who contribute code, docs, or issues
- **Users**: Community members who use and provide feedback on AEIOU

## Development Commands

```bash
# Setup
make dev-install      # Install all development dependencies
make dev              # Setup development environment

# Testing
make test            # Run all tests
make lint            # Run linting
make type-check      # Run type checking

# Development
make run             # Start development server
make clean           # Clean build artifacts

# Documentation
make docs            # Generate documentation

# CI/CD
make ci              # Run CI pipeline locally
```

Thank you for contributing to AEIOU! 🎉