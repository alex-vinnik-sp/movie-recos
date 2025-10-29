# Movie Recommendations App

A sophisticated movie recommendation system powered by AI, featuring:
- **React Agent** with LangGraph and AWS Bedrock (Claude 3 Haiku)
- **TMDB API** integration for movie data
- **Web search** capabilities via Tavily
- **HTMX frontend** for a smooth user experience
- **MCP Server** for Claude desktop integration
- **LangSmith** tracing for observability

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
- AWS Account with Bedrock access
- AWS Credentials configured (via AWS CLI or environment variables)
- API Keys:
  - [TMDB API key](https://www.themoviedb.org/settings/api)
  - [Tavily API key](https://tavily.com/)
  - [LangSmith API key](https://smith.langchain.com/) (optional - for tracing)

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
# AWS Configuration (credentials should be configured via AWS CLI or environment)
AWS_REGION=us-east-1

# API Keys
TMDB_API_KEY=your_tmdb_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
PORT=3000

# LangSmith Configuration (optional - for tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=movie-recommendations
```

**AWS Credentials Setup:**

AWS credentials should be configured using one of the following methods:
1. **AWS CLI**: Run `aws configure` to set up credentials
2. **Environment Variables**: Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
3. **IAM Role**: If running on AWS (EC2, Lambda, etc.)

Ensure your AWS account has access to Amazon Bedrock and the Claude 3 Haiku model is enabled in your region.

**Note:** LangSmith tracing is optional. If you don't want to use it, you can leave those fields commented out or set `LANGCHAIN_TRACING_V2=false`.

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
        "AWS_ACCESS_KEY_ID": "your_aws_access_key",
        "AWS_SECRET_ACCESS_KEY": "your_aws_secret_key",
        "AWS_REGION": "us-east-1",
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

## LangSmith Tracing

This app includes LangSmith integration for tracing and observability. To enable:

1. Sign up for [LangSmith](https://smith.langchain.com/)
2. Get your API key
3. Add to `.env`:
   ```env
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_api_key
   LANGCHAIN_PROJECT=movie-recommendations
   ```
4. View traces at https://smith.langchain.com/

When tracing is enabled, you'll see all agent interactions, tool calls, and LLM responses in the LangSmith dashboard.

## How It Works

1. **React Agent**: Uses LangGraph's state machine with AWS Bedrock (Claude 3 Haiku) to orchestrate tool calls
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
   - Agent node calls AWS Bedrock (Claude 3 Haiku) with bound tools
   - Tool node executes selected tools
   - Process repeats until agent provides final answer
   - All interactions traced via LangSmith (if enabled)

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
