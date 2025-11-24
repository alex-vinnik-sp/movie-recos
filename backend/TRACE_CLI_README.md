# TruLens Snowflake Tracing CLI

A standalone CLI application for recording TruLens traces to Snowflake. This script demonstrates how to instrument a LangGraph agent and automatically capture execution traces (LLM calls, inputs, outputs, metadata) in Snowflake for observability and analysis.

## 🎯 Purpose

This CLI app:
- Configures TruLens to send instrumentation traces to Snowflake
- Wraps a MovieAgent (LangGraph) with TruApp for automatic tracing
- Runs 3 different movie recommendation queries **in parallel**
- Records all LLM interactions, tool calls, and responses to Snowflake tables

## 📋 Prerequisites

1. **Snowflake Account** with:
   - Database and schema for storing traces
   - Warehouse for compute
   - SSO/OAuth authentication configured

2. **AWS Bedrock Access** for Claude model

3. **API Keys**:
   - TMDB (The Movie Database) API key
   - Tavily API key for web search

## 🔧 Installation

### 1. Install Dependencies

```bash
cd /Users/alex.vinnik/code/movie-recos/backend
uv sync
```

This installs:
- `trulens-core`, `trulens-connectors-snowflake`, `trulens-apps-langgraph`, `trulens-benchmark`
- `snowflake-connector-python[pandas]` with PyArrow and secure-local-storage
- LangGraph, LangChain, AWS Bedrock dependencies
- MS MARCO BEIR dataset (downloaded on first run, ~200MB)

### 2. Configure Environment Variables

Create a `.env` file in the backend directory with:

```bash
# Snowflake Configuration
SNOWFLAKE_ACCOUNT=your-account-identifier
SNOWFLAKE_USER=your-username
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=your-schema
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_ROLE=SYSADMIN  # Optional, defaults to SYSADMIN

# TruLens Configuration
TRULENS_OTEL_TRACING=true  # true = enabled (default), false = disabled
TRULENS_USE_ACCOUNT_EVENT_TABLE=false  # false = traditional tables (OTEL + feedbacks), true = native OTEL event tables (traces only, no feedbacks)

# API Keys
TMDB_API_KEY=your-tmdb-api-key
TAVILY_API_KEY=your-tavily-api-key

# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1  # Optional, defaults to us-east-1
AWS_PROFILE=your-profile  # Optional

# Evaluations (Optional)
ENABLE_EVALUATIONS=false  # Set to 'true' to enable feedback evaluations (ground truth + LLM-based)
```

**Note:** Uses external browser authentication (SSO/OAuth) for Snowflake - no password needed!

## 🚀 Usage

Run the CLI:

```bash
uv run python trace_cli.py
```

### What Happens:

1. **Loads environment variables** from `.env` (overrides system vars)
2. **Enables TruLens debug logging** for detailed insights
3. **Authenticates with Snowflake** via browser SSO
4. **Verifies Snowpark session** (database, schema, warehouse, role)
5. **Checks for existing TruLens tables** in Snowflake
6. **Creates TruApp wrapper** around the MovieAgent
7. **Runs 3 movie queries in parallel**:
   - "Recommend a good sci-fi movie"
   - "What are some great comedy movies from the 2020s?"
   - "Suggest a thriller movie with a twist ending"
8. **Records all traces to Snowflake**
9. **Displays results** and confirmation

## 📊 Output Example

```
=============================================================
TruLens Snowflake Tracing CLI
=============================================================

Loading environment variables from .env file...
✓ All required environment variables found

------------------------------------------------------------
ENABLING DEBUG LOGGING
------------------------------------------------------------
✓ TruLens debug logging enabled

Note: A browser window will open for Snowflake authentication...

------------------------------------------------------------
SNOWPARK SESSION VERIFICATION
------------------------------------------------------------
  Connected User: YOUR_USER
  Current Role: SYSADMIN
  Current Warehouse: YOUR_WAREHOUSE
  Current Database: YOUR_DATABASE
  Current Schema: YOUR_SCHEMA

  ⚠ No TruLens tables found yet (will be created on first trace)

✓ Snowpark session verification complete

------------------------------------------------------------
TRULENS CONNECTOR DIAGNOSTICS
------------------------------------------------------------
  Connector Type: SnowflakeConnector
  ✓ Connector has snowpark_session attribute
  OTEL Tracing Enabled: 1
  Table Mode: Traditional TruLens tables (OTEL traces + feedbacks)

✓ MovieAgent created successfully
✓ TruApp wrapper created successfully

=============================================================
RUNNING 1 QUERIES IN PARALLEL
=============================================================

🔍 Starting query 1: Recommend a good sci-fi movie

✓ All queries completed

=============================================================
QUERY 1/1: Recommend a good sci-fi movie
=============================================================
------------------------------------------------------------
RESPONSE:
------------------------------------------------------------
[Movie recommendations...]
------------------------------------------------------------

=============================================================
🎉 Traces have been recorded to Snowflake!
=============================================================
```

## 🔍 Key Features

### ✅ Parallel Query Execution Support
- Configured to run 1 query by default
- Supports running multiple queries concurrently using `asyncio.gather()`
- To enable multiple queries: uncomment additional queries in the `queries` list
- All queries in the list will run in parallel for faster execution

### ✅ External Browser Authentication
- Uses SSO/OAuth for Snowflake
- No passwords in `.env` file
- Secure browser-based login

### ✅ Comprehensive Diagnostics
- Debug logging for TruLens internals
- Snowpark session verification
- Connector diagnostics
- Table existence checks

### ✅ TruApp Integration
- Wraps LangGraph agent with TruApp
- Uses `live_run()` context for proper trace recording
- Automatic instrumentation via `@instrument` decorators

### ✅ MS MARCO Ground Truth Evaluation (Demonstration)
- Loads BEIR MS MARCO benchmark dataset
- Demonstrates TruLens ground truth evaluation capabilities
- Creates feedback functions for semantic similarity
- **Educational Purpose:** Shows evaluation features, but note that MovieAgent uses APIs (TMDB, Tavily) rather than traditional document retrieval, so IR metrics aren't directly applicable

**Learn More:**
- [BEIR Benchmark](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/)
- [TruLens Ground Truth Evaluation](https://www.trulens.org/getting_started/quickstarts/groundtruth_evals_for_retrieval_systems/)

### ✅ Feedback Evaluations (Optional)
The CLI includes optional feedback evaluation using AWS Bedrock Claude as a judge:

**How to Enable:** Set `ENABLE_EVALUATIONS=true` in your `.env` file.

**What's Included:**
1. **Ground Truth Evaluation** (MS MARCO dataset)
   - Demonstrates TruLens ground truth evaluation capabilities
   - Compares responses against reference answers using LLM judge
2. **LLM-Based Evaluations**
   - **Answer Relevance**: Does the recommendation address the user's query?
   - **Helpfulness**: Is the recommendation helpful and actionable?
   - **Conciseness**: Is the response clear and not overly verbose?

**How it works:**
1. Your app generates a movie recommendation
2. TruLens sends the input/output to Claude (judge LLM)
3. Claude scores the quality (0-10) with reasoning
4. Scores stored in Snowflake for tracking

**Note:** Each evaluation makes an API call to Claude, which incurs costs. Use judiciously.

### 🗄️ Choosing Your Table Mode

The `TRULENS_USE_ACCOUNT_EVENT_TABLE` environment variable controls which database schema TruLens uses for storing OTEL traces:

**Traditional Tables Mode (default, `TRULENS_USE_ACCOUNT_EVENT_TABLE=false`):**
- ✅ **Use when:** You need feedback evaluation (ground truth or LLM-based)
- ✅ **Best for:** Development, testing, and production with evaluations
- Creates TruLens-specific tables in your Snowflake schema
- Stores OTEL traces in traditional table format
- Supports both OTEL traces AND feedback results
- Works with OTEL `@instrument` decorators

**Native Event Tables Mode (`TRULENS_USE_ACCOUNT_EVENT_TABLE=true`):**
- ✅ **Use when:** You only need OTEL trace collection (no evaluations)
- ✅ **Best for:** Integration with Snowflake's native OTEL infrastructure
- Uses Snowflake's account-level event tables (e.g., `SNOWFLAKE.TELEMETRY.EVENTS`)
- Stores OTEL traces in Snowflake's native OpenTelemetry format
- Works with OTEL `@instrument` decorators
- ❌ Feedback evaluation NOT supported in this mode (TruLens limitation)

## 🛠️ Troubleshooting

### No Tables in Snowflake
- Check that OTEL tracing is enabled (`TRULENS_OTEL_TRACING=1`)
- Verify Snowflake permissions (CREATE TABLE rights)
- Check TruLens debug logs for errors

### Authentication Fails
- Ensure SSO is configured in Snowflake
- Check browser allows pop-ups
- Verify `SNOWFLAKE_ACCOUNT` and `SNOWFLAKE_USER` are correct

### Missing Pandas Error
- Ensure you installed with: `snowflake-connector-python[pandas]`
- Run: `uv sync` to reinstall dependencies

## 📚 Architecture

```
trace_cli.py
    ↓
load_dotenv(override=True)
    ↓
TruLens Debug Logging (enabled)
    ↓
Snowpark Session (SSO auth)
    ↓
SnowflakeConnector (use_account_event_table=False)
    ↓
MovieAgent (LangGraph)
    ↓
TruApp(agent, connector, feedbacks)
    ↓
live_run() context
    ↓
Query execution (1+ queries, asyncio.gather)
    ↓
Traces + Feedback Results → Snowflake Tables
```

**Database Schema & OTEL Tracing:**
- Both modes use OTEL tracing via `@instrument` decorators (enabled by `TRULENS_OTEL_TRACING=1`)
- Table mode is configurable via `TRULENS_USE_ACCOUNT_EVENT_TABLE` environment variable
- **Default (false)**: TruLens traditional tables
  - ✅ OTEL traces stored in TruLens's custom schema
  - ✅ Supports feedback evaluation alongside OTEL traces
  - ✅ Both trace collection AND feedback evaluation
- **Optional (true)**: Snowflake native event tables
  - ✅ OTEL traces stored in Snowflake's native OpenTelemetry format
  - ✅ Uses account-level event tables (e.g., `SNOWFLAKE.TELEMETRY.EVENTS`)
  - ❌ Feedback evaluation NOT supported (TruLens limitation with OTEL + native tables)

## 🔗 Related Files

- `src/agent.py` - MovieAgent with `@instrument` decorators
- `src/server.py` - FastAPI server (also uses TruLens)
- `pyproject.toml` - Dependencies configuration

## 📝 Notes

- The `.env` file overrides system environment variables
- TruLens tables are created automatically on first run
- Each run has a timestamped name: `movie_rec_YYYY-MM-DD_HH-MM-SS`
- All traces from the queries are grouped under one run (1 query by default, more can be added)
- **OTEL Tracing**: Enabled by default (`TRULENS_OTEL_TRACING=true`). The `@instrument` decorators capture function calls, inputs, and outputs. Set to `false` only if you don't want any tracing.
- **Table Mode**: When OTEL tracing is enabled, set `TRULENS_USE_ACCOUNT_EVENT_TABLE=false` (default) for OTEL traces + feedback support, or `true` for OTEL traces in native Snowflake event tables only

### About MS MARCO Ground Truth Evaluation

The MS MARCO BEIR dataset integration is included for **educational/demonstration purposes** to showcase TruLens ground truth evaluation capabilities. 

**Important:** MovieAgent is not a traditional Information Retrieval (IR) system:
- ✅ MovieAgent makes API calls to TMDB and Tavily
- ✅ Uses LLM to generate conversational recommendations
- ❌ Does NOT retrieve documents from a static corpus
- ❌ Does NOT rank retrieved documents

Traditional IR metrics like NDCG@k, IR Hit Rate, and Recall@k are designed for document retrieval systems. While they're included here to demonstrate TruLens features, they don't directly evaluate the MovieAgent's actual architecture.

For more appropriate MovieAgent evaluation, consider:
- LLM-based evaluations (answer relevance, helpfulness)
- User feedback collection
- Custom ground truth datasets with movie Q&A pairs

## 🎬 Next Steps

After running successfully:
1. Check Snowflake for trace tables
2. Query trace data for analysis
3. Integrate TruApp into other applications
4. Add evaluation feedback functions (optional)
5. Build dashboards using trace data

---

**Built with:** TruLens, Snowflake, LangGraph, AWS Bedrock, Python 3.12+

