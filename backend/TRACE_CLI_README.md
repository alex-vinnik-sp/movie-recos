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
- `trulens-core`, `trulens-connectors-snowflake`, `trulens-apps-langgraph`
- `snowflake-connector-python[pandas]` with PyArrow
- LangGraph, LangChain, AWS Bedrock dependencies

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

# API Keys
TMDB_API_KEY=your-tmdb-api-key
TAVILY_API_KEY=your-tavily-api-key

# AWS Configuration (for Bedrock)
AWS_REGION=us-east-1  # Optional, defaults to us-east-1
AWS_PROFILE=your-profile  # Optional
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

✓ MovieAgent created successfully
✓ TruApp wrapper created successfully

=============================================================
RUNNING 3 QUERIES IN PARALLEL
=============================================================

🔍 Starting query 1: Recommend a good sci-fi movie
🔍 Starting query 2: What are some great comedy movies from the 2020s?
🔍 Starting query 3: Suggest a thriller movie with a twist ending

✓ All queries completed

=============================================================
QUERY 1/3: Recommend a good sci-fi movie
=============================================================
------------------------------------------------------------
RESPONSE:
------------------------------------------------------------
[Movie recommendations...]
------------------------------------------------------------

... [additional queries] ...

=============================================================
🎉 Traces have been recorded to Snowflake!
=============================================================
```

## 📈 Viewing Traces in Snowflake

### 1. Navigate to Snowsight

Go to: **Data → Databases → YOUR_DATABASE → YOUR_SCHEMA**

### 2. Find TruLens Tables

Look for tables created by TruLens:
- `TRULENS_RECORDS` - Root-level traces
- `TRULENS_SPANS` - Individual operation spans (LLM calls)
- `TRULENS_FEEDBACKS` - Evaluation/feedback data (if configured)

### 3. Query Traces

```sql
-- View all recent traces
SELECT * FROM YOUR_SCHEMA.TRULENS_RECORDS 
ORDER BY TIMESTAMP DESC 
LIMIT 10;

-- View LLM call spans
SELECT * FROM YOUR_SCHEMA.TRULENS_SPANS 
ORDER BY START_TIME DESC 
LIMIT 10;

-- See trace details with inputs/outputs
SELECT 
    RECORD_ID,
    TIMESTAMP,
    INPUT,
    OUTPUT,
    APP_ID
FROM YOUR_SCHEMA.TRULENS_RECORDS
WHERE APP_ID = 'movie_agent'
ORDER BY TIMESTAMP DESC;
```

## 🔍 Key Features

### ✅ Parallel Query Execution
- All 3 queries run concurrently using `asyncio.gather()`
- Faster overall execution
- Realistic concurrent trace recording

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
SnowflakeConnector
    ↓
MovieAgent (LangGraph)
    ↓
TruApp(agent, connector)
    ↓
live_run() context
    ↓
3 parallel queries (asyncio.gather)
    ↓
Traces → Snowflake Tables
```

## 🔗 Related Files

- `src/agent.py` - MovieAgent with `@instrument` decorators
- `src/server.py` - FastAPI server (also uses TruLens)
- `pyproject.toml` - Dependencies configuration

## 📝 Notes

- The `.env` file overrides system environment variables
- TruLens tables are created automatically on first run
- Each run has a timestamped name: `movie_rec_YYYY-MM-DD_HH-MM-SS`
- All traces from the 3 queries are grouped under one run

## 🎬 Next Steps

After running successfully:
1. Check Snowflake for trace tables
2. Query trace data for analysis
3. Integrate TruApp into other applications
4. Add evaluation feedback functions (optional)
5. Build dashboards using trace data

---

**Built with:** TruLens, Snowflake, LangGraph, AWS Bedrock, Python 3.12+

