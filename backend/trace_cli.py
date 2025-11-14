#!/usr/bin/env python3
"""
Simple CLI app for recording TruLens traces to Snowflake.

This app demonstrates how to configure TruLens to send instrumentation traces
to Snowflake. It uses the existing @instrument decorators in the MovieAgent
to automatically capture and record traces.

Required Environment Variables (in .env file):
    SNOWFLAKE_ACCOUNT: Your Snowflake account identifier
    SNOWFLAKE_USER: Snowflake username
    SNOWFLAKE_DATABASE: Database name for storing traces
    SNOWFLAKE_SCHEMA: Schema name for trace tables
    SNOWFLAKE_WAREHOUSE: Snowflake warehouse to use
    SNOWFLAKE_ROLE: Snowflake role (optional, default: SYSADMIN)
    TMDB_API_KEY: The Movie Database API key
    TAVILY_API_KEY: Tavily search API key
    AWS_REGION: AWS region for Bedrock (default: us-east-1)
    AWS_PROFILE: Optional AWS profile name

Note: Uses external browser authentication (SSO/OAuth) for Snowflake.
      A browser window will open for authentication.

Usage:
    python trace_cli.py
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the CLI app."""
    print("=" * 60)
    print("TruLens Snowflake Tracing CLI")
    print("=" * 60)
    print()

    # Load environment variables from .env file
    logger.info("Loading environment variables from .env file...")
    load_dotenv()

    # Check for required Snowflake environment variables
    required_snowflake_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_WAREHOUSE",
    ]

    missing_vars = [var for var in required_snowflake_vars if not os.getenv(var)]
    if missing_vars:
        logger.error("Missing required Snowflake environment variables:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("\nPlease add these to your .env file")
        sys.exit(1)

    # Check for required API keys
    required_api_vars = ["TMDB_API_KEY", "TAVILY_API_KEY"]
    missing_api_vars = [var for var in required_api_vars if not os.getenv(var)]
    if missing_api_vars:
        logger.error("Missing required API keys:")
        for var in missing_api_vars:
            logger.error(f"  - {var}")
        logger.error("\nPlease add these to your .env file")
        sys.exit(1)

    logger.info("✓ All required environment variables found")
    print()

    # Enable TruLens debug logging
    print("-" * 60)
    print("ENABLING DEBUG LOGGING")
    print("-" * 60)
    logging.getLogger("trulens").setLevel(logging.DEBUG)
    logging.getLogger("trulens.core").setLevel(logging.DEBUG)
    logging.getLogger("trulens.connectors").setLevel(logging.DEBUG)
    logging.getLogger("trulens.otel").setLevel(logging.DEBUG)
    logging.getLogger("trulens.providers").setLevel(logging.DEBUG)
    logger.info("✓ TruLens debug logging enabled")
    print()

    # Enable TruLens OTEL tracing
    os.environ["TRULENS_OTEL_TRACING"] = "1"
    logger.info("✓ Enabled TruLens OTEL tracing environment variable")
    print(f"  TRULENS_OTEL_TRACING = {os.environ.get('TRULENS_OTEL_TRACING')}")
    print()

    # Initialize TruLens with Snowflake connector
    logger.info("Initializing TruLens with Snowflake connector...")
    print("Note: A browser window will open for Snowflake authentication...")
    print()
    try:
        from trulens.connectors.snowflake import SnowflakeConnector
        from trulens.core import TruSession
        from snowflake.snowpark import Session

        # Configure Snowflake connection with SSO
        snowflake_config = {
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "authenticator": "externalbrowser",  # SSO authentication
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
            "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        }

        # Create Snowpark session with SSO
        logger.info("Creating Snowpark session with SSO authentication...")
        snowpark_session = Session.builder.configs(snowflake_config).create()
        logger.info("✓ Snowpark session created successfully")
        logger.info("✓ Authentication successful")
        print()

        # Verify Snowpark session
        print("-" * 60)
        print("SNOWPARK SESSION VERIFICATION")
        print("-" * 60)
        logger.info("Verifying Snowpark session configuration...")
        
        # Get current session info
        current_db = snowpark_session.get_current_database()
        current_schema = snowpark_session.get_current_schema()
        current_warehouse = snowpark_session.get_current_warehouse()
        current_role = snowpark_session.get_current_role()
        current_user = snowpark_session.get_current_user()
        
        print(f"  Connected User: {current_user}")
        print(f"  Current Role: {current_role}")
        print(f"  Current Warehouse: {current_warehouse}")
        print(f"  Current Database: {current_db}")
        print(f"  Current Schema: {current_schema}")
        
        # Test query to verify connection
        logger.info("Testing Snowpark connection with simple query...")
        test_result = snowpark_session.sql("SELECT CURRENT_TIMESTAMP() as now").collect()
        logger.info(f"✓ Connection test successful: {test_result[0]['NOW']}")
        
        # Check if TruLens tables exist
        logger.info("Checking for existing TruLens tables...")
        check_tables_query = f"""
        SELECT TABLE_NAME 
        FROM {current_db}.INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = '{current_schema}' 
        AND TABLE_NAME LIKE 'TRULENS%'
        ORDER BY TABLE_NAME
        """
        existing_tables = snowpark_session.sql(check_tables_query).collect()
        
        if existing_tables:
            print(f"\n  Found {len(existing_tables)} TruLens table(s):")
            for row in existing_tables:
                print(f"    - {row['TABLE_NAME']}")
        else:
            print("  ⚠ No TruLens tables found yet (will be created on first trace)")
        
        print()
        logger.info("✓ Snowpark session verification complete")

        # Initialize TruLens connector with the Snowpark session
        print("-" * 60)
        print("TRULENS CONNECTOR DIAGNOSTICS")
        print("-" * 60)
        logger.info("Initializing TruLens SnowflakeConnector...")
        
        connector = SnowflakeConnector(snowpark_session=snowpark_session)
        logger.info("✓ TruLens connector initialized")
        
        # Log connector details
        print(f"  Connector Type: {type(connector).__name__}")
        print(f"  Connector Module: {type(connector).__module__}")
        
        # Check if connector has expected attributes
        logger.info("Verifying connector attributes...")
        if hasattr(connector, 'session'):
            print(f"  ✓ Connector has session attribute")
        if hasattr(connector, 'snowpark_session'):
            print(f"  ✓ Connector has snowpark_session attribute")
        
        # Initialize TruLens session with Snowflake connector
        logger.info("Initializing TruSession with connector...")
        session = TruSession(connector=connector)
        logger.info("✓ TruLens session initialized")
        
        # Log session details
        print(f"  Session Type: {type(session).__name__}")
        print(f"  Session Connector: {type(session.connector).__name__}")
        
        # Verify OTEL tracing is enabled
        otel_enabled = os.environ.get("TRULENS_OTEL_TRACING")
        print(f"  OTEL Tracing Enabled: {otel_enabled}")
        
        print()
        logger.info("✓ TruLens configured to send traces to Snowflake")
        print("Configuration Summary:")
        print(f"  Account: {os.getenv('SNOWFLAKE_ACCOUNT')}")
        print(f"  Database: {os.getenv('SNOWFLAKE_DATABASE')}")
        print(f"  Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
        print()

    except Exception as e:
        logger.error(f"Failed to initialize TruLens with Snowflake: {e}")
        logger.error("Make sure Snowflake credentials are correct")
        sys.exit(1)

    # Create the MovieAgent
    logger.info("Creating MovieAgent with TruLens instrumentation...")
    try:
        from src.agent import create_movie_agent

        agent = create_movie_agent(
            tmdb_api_key=os.getenv("TMDB_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_profile=os.getenv("AWS_PROFILE"),
        )
        logger.info("✓ MovieAgent created successfully")
        print()

    except Exception as e:
        logger.error(f"Failed to create MovieAgent: {e}")
        sys.exit(1)

    # Run a simple recommendation to generate traces
    logger.info("Running movie recommendation to generate traces...")
    print("Prompt: 'Recommend a good sci-fi movie'")
    print()

    try:
        # Run async recommendation
        result = asyncio.run(
            agent.aget_recommendations("Recommend a good sci-fi movie")
        )

        if result.get("success"):
            logger.info("✓ Recommendation completed successfully")
            print("-" * 60)
            print("RESPONSE:")
            print("-" * 60)
            print(result.get("response"))
            print("-" * 60)
            print()
        else:
            logger.error(f"Recommendation failed: {result.get('error')}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during recommendation: {e}")
        sys.exit(1)

    # Confirmation
    print()
    print("=" * 60)
    logger.info("✓ Traces have been recorded to Snowflake!")
    print("=" * 60)
    print()
    print("Check your Snowflake database for trace records:")
    print(f"  Database: {os.getenv('SNOWFLAKE_DATABASE')}")
    print(f"  Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
    print()
    print("TruLens automatically captured:")
    print("  - LLM generation spans from _call_model()")
    print("  - Root record from aget_recommendations()")
    print("  - Input/output data and metadata")
    print()


if __name__ == "__main__":
    main()

