#!/usr/bin/env python3
"""
CLI to compute metrics for an existing TruLens run.

This script retrieves an existing run and computes offline metrics using
feedback definitions already stored in the database.

Required Environment Variables (in .env file):
    SNOWFLAKE_ACCOUNT: Your Snowflake account identifier
    SNOWFLAKE_USER: Snowflake username
    SNOWFLAKE_DATABASE: Database name for storing traces
    SNOWFLAKE_SCHEMA: Schema name for trace tables
    SNOWFLAKE_WAREHOUSE: Snowflake warehouse to use
    SNOWFLAKE_ROLE: Snowflake role (optional, default: SYSADMIN)
    AWS_REGION: AWS region for Bedrock (default: us-east-1)

Usage:
    uv run compute_metrics_cli.py
"""

import os
import time
import logging

from dotenv import load_dotenv
from snowflake.snowpark import Session
from langchain_aws import ChatBedrock
from langgraph.graph import END, MessagesState, StateGraph

from trulens.apps.langgraph import TruGraph
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.core.run import RunStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_snowpark_session() -> Session:
    """Create Snowpark session with conditional authentication."""
    # Configure Snowflake connection with conditional authentication
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")
    
    snowflake_config = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
    }
    
    # Add authentication method based on environment
    if snowflake_password:
        snowflake_config["password"] = snowflake_password
    else:
        snowflake_config["authenticator"] = "externalbrowser"
    
    snowpark_session = Session.builder.configs(snowflake_config).create()
    return snowpark_session


def main():
    """Main entry point for the CLI."""
    logger.info("=" * 60)
    logger.info("Compute Metrics CLI for Existing Run")
    logger.info("=" * 60)
    
    # Load environment variables from .env file
    load_dotenv(override=True)
    
    # Check for required Snowflake environment variables
    required_vars = [
        "SNOWFLAKE_ACCOUNT",
        "SNOWFLAKE_USER",
        "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA",
        "SNOWFLAKE_WAREHOUSE",
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please add these to your .env file")
        return
    
    logger.info("✓ All required environment variables found")
    
    # Create Snowpark session and connector
    logger.info("Creating Snowpark session...")
    snowpark_session = create_snowpark_session()
    logger.info("✓ Snowpark session created")
    
    use_account_event_table = os.getenv("TRULENS_USE_ACCOUNT_EVENT_TABLE", "false").lower() == "true"
    connector = SnowflakeConnector(
        snowpark_session=snowpark_session,
        use_account_event_table=use_account_event_table
    )
    logger.info("✓ Snowflake connector initialized")
    
    # Create minimal dummy graph (just to satisfy TruGraph requirements)
    logger.info("Creating minimal graph wrapper...")
    llm = ChatBedrock(
        model="anthropic.claude-3-5-sonnet-20240620-v1:0",
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
    workflow = StateGraph(MessagesState)
    workflow.add_node("chat", lambda state: {"messages": [llm.invoke(state["messages"])]})
    workflow.add_edge("chat", END)
    workflow.set_entry_point("chat")
    graph = workflow.compile()
    
    # Create TruGraph without feedbacks (offline evaluation uses stored definitions)
    logger.info("Creating TruGraph wrapper...")
    tru_app = TruGraph(
        graph,
        app_name="movie_agent",  # Must match original run
        app_version="v1",        # Must match original run
        connector=connector
        # NO feedbacks parameter - using stored feedback definitions from database
    )
    logger.info("✓ TruGraph wrapper created")
    
    # Hardcoded run name
    run_name = "movie_rec_2025-12-03_19-20-37"
    logger.info("=" * 60)
    logger.info(f"Retrieving run: {run_name}")
    logger.info("=" * 60)
    
    # Get existing run
    try:
        run = tru_app.get_run(run_name=run_name)
        logger.info(f"✓ Run retrieved: {run_name}")
    except Exception as e:
        logger.error(f"Failed to retrieve run: {e}")
        logger.error("Make sure the run exists in the database")
        return
    
    # Wait up to 3 minutes for INVOCATION_COMPLETED
    timeout = 180
    elapsed = 0
    logger.info("Waiting for invocation completion...")
    
    while (status := run.get_status()) != RunStatus.INVOCATION_COMPLETED:
        if elapsed >= timeout:
            logger.warning(f"Timeout after {timeout}s. Status: {status}")
            logger.warning("Skipping metric computation.")
            logger.warning("The run may still be processing. Try again later.")
            return
        
        logger.info(f"Run status: {status} (elapsed: {elapsed}s)")
        time.sleep(30)
        elapsed += 30
    
    logger.info(f"✓ Run status: {status}")
    
    # Compute offline metrics using stored feedback definitions
    logger.info("=" * 60)
    logger.info("Computing offline metrics...")
    logger.info("Using stored feedback definitions from database")
    logger.info("=" * 60)
    
    try:
        metric_status = run.compute_metrics(
            metrics=["answer_relevance", "helpfulness", "conciseness"]
        )
        logger.info(f"✓ Metrics computation status: {metric_status}")
        logger.info("=" * 60)
        logger.info("Check Snowflake for results:")
        logger.info(f"  Database: {os.getenv('SNOWFLAKE_DATABASE')}")
        logger.info(f"  Schema: {os.getenv('SNOWFLAKE_SCHEMA')}")
        logger.info("  Table: TRULENS_FEEDBACKS")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Failed to compute metrics: {e}")
        logger.error("Check that feedback definitions exist in the database")


if __name__ == "__main__":
    main()

