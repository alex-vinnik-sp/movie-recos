# OpenLit Setup Guide

This guide explains how to set up and use OpenLit for LLM observability with the movie recommendation agent.

## What is OpenLit?

OpenLit is an OpenTelemetry-native LLM observability platform that provides:
- **Auto-instrumentation** for 50+ LLM providers, LangChain, and LangGraph
- **ClickHouse-based backend** for storing traces and metrics
- **OpenLit UI** for visualizing traces, metrics, and costs
- **No manual decorators needed** - automatic span creation
- **OpenTelemetry standard compliance** - works with any OTLP backend

Reference: https://github.com/openlit/openlit

## Migration from TruLens

This project has been migrated from TruLens to OpenLit. Key changes:

### What Was Removed
- All TruLens imports and decorators (`@instrument`)
- Snowflake connector setup
- TruGraph wrapper and live_run context
- Manual feedback function implementations
- All `trulens-*` dependencies

### What Was Added
- `openlit>=1.0.0` dependency
- `openlit.init()` in server startup
- Environment variable: `OTEL_EXPORTER_OTLP_ENDPOINT`

### Benefits of OpenLit vs TruLens
1. **Zero code changes** - Auto-instrumentation means no decorators needed
2. **Simpler setup** - No Snowflake configuration or authentication required
3. **OpenTelemetry native** - Standard OTLP protocol, vendor-agnostic
4. **Automatic metrics** - Captures tokens, latency, and costs automatically
5. **Modern UI** - ClickHouse-powered UI for fast trace visualization

## Prerequisites

OpenLit infrastructure should already be running via Docker Compose. Verify with:

```bash
docker ps --filter "name=openlit" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You should see the following containers:
- `openlit` (UI on port 3000)
- `clickhouse` (database)
- `otel-collector` (OpenTelemetry collector on port 4318)

If not running, start the OpenLit stack:

```bash
docker compose up -d
```

## Installation

1. Install updated dependencies:

```bash
cd /Users/alex.vinnik/code/movie-recos/backend
pip install -e .
```

This will:
- Install `openlit>=1.0.0`
- Remove all `trulens-*` packages
- Remove `snowflake-connector-python`

## Configuration

### Environment Variables

Update your `.env` file with the following variables:

```bash
# OpenLit Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318

# API Keys (required)
TMDB_API_KEY=your_tmdb_api_key
TAVILY_API_KEY=your_tavily_api_key

# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1
AWS_PROFILE=your_aws_profile_name  # Optional

# Server Configuration
PORT=3000  # Default: 3000
```

### How It Works

OpenLit automatically instruments your code:

1. **Server Initialization** (`src/server.py` and `src/mcp_server.py`):
   ```python
   import openlit
   
   openlit.init(
       otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://127.0.0.1:4318"),
   )
   ```

2. **Auto-Instrumentation**:
   - OpenLit automatically detects and instruments:
     - **LangChain** chains and agents
     - **LangGraph** graph execution
     - **AWS Bedrock** LLM calls
     - **Tool invocations** (TMDB, Tavily)

3. **No Code Changes Needed**:
   - No decorators required
   - No manual span creation
   - No wrapper objects
   - Just run your code normally!

## Usage

### Running the FastAPI Server

```bash
cd /Users/alex.vinnik/code/movie-recos/backend
python -m src.server
```

OpenLit will automatically capture:
- All LLM calls (prompts, completions, tokens)
- LangGraph execution traces
- Tool invocations
- Latency and performance metrics
- Cost tracking

### Running the MCP Server

```bash
cd /Users/alex.vinnik/code/movie-recos/backend
python -m src.mcp_server
```

Same automatic instrumentation applies.

### Running the CLI Test App

For testing OpenLit integration:

```bash
cd /Users/alex.vinnik/code/movie-recos/backend
python trace_cli.py
```

This will:
1. Initialize OpenLit
2. Create the movie agent
3. Run sample queries
4. Send traces to OpenLit automatically

## Viewing Traces and Metrics

### OpenLit UI

Open your browser to: **http://127.0.0.1:3000**

The UI provides:
- **Traces View**: See all LLM calls, tool invocations, and execution spans
- **Metrics Dashboard**: View latency, token usage, and request counts
- **Cost Tracking**: Monitor API costs across providers
- **Filters**: Filter by time range, status, duration, etc.

### What You'll See

For each movie recommendation request, you'll see:
- **Root span**: The entire request
- **LLM spans**: Each call to AWS Bedrock
  - Input prompts
  - Output completions
  - Token counts (input, output, total)
  - Latency
  - Cost estimate
- **Tool spans**: Calls to TMDB and Tavily APIs
- **LangGraph spans**: State transitions and node executions

## Troubleshooting

### OpenLit UI Not Loading

Check if OpenLit containers are running:

```bash
docker ps --filter "name=openlit"
```

If not running, restart:

```bash
docker compose up -d
```

### No Traces Appearing

1. **Check OTLP endpoint**:
   ```bash
   echo $OTEL_EXPORTER_OTLP_ENDPOINT
   # Should be: http://127.0.0.1:4318
   ```

2. **Verify OpenLit initialization**:
   Check server logs for:
   ```
   ✓ OpenLit initialized successfully
     OTLP Endpoint: http://127.0.0.1:4318
   ```

3. **Test OTLP collector**:
   ```bash
   curl http://127.0.0.1:4318/v1/traces
   ```

4. **Check ClickHouse**:
   ```bash
   docker logs clickhouse
   ```

### Import Error: "openlit" could not be resolved

Make sure you've installed the updated dependencies:

```bash
pip install -e .
```

### AWS Bedrock Credentials

Ensure your AWS credentials are configured:

```bash
aws configure
# OR set in .env:
# AWS_PROFILE=your_profile_name
```

## Comparison: TruLens vs OpenLit

| Feature | TruLens | OpenLit |
|---------|---------|---------|
| **Setup Complexity** | High (Snowflake auth, connectors) | Low (single init call) |
| **Code Changes** | Many (`@instrument` decorators) | Minimal (just `init()`) |
| **Backend** | Snowflake | ClickHouse (via Docker) |
| **Protocol** | Custom + OTEL | OpenTelemetry (OTLP) |
| **UI** | Snowflake-based or TruLens UI | Modern OpenLit UI |
| **Auto-Instrumentation** | Partial | Full (50+ LLM providers) |
| **Vendor Lock-in** | Snowflake | None (OTLP standard) |
| **Local Development** | Requires Snowflake account | Fully local via Docker |
| **LLM Evaluations** | Yes (feedback functions) | Coming soon |

## Advanced Configuration

### Custom OTLP Endpoint

To send traces to a different OTLP endpoint (e.g., production):

```bash
# In .env
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otlp-endpoint:4318
```

### Disable OpenLit (for testing)

OpenLit is always enabled when the server starts. To run without observability, simply don't start the OpenLit Docker containers. The application will continue to work, but without trace collection.

### Environment-specific Configuration

For production deployments, consider:

1. **Separate OTLP collectors** per environment
2. **Different sampling rates** for dev vs prod
3. **Cost alerts** based on token usage
4. **Performance budgets** for latency SLIs

## Resources

- **OpenLit Documentation**: https://docs.openlit.io
- **OpenLit GitHub**: https://github.com/openlit/openlit
- **OpenTelemetry Blog**: https://opentelemetry.io/blog/2024/llm-observability/
- **ClickHouse**: https://clickhouse.com

## Support

For issues or questions:
1. Check OpenLit GitHub Issues: https://github.com/openlit/openlit/issues
2. Join OpenLit Discord: https://discord.gg/openlit
3. Review OpenTelemetry documentation for OTLP troubleshooting

