# Movie Recommendations App

A sophisticated movie recommendation system powered by AI, featuring:
- **React Agent** with LangGraph and AWS Bedrock (Claude 3.5 Sonnet)
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
- AWS account with Bedrock access
- API Keys:
  - [AWS credentials](https://docs.aws.amazon.com/bedrock/latest/userguide/security-iam.html) with Bedrock access
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
# AWS Bedrock Configuration (Optional - boto3 uses default credential chain)
# Credentials will be automatically loaded from:
# 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
# 2. ~/.aws/credentials file (if using `aws configure`)
# 3. IAM roles (if running on AWS)
AWS_REGION=us-east-1  # Optional, defaults to us-east-1
AWS_PROFILE=dev  # Optional, only if using a specific AWS profile

# API Keys
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

**AWS Credentials:**
The application uses boto3's default credential chain, which means credentials are automatically loaded from:
1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
2. AWS credentials file (`~/.aws/credentials`) - works with `aws configure`
3. AWS config file (`~/.aws/config`)
4. IAM roles (if running on AWS infrastructure)
5. SSO credentials

You can use any of these methods. For example, if you use `aws configure set` to manage credentials, they will be automatically picked up.

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
        "AWS_REGION": "us-east-1",
        "AWS_PROFILE": "dev",
        "TMDB_API_KEY": "your_key_here",
        "TAVILY_API_KEY": "your_key_here"
      }
    }
  }
}
```

**Note:** AWS credentials will be automatically loaded from your `~/.aws/credentials` file (if using `aws configure`) or from environment variables. You only need to specify `AWS_REGION` (optional) and `AWS_PROFILE` (optional, if using a specific profile).

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

This app includes [Snowflake AI Observability](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability) for LangGraph application tracing and monitoring. TruLens provides:

- **Distributed Tracing**: OTEL-based traces exported to Snowflake for observability
- **LangGraph Execution Tracking**: Captures agent workflow, LLM calls, and tool usage
- **Performance Monitoring**: Latency, execution times, and error tracking
- **Debugging**: Detailed execution traces with inputs/outputs at each step

### Setup

1. **Prerequisites in Snowflake**:
   - Ensure your role has the following privileges:
     - Access to the database, schema, and warehouse
     - Permissions to write event data (for OTEL traces)
   - Optional for advanced features:
     - `CORTEX_USER` database role (if using Cortex features)
     - `AI_OBSERVABILITY_EVENTS_LOOKUP` application role (for querying traces)

2. **Install TruLens packages** (already included in `pyproject.toml`):
   ```bash
   cd backend
   uv sync
   ```

3. **Configure environment variables** in `.env`:
   ```env
   ENABLE_SNOWFLAKE_OBSERVABILITY=true
   SNOWFLAKE_ACCOUNT=sailpoint-dev  # your Snowflake account identifier
   SNOWFLAKE_USER=your.email@company.com  # your email for SSO authentication
   SNOWFLAKE_DATABASE=your_database
   SNOWFLAKE_SCHEMA=your_schema
   SNOWFLAKE_WAREHOUSE=your_warehouse
   SNOWFLAKE_ROLE=SYSADMIN  # or your custom role with required privileges
   DEBUG_TRULENS=false  # set to true to enable TruLens debug logging
   ```
   
   **Authentication**: Uses SSO (Single Sign-On) with `externalbrowser` authenticator. When you start the application, a browser window will open for authentication (same as `snowsql --authenticator externalbrowser`).
   
   **Note**: The `SNOWFLAKE_ROLE` should be a role that has the required privileges listed in step 1. If not specified, it defaults to `SYSADMIN`.
   
   **Debug Logging**: Set `DEBUG_TRULENS=true` to enable detailed debug logs from TruLens for troubleshooting connection and initialization issues.

4. **Start the application** - TruLens will automatically:
   - Set `TRULENS_OTEL_TRACING=1` for distributed tracing
   - Open browser for SSO authentication (first time)
   - Create Snowpark session with your credentials
   - Connect to Snowflake and export OTEL traces

5. **View traces in Snowsight**:
   - Navigate to your Snowflake account
   - Query the event tables to view execution traces
   - Use AI Observability dashboards for performance monitoring

For more information, see the [Snowflake AI Observability documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability).

### Instrumentation

The movie recommendation agent is instrumented with TruLens `@instrument` decorators for distributed tracing:

**Instrumented Methods:**

1. **`aget_recommendations()`** - Main entry point
   - Span Type: `RECORD_ROOT`
   - Captures: User input prompt and final response
   - Tracks: End-to-end execution and latency

2. **`_call_model()`** - LLM inference
   - Span Type: `GENERATION`
   - Captures: Model invocation, latency, and responses
   - Tracks: LLM generation performance

3. **Tool Methods** - TMDB and web search
   - Span Type: `RETRIEVAL`
   - Captures: Query inputs and retrieved contexts
   - Tracks: Tool execution and data retrieval

**What Gets Traced:**
- Input prompts and output responses
- LLM inference calls with latency
- Tool invocations (TMDB movie searches, web searches)
- LangGraph node transitions and state changes
- Error conditions and exceptions
- Execution timing at each step

**Viewing Traces:**
1. Navigate to Snowsight → AI & ML → Observability
2. Select your application
3. View detailed OTEL traces with inputs, outputs, and latency for each span
4. Analyze performance bottlenecks and execution flow

For detailed instrumentation guide, see [Snowflake AI Observability - Instrument the app](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability/evaluate-ai-applications#instrument-the-app).

### TruLens Packages

The application uses the following TruLens packages for tracking:

- **`trulens-core`** - Core instrumentation with `@instrument` decorators
- **`trulens-connectors-snowflake`** - OTEL trace export to Snowflake
- **`trulens-apps-langgraph`** - LangGraph-specific tracing support (available for automatic graph-level tracing)

**Note**: This setup is optimized for **tracking and observability only**. Evaluation features (e.g., `trulens-providers-cortex` for LLM-as-a-judge metrics) are not included. If you need evaluation capabilities, you can add them separately.

For detailed information about Snowflake AI Observability features, see [Snowflake AI Observability documentation](https://docs.snowflake.com/en/user-guide/snowflake-cortex/ai-observability).

## How It Works

1. **React Agent**: Uses LangGraph's state machine with AWS Bedrock (Claude 3.5 Sonnet) to orchestrate tool calls
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
   - Agent node calls AWS Bedrock with bound tools
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
