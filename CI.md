# Continuous Integration & Code Coverage

This document explains how to set up and use code coverage in Nucleo development.

## Overview

Nucleo uses a GitHub Actions CI/CD pipeline that automatically:
- Runs tests on Python 3.10, 3.11, 3.12
- Checks code linting with ruff
- Generates code coverage reports
- Uploads coverage to Codecov
- Fails builds if tests don't pass

## Local Setup

### Install Coverage Tools

```bash
pip install pytest pytest-cov ruff
```

### Run Tests with Coverage

```bash
# Basic coverage report (terminal)
pytest test_nucleo.py --cov=nucleo --cov-report=term

# Detailed coverage (terminal + missing lines)
pytest test_nucleo.py --cov=nucleo --cov-report=term-missing

# HTML report (open htmlcov/index.html in browser)
pytest test_nucleo.py --cov=nucleo --cov-report=html

# Combined: XML (for CI) + HTML (for browsing)
pytest test_nucleo.py --cov=nucleo --cov-report=xml --cov-report=html
```

### View Coverage Report

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## GitHub Actions CI Pipeline

### Workflow Triggers

The `.github/workflows/ci.yml` runs on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Manual trigger (workflow_dispatch)

### Pipeline Stages

1. **Test Matrix** (3 Python versions in parallel):
   - Python 3.10, 3.11, 3.12
   - Install dependencies
   - Run linting (ruff check)
   - Run tests with coverage
   - Upload to Codecov

2. **Build Status**:
   - Final check that all tests passed

### Environment Variables

The workflow uses GitHub secrets for:
- `CODECOV_TOKEN` - For uploading coverage reports

## Setting Up Codecov

### 1. Enable Codecov Integration

```bash
# Go to your GitHub repository
https://github.com/YOUR_ORG/nucleo/settings

# Install Codecov GitHub App
# Visit: https://github.com/apps/codecov
```

### 2. Create Codecov Token (Optional)

For private repos or additional security:

```bash
# Visit: https://app.codecov.io/gh/YOUR_ORG/nucleo
# Settings → Copy "Repository Upload Token"
# Add to GitHub Secrets as CODECOV_TOKEN
```

### 3. View Coverage Reports

- **Public**: https://codecov.io/gh/YOUR_ORG/nucleo
- **On PR**: Automated coverage comments on pull requests
- **Badge**: Copy badge markdown from Codecov dashboard

## Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Overall | 70% | TBD |
| agent.py | 90% | TBD |
| channels/ | 90% | TBD |
| tools/ | 85% | TBD |
| memory.py | 85% | TBD |
| identity.py | 85% | TBD |
| scheduler.py | 80% | TBD |

## Writing Tests

### Test File Structure

Tests should be in `test_nucleo.py`:

```python
import pytest
from nucleo import Agent, Config
from nucleo.memory import MemoryManager

class TestAgent:
    """Agent tests"""
    
    def test_agent_initialization(self):
        config = Config().load()
        agent = Agent(config)
        assert agent is not None
        assert agent.memory is not None
    
    async def test_agent_chat(self):
        config = Config().load()
        agent = Agent(config)
        # Note: Mock LLM responses in tests
        # Don't call actual API in tests

class TestMemory:
    """Memory system tests"""
    
    def test_memory_save_and_recall(self):
        mem = MemoryManager(db_path=':memory:')  # In-memory DB for tests
        mid = mem.save_memory('user1', 'Test message')
        assert mid > 0
        
        memories = mem.get_user_memories('user1')
        assert len(memories) > 0
```

### Mocking LLM Calls

For unit tests, mock external API calls:

```python
from unittest.mock import patch, AsyncMock

@patch('nucleo.llm.LLMClient.chat_stream')
async def test_agent_with_mock(mock_chat):
    mock_chat.return_value = AsyncMock(return_value=[
        {'type': 'text', 'content': 'Hello!'}
    ])
    
    config = Config().load()
    agent = Agent(config)
    # Test with mocked LLM
```

## Badges & Status

Add these badges to your README or project documentation:

```markdown
[![Build Status](https://img.shields.io/github/actions/workflow/status/your-org/nucleo/ci.yml?style=flat-square&label=tests)](https://github.com/your-org/nucleo/actions)
[![Code Coverage](https://img.shields.io/codecov/c/github/your-org/nucleo?style=flat-square)](https://codecov.io/gh/your-org/nucleo)
```

## Troubleshooting

### Tests Fail Locally but Pass in CI

- Check Python version: `python --version`
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Clear cache: `rm -rf .pytest_cache __pycache__`

### Coverage Report Not Uploading

- Check `CODECOV_TOKEN` is set in GitHub Secrets
- Verify `.github/workflows/ci.yml` has correct token reference
- Check Codecov status on pull request

### Linting Errors in CI

Run locally and fix before pushing:
```bash
ruff check --fix nucleo/
ruff format nucleo/
```

## Best Practices

1. **Write tests for new features** - Aim for >80% coverage on new code
2. **Mock external APIs** - Don't make real API calls in tests
3. **Use pytest fixtures** - For setup/teardown common test data
4. **Run locally before push** - Catch issues early
5. **Review coverage reports** - Aim to increase coverage each PR
6. **Keep tests fast** - Unit tests should complete in seconds

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Codecov Documentation](https://docs.codecov.io/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
