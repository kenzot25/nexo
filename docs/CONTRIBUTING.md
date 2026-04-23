# Contributing to nexo

Thank you for contributing to nexo! This guide covers how to contribute code, documentation, and bug reports.

## Getting Started

### 1. Fork and Clone

```bash
# Fork on GitHub, then clone
git clone https://github.com/YOUR_USERNAME/nexo.git
cd nexo

# Add upstream remote
git remote add upstream https://github.com/kenzot25/nexo.git
```

### 2. Set Up Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or use make
make setup
```

### 3. Run Tests

```bash
# All tests
make t

# Specific test file
pytest tests/test_mcp_subagent.py -v

# With coverage
pytest tests/ --cov=nexo --cov-report=term-missing
```

## How to Contribute

### Reporting Bugs

1. **Check existing issues** - Search [GitHub Issues](https://github.com/kenzot25/nexo/issues)
2. **Create a new issue** with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python version, nexo version)
   - Relevant error messages/logs

### Suggesting Features

1. **Open an issue** describing the feature
2. **Explain the use case** - Why is this needed?
3. **Discuss implementation** - Maintainers will provide feedback

### Code Contributions

#### Small Changes (Bug Fixes, Typos)

1. Create a branch: `git checkout -b fix/issue-123`
2. Make changes
3. Run tests: `make t`
4. Commit: `git commit -m "Fix: describe the fix"`
5. Push and create PR

#### Larger Changes (Features, Refactors)

1. **Open an issue first** to discuss the approach
2. **Create a branch**: `git checkout -b feature/new-feature`
3. **Implement the feature** with tests
4. **Update documentation** if applicable
5. **Run all tests**: `pytest tests/ -q`
6. **Check code style**: ensure PEP 8 compliance
7. **Commit** with clear messages
8. **Push and create PR**

## Pull Request Guidelines

### PR Title

- Use conventional commits style: `feat:`, `fix:`, `docs:`, `chore:`, etc.
- Keep it under 72 characters
- Example: `feat: add new workspace query mode`

### PR Description

Use this template:

```markdown
## Summary
- What does this PR do?
- Why is this change needed?

## Changes
- List key changes

## Testing
- How was this tested?
- Any new tests added?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Changelog entry added (if applicable)
```

### Before Submitting

- [ ] Tests pass (`make t`)
- [ ] Code follows PEP 8
- [ ] Type hints added for new functions
- [ ] Docstrings for public APIs
- [ ] Documentation updated (if applicable)

## Code Standards

### Python Style

- Follow PEP 8
- Use type hints: `def func(x: int) -> str:`
- Max line length: 88 characters (Black default)
- Use f-strings for formatting

### Type Hints

```python
# Good
def process_files(paths: list[Path], max_count: int = 100) -> dict[str, Any]:
    ...

# Avoid
def process_files(paths, max_count=100):
    ...
```

### Docstrings

```python
def cluster(graph: nx.Graph) -> dict[int, int]:
    """Run community detection on a graph.
    
    Args:
        graph: NetworkX graph with nodes and edges
        
    Returns:
        Dict mapping node_id to community_id
        
    Raises:
        ValueError: If graph is empty
    """
```

### Tests

- Use pytest
- Test both success and failure cases
- Use `tmp_path` for file operations
- Keep tests isolated and deterministic

```python
def test_extract_finds_nodes(tmp_path):
    code_file = tmp_path / "sample.py"
    code_file.write_text("def foo(): pass")
    
    result = extract(code_file)
    
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["label"] == "foo"
```

## Documentation Contributions

### Types of Documentation

- **User Guide** (`docs/USER_GUIDE.md`) - Workflows and examples
- **Developer Guide** (`docs/DEVELOPING.md`) - Architecture and extension
- **CLI Reference** (`docs/CLI_REFERENCE.md`) - Command documentation
- **FAQ** (`docs/faq.md`) - Common questions

### Documentation Style

- Use clear, action-oriented language
- Include copy-paste examples
- Link to related docs
- Keep paragraphs short (3-4 sentences max)

## Release Process

### Version Numbering

nexo follows [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (e.g., `1.2.3`)
- **MAJOR**: Breaking changes
- **MINOR**: New features (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

### Release Checklist

For maintainers:

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run tests: `pytest tests/ -q`
4. Tag release: `git tag -a v1.2.3 -m "Release 1.2.3"`
5. Push tag: `git push origin v1.2.3`
6. Build: `python -m build`
7. Publish: `twine upload dist/*`
8. Create GitHub Release

## Questions?

- **General questions**: Open a [Discussion](https://github.com/kenzot25/nexo/discussions)
- **Bug reports**: Open an [Issue](https://github.com/kenzot25/nexo/issues)
- **Security issues**: See [SECURITY.md](../SECURITY.md)

## Thank You!

Every contribution helps make nexo better. Whether it's a bug report, documentation fix, or new feature - your time is appreciated!
