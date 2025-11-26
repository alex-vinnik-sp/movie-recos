#!/usr/bin/env python3
"""
Simple CLI app for testing OpenLit observability with the movie recommendation agent.

This app demonstrates how OpenLit auto-instruments LangChain/LangGraph applications
to automatically capture and send traces to the OpenLit backend via OpenTelemetry.

Required Environment Variables (in .env file):
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint for OpenLit (default: http://127.0.0.1:4318)
    TMDB_API_KEY: The Movie Database API key
    TAVILY_API_KEY: Tavily search API key
    AWS_REGION: AWS region for Bedrock (default: us-east-1)
    AWS_PROFILE: Optional AWS profile name

Usage:
    python trace_cli.py
"""

import asyncio
import logging
import os
import sys
import traceback
from dotenv import load_dotenv
import openlit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("Logger keys:", list(logging.root.manager.loggerDict.keys()))

# Set DEBUG level
import re

pattern = re.compile(r"^(opentelemetry|openlit|httpx)")
for logger_name in list(logging.root.manager.loggerDict.keys()):
    if pattern.match(logger_name):
        logging.getLogger(logger_name).setLevel(logging.DEBUG)


def main():
    """Main entry point for the CLI app."""
    print("=" * 60)
    print("OpenLit Movie Agent Observability CLI")
    print("=" * 60)

    # Load environment variables from .env file
    logger.info("Loading environment variables from .env file...")
    load_dotenv(override=True)

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

    # Initialize OpenLit for LLM observability
    logger.info("Initializing OpenLit for LLM observability...")
    try:       
        # Initialize OpenLit with auto-instrumentation for LangGraph/Bedrock
        # Note: Disabling langchain instrumentor due to compatibility issues with langchain.hub
        openlit.init(
            application_name="movie-recommendations-cli",
            disabled_instrumentors=["langchain"]
        )
        
        logger.info("✓ OpenLit initialized successfully")
        logger.info("  Auto-instrumentation enabled for:")
        logger.info("    - LangGraph")
        logger.info("    - AWS Bedrock")
        
    except Exception as e:
        logger.error(f"Failed to initialize OpenLit: {e}")
        logger.error("Make sure OpenLit is installed: pip install openlit")
        sys.exit(1)

    # Create the MovieAgent
    # OpenLit will automatically instrument LangChain/LangGraph without any wrappers
    logger.info("Creating MovieAgent...")
    try:
        from src.agent import create_movie_agent

        agent = create_movie_agent(
            tmdb_api_key=os.getenv("TMDB_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            aws_profile=os.getenv("AWS_PROFILE"),
        )
        logger.info("✓ MovieAgent created successfully")
        logger.info("  OpenLit will automatically capture:")
        logger.info("    - LLM calls (AWS Bedrock)")
        logger.info("    - LangGraph execution traces")
        logger.info("    - Tool invocations")
        logger.info("    - Latency and token usage metrics")

    except Exception as e:
        logger.error(f"Failed to create MovieAgent: {e}")
        sys.exit(1)

    # Run multiple movie recommendations to generate traces
    # OpenLit will automatically capture all traces and send them to the OTLP endpoint
    logger.info("Running movie recommendations (OpenLit will auto-capture traces)...")

    # Define movie queries (add more queries to the list to run them in parallel)
    queries = [
        "Recommend a good sci-fi movie",
        # "What are some great comedy movies from the 2020s?",
        # "Suggest a thriller movie with a twist ending"
    ]

    try:
        # Define async function to process a single query
        async def process_query(query, index):
            """Process a single query and return result with index."""
            logger.info(f"🔍 Starting query {index}: {query}")
            result = await agent.aget_recommendations(query)
            return (index, query, result)

        # Define async function to run recommendations
        async def run_recommendations():
            print(f"\n{'=' * 60}")
            print(f"RUNNING {len(queries)} QUERIES IN PARALLEL")
            print("=" * 60)
            
            # Run all queries in parallel using asyncio.gather
            logger.info("Executing all queries concurrently...")
            tasks = [process_query(query, i+1) for i, query in enumerate(queries)]
            results = await asyncio.gather(*tasks)
            
            logger.info("✓ All queries completed")
            
            # Display results in order
            all_success = True
            for index, query, result in results:
                print(f"\n{'=' * 60}")
                print(f"QUERY {index}/{len(queries)}: {query}")
                print("=" * 60)
                
                if result.get("success"):
                    logger.info(f"✓ Query {index} successful")
                    print("-" * 60)
                    print("RESPONSE:")
                    print("-" * 60)
                    print(result.get("response"))
                    print("-" * 60)
                else:
                    logger.error(f"Query {index} failed: {result.get('error')}")
                    all_success = False
            
            return all_success

        # Run async recommendations
        success = asyncio.run(run_recommendations())

        if not success:
            logger.error("One or more recommendations failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during recommendations: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Confirmation
    print("=" * 60)
    logger.info("🎉 Traces have been recorded to OpenLit!")
    print("=" * 60)
    print("View traces and metrics in OpenLit UI:")
    print(f"  OpenLit UI: http://127.0.0.1:3000")
    print(f"  OTLP Endpoint: {os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://127.0.0.1:4318')}")
    print("OpenLit automatically captured:")
    print("  - LLM calls (prompts, completions, tokens)")
    print("  - LangGraph execution traces")
    print("  - Tool invocations (TMDB, Tavily)")
    print("  - Latency and performance metrics")
    print("  - Cost tracking")


if __name__ == "__main__":
    main()

