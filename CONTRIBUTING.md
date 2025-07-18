# Contributing to Semantic MPC Interface

Thank you for your interest in contributing to the Semantic MPC Interface! This document provides guidelines and information for contributors.

## Getting Started

### Development Environment Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/semantic-mpc-interface.git
   cd semantic-mpc-interface
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Development Dependencies**
   ```bash
   pip install -e .[dev]
   ```

4. **Install Pre-commit Hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

### Code Style

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking

Run all checks:
```bash
# Format code
black src/ tests/
isort src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/
```

### Testing

We use pytest for testing:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/semantic_mpc_interface

# Run specific test file
pytest tests/test_model_builder.py
```

### Adding New Features

1. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write Tests First** (TDD approach recommended)
   - Add tests in the appropriate `tests/` subdirectory
   - Ensure tests cover edge cases and error conditions

3. **Implement the Feature**
   - Follow existing code patterns and conventions
   - Add type hints to all functions and methods
   - Include docstrings for public APIs

4. **Update Documentation**
   - Update docstrings
   - Add examples if applicable
   - Update README if needed

5. **Run Tests and Checks**
   ```bash
   pytest
   black src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

## Code Organization

### Module Structure

- `model_builder.py`: Core model building functionality
- `namespaces.py`: RDF namespace definitions
- `metadata.py`: Metadata handling and surveys
- `points.py`: Point management
- `conversion.py`: Unit conversion utilities
- `grafana.py`: Grafana dashboard generation
- `validation.py`: SHACL validation
- `utils.py`: General utility functions

### Template Organization

- `templates/brick-templates/`: Brick Schema templates
- `templates/s223-templates/`: ASHRAE 223P templates
- Each template directory should have `nodes.yml` and `relations.yml`

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for all public functions
- Maximum line length: 88 characters
- Use descriptive variable and function names

### Documentation

- All public functions and classes must have docstrings
- Use Google-style docstrings
- Include examples in docstrings where helpful

Example:
```python
def add_zone(self, zone_id: str) -> None:
    """
    Add an HVAC zone to the model.
    
    Args:
        zone_id: Unique identifier for the zone
        
    Raises:
        ValueError: If zone_id is empty or invalid
        
    Example:
        >>> builder = SemanticModelBuilder("site_001")
        >>> builder.add_zone("zone_001")
    """
```

### Error Handling

- Use specific exception types
- Provide helpful error messages
- Validate inputs early

### Testing

- Write unit tests for all new functionality
- Use descriptive test names
- Test both success and failure cases
- Mock external dependencies

## Submitting Changes

### Pull Request Process

1. **Ensure All Checks Pass**
   ```bash
   pytest
   black --check src/ tests/
   flake8 src/ tests/
   mypy src/
   ```

2. **Update Documentation**
   - Update docstrings
   - Update README if needed
   - Add examples if applicable

3. **Create Pull Request**
   - Use a descriptive title
   - Explain what the PR does and why
   - Reference any related issues
   - Include screenshots for UI changes

4. **Address Review Comments**
   - Respond to all review comments
   - Make requested changes
   - Re-request review when ready

### Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] Added tests for new functionality
- [ ] Updated documentation

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
```

## Reporting Issues

### Bug Reports

Include:
- Python version
- Package version
- Minimal code example
- Expected vs actual behavior
- Full error traceback

### Feature Requests

Include:
- Use case description
- Proposed API (if applicable)
- Examples of how it would be used

## Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Focus on constructive feedback
- Follow the code of conduct

## Questions?

- Open a GitHub Discussion for general questions
- Open an Issue for bugs or feature requests
- Email maintainers for sensitive topics

Thank you for contributing!