# Movie Recommendations App

A sophisticated movie recommendation system powered by AI, featuring:
- **React Agent** with LangGraph and OpenAI
- **TMDB API** integration for movie data
- **Web search** capabilities via Tavily
- **HTMX frontend** for a smooth user experience
- **MCP Server** for Claude desktop integration
- **Snowflake AI Observability** for evaluation and tracing

## Features

- Get personalized movie recommendations based on natural language queries
- Search by genre, mood, theme, actor, director, or any criteria
- Two interfaces:
  - HTMX web interface for browser-based interaction
  - MCP server for Claude desktop integration

## Project Structure

```
movie_recos/
├── backend/
│   ├── src/
│   │   ├── agent.py           # React agent with LangGraph
│   │   ├── server.py          # FastAPI server with HTMX endpoint
│   │   ├── mcp_server.py      # MCP server implementation
│   │   └── tools/
│   │       ├── tmdb.py        # TMDB API tools
│   │       └── websearch.py   # Web search tool
│   ├── run_server.py          # FastAPI server entry point
│   ├── run_mcp.py             # MCP server entry point
│   ├── pyproject.toml         # UV package configuration
│   └── .env.example
├── frontend/
│   ├── index.html             # HTMX frontend
│   └── styles.css
├── mcp-config.json            # MCP configuration for Claude
└── README.md
```

## Prerequisites

- Python 3.10+
- [UV package manager](https://github.com/astral-sh/uv) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Snowflake account with Cortex access (optional - for AI Observability)
- API Keys:
  - [OpenAI API key](https://platform.openai.com/api-keys)
  - [TMDB API key](https://www.themoviedb.org/settings/api)
  - [Tavily API key](https://tavily.com/)

## Setup

### 1. Install UV

If you haven't already, install UV:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies

```bash
cd backend
uv sync
```

This will create a virtual environment and install all dependencies specified in `pyproject.toml`.

### 3. Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and add your API keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
PORT=3000

# Snowflake AI Observability Configuration (optional - for evaluation and tracing)
ENABLE_SNOWFLAKE_OBSERVABILITY=true
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_ROLE=SYSADMIN  # or your custom role with required privileges
SNOWFLAKE_APP_VERSION=v1.0  # version for tracking experiments
DEBUG_TRULENS=false  # set to true to enable TruLens debug logging
```

**Note:** Snowflake AI Observability is optional. If you don't want to use it, set `ENABLE_SNOWFLAKE_OBSERVABILITY=false` or omit the Snowflake configuration.

## Usage

### Option 1: HTMX Web Interface

1. Start the server:

```bash
cd backend
uv run python run_server.py
```

Or using uvicorn directly:
```bash
cd backend
uv run uvicorn src.server:app --host 0.0.0.0 --port 3000 --reload
```

2. Open your browser to `http://localhost:3000`

3. Enter your movie preferences and get recommendations!

Example queries:
- "action movies like John Wick"
- "romantic comedies from the 90s"
- "movies with strong female leads"
- "sci-fi films similar to Blade Runner"

### Option 2: Claude Desktop (MCP Server)

1. Update `mcp-config.json` with your API keys and correct path:

```json
{
  "mcpServers": {
    "movie-recommendations": {
      "command": "python3",
      "args": ["backend/run_mcp.py"],
      "cwd": "/absolute/path/to/movie_recos",
      "env": {
        "OPENAI_API_KEY": "your_key_here",
        "TMDB_API_KEY": "your_key_here",
        "TAVILY_API_KEY": "your_key_here"
      }
    }
  }
}
```

2. Add the MCP server to your Claude desktop configuration:

On macOS/Linux:
```bash
# Edit Claude desktop config
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

On Windows:
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

3. Add the contents of `mcp-config.json` to your Claude desktop config

4. Restart Claude desktop

5. Use the tool in Claude:
```
Can you recommend some sci-fi movies like Interstellar?
```

## API Reference

### HTMX Endpoint

**POST** `/api/recommend`

Form data:
- `prompt` (string): User's movie preference

Returns: HTML formatted recommendations

### MCP Tool

Tool: `get_movie_recommendations`

Parameters:
- `prompt` (string): User's movie preference

Returns: Text response with recommendations

## Development

Run in development mode with auto-reload:

```bash
cd backend
uv run python run_server.py
# Or
uv run uvicorn src.server:app --host 0.0.0.0 --port 3000 --reload
```

### Adding New Dependencies

Use UV to add new packages:

```bash
cd backend
uv add package-name
```

## Snowflake AI Observability

This app includes [Snowflake AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability) for comprehensive AI application evaluation and tracing. Snowflake AI Observability uses TruLens to provide:

- **Evaluations**: Systematic performance evaluation using LLM-as-a-judge technique
- **Comparison**: Side-by-side comparison of different LLMs, prompts, and configurations
- **Tracing**: Detailed execution traces for debugging and optimization
- **Metrics**: Context relevance, answer relevance, groundedness scores, and more

### Setup

1. **Prerequisites in Snowflake**:
   - Ensure your role has the following privileges:
     - `CORTEX_USER` database role
     - `AI_OBSERVABILITY_EVENTS_LOOKUP` application role
     - `CREATE EXTERNAL AGENT` privilege on the schema
     - `CREATE TASK` privilege on the schema
     - `EXECUTE TASK` global privilege

2. **Install TruLens packages** (already included in `pyproject.toml`):
   ```bash
   cd backend
   uv sync
   ```

3. **Configure environment variables** in `.env`:
   ```env
   ENABLE_SNOWFLAKE_OBSERVABILITY=true
   SNOWFLAKE_ACCOUNT=your_account
   SNOWFLAKE_USER=your_user
   SNOWFLAKE_PASSWORD=your_password
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_ROLE=SYSADMIN  # or your custom role with required privileges
   SNOWFLAKE_APP_VERSION=v1.0  # version for tracking experiments
   DEBUG_TRULENS=false  # set to true to enable TruLens debug logging
   ```
   
   **Note**: The `SNOWFLAKE_ROLE` should be a role that has the required privileges listed in step 1. If not specified, it defaults to `SYSADMIN`.
   
   **Debug Logging**: Set `DEBUG_TRULENS=true` to enable detailed debug logs from TruLens for troubleshooting connection and initialization issues.

4. **Create External Agent in Snowflake** (run once):
   ```sql
   CREATE EXTERNAL AGENT movie_recommendations_agent
   VERSION 'v1.0'
   COMMENT = 'Movie recommendation agent with LangGraph and OpenAI';
   ```

5. **Start the application** - TruLens will automatically:
   - Set `TRULENS_OTEL_TRACING=1` for distributed tracing
   - Connect to Snowflake
   - Store evaluation results and traces in your Snowflake account

6. **View results in Snowsight**:
   - Navigate to your Snowflake account
   - Query the event tables to view traces and metrics
   - Use AI Observability dashboards for evaluation comparisons

For more information, see the [Snowflake AI Observability documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability).

### Instrumentation

The movie recommendation agent is instrumented with TruLens decorators for comprehensive tracing and evaluation:

**Instrumented Methods:**

1. **`get_recommendations()` and `aget_recommendations()`** - Main entry points
   - Span Type: `RECORD_ROOT`
   - Captures: User input prompt and final response
   - Enables: Answer relevance, correctness, and coherence metrics

2. **`_call_model()`** - LLM inference
   - Span Type: `GENERATION`
   - Captures: Model invocation, latency, and responses
   - Enables: Generation quality metrics

**What Gets Traced:**
- Input prompts and output responses
- LLM inference calls with latency
- Tool invocations (TMDB searches, web searches)
- Intermediate steps in the agent workflow
- Error conditions and exceptions

**Viewing Traces:**
1. Navigate to Snowsight → AI & ML → Evaluations
2. Select your application and run
3. View detailed traces with inputs, outputs, and latency for each stage
4. Analyze evaluation metrics (relevance, groundedness, coherence)

For detailed instrumentation guide, see [Snowflake AI Observability - Instrument the app](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability/evaluate-ai-applications#instrument-the-app).

### Application Registration

When Snowflake AI Observability is enabled, the application is automatically registered using `TruSession.App()`:

```python
tru_app = tru_session.App(
    app=agent,
    app_name="movie-recommendations",
    app_version="v1.0",  # configurable via SNOWFLAKE_APP_VERSION
    main_method=agent.aget_recommendations
)
```

**What This Enables:**
- **Trace capture**: All interactions are recorded in Snowflake
- **Evaluation runs**: Create runs with test datasets to compute metrics
- **Version tracking**: Compare different versions (v1.0, v1.1, v2.0, etc.)
- **Experiment comparison**: Side-by-side comparison in Snowsight

**Creating Evaluation Runs:**

After the application is registered, you can create evaluation runs programmatically:

```python
from trulens.core import RunConfig

# Define your run configuration
run_config = RunConfig(
    run_name="test-run-1",
    description="Testing movie recommendations with sample queries",
    source_type="DATAFRAME",
    dataset_name="test_queries",
    dataset_spec={
        "RECORD_ROOT.INPUT": "query",
        "RECORD_ROOT.GROUND_TRUTH_OUTPUT": "expected_answer"
    },
    llm_judge_name="mistral-large2"
)

# Create and execute the run
run = tru_app.add_run(run_config=run_config)
run.start(input_df=test_dataframe)

# Compute evaluation metrics
run.compute_metrics(metrics=[
    "answer_relevance",
    "coherence",
    "correctness"
])
```

For detailed information about creating runs and computing metrics, see [Snowflake AI Observability - Evaluate AI applications](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability/evaluate-ai-applications#register-app-in-snowflake).

## How It Works

1. **React Agent**: Uses LangGraph's state machine with OpenAI to orchestrate tool calls
   - Built as a cyclic graph with agent and tool nodes
   - Agent decides which tools to call based on the user's query
   - Tools execute and return results to the agent
   - Agent synthesizes final response
2. **TMDB Tools**:
   - `search_movies`: Search for movies by title, genre, or get popular movies
   - `get_movie_details`: Get detailed information about specific movies
3. **Web Search Tool**: Search the web for reviews, context, and additional information
4. **Agent Workflow**:
   - Receives user prompt
   - LangGraph manages state through message passing
   - Agent node calls OpenAI with bound tools
   - Tool node executes selected tools
   - Process repeats until agent provides final answer
   - All interactions traced via Snowflake AI Observability (if enabled)

## Architecture

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
       ├─────────────┐
       │             │
┌──────▼──────┐  ┌──▼───────────┐
│ HTMX Web UI │  │ Claude (MCP) │
└──────┬──────┘  └──┬───────────┘
       │             │
       │    ┌────────▼────────┐
       └────►  FastAPI Server │
            └────────┬────────┘
                     │
            ┌────────▼────────┐
            │  React Agent    │
            │   (LangGraph)   │
            └────────┬────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
   ┌────▼───┐  ┌────▼───┐  ┌────▼────┐
   │  TMDB  │  │  TMDB  │  │   Web   │
   │ Search │  │Details │  │ Search  │
   └────────┘  └────────┘  └─────────┘
```

## Troubleshooting

**MCP Server not showing in Claude:**
- Ensure paths in `mcp-config.json` are absolute
- Restart Claude desktop after config changes
- Check Claude logs: `~/Library/Logs/Claude/`

**Agent errors:**
- Verify all API keys are correct
- Check API rate limits
- Review server logs for detailed error messages

**HTMX not loading:**
- Ensure server is running on the correct port
- Check browser console for errors
- Verify frontend files are in the correct location

## License

MIT

## Contributing

Contributions welcome! Please open an issue or submit a pull request.
