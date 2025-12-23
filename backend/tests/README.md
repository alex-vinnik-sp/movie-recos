# Movie Recommendation Agent - Pytest Evaluations

This directory contains pytest-based evaluations for the movie recommendation agent using LangSmith integration.

## Setup

1. Install dependencies:
```bash
# Using pip
pip install -U "langsmith[pytest]"
pip install pytest pytest-asyncio pytest-xdist

# Or using uv (recommended)
uv sync
```

The `langsmith[pytest]` extra provides:
- **Rich terminal outputs**: Beautiful table displays of test results
- **Test caching**: Cache HTTP requests to avoid repeated LLM calls in CI/CD
- **Enhanced pytest integration**: Full support for all LangSmith pytest features

2. Set up environment variables:
```bash
export TMDB_API_KEY=your_tmdb_key
export TAVILY_API_KEY=your_tavily_key
export AWS_REGION=us-east-1
export LANGCHAIN_API_KEY=your_langsmith_key  # Optional, for LangSmith tracking
```

## Running Tests

### Basic run:
```bash
pytest tests/
```

### With test suite name:
```bash
LANGSMITH_TEST_SUITE="Movie Recommendations Tests" pytest tests/
```

### With experiment name:
```bash
LANGSMITH_TEST_SUITE="Movie Recommendations Tests" LANGSMITH_EXPERIMENT="baseline" pytest tests/
```

### With rich output:
```bash
pytest --langsmith-output tests/
```

### Parallel execution:
```bash
pytest -n auto tests/
```

### With caching (recommended for CI):
```bash
LANGSMITH_TEST_CACHE=tests/cassettes pytest tests/
```

### Dry run (without LangSmith tracking):
```bash
LANGSMITH_TEST_TRACKING=false pytest tests/
```

## Test Structure

- `test_movie_recommendations.py`: Main test file with various evaluation scenarios
  - Basic recommendation tests
  - LLM-as-judge relevance evaluation
  - Completeness checks
  - Format quality validation
  - Parametrized genre tests

## Features

- **Automatic dataset creation**: Tests are automatically synced to LangSmith datasets
- **Experiment tracking**: Each test run creates an experiment in LangSmith
- **Multiple evaluators**: Tests use various evaluation metrics
- **LLM-as-judge**: Uses Claude Haiku for relevance evaluation
- **Feedback logging**: Custom feedback scores for different dimensions

## Environment Variables

- `LANGSMITH_TEST_SUITE`: Name of the test suite (default: "Movie Recommendations Tests")
- `LANGSMITH_EXPERIMENT`: Name of the experiment (default: "pytest-evaluation")
- `LANGSMITH_TEST_CACHE`: Path to cache directory for HTTP requests
- `LANGSMITH_TEST_TRACKING`: Set to "false" to disable LangSmith tracking
- `TMDB_API_KEY`: Required for TMDB API access
- `TAVILY_API_KEY`: Required for web search
- `AWS_REGION`: AWS region for Bedrock (default: us-east-1)

## Viewing Results

After running tests, view results in the LangSmith UI:
1. Navigate to the Datasets section
2. Find the dataset named after your test suite
3. View the experiment results with all logged feedback and metrics

