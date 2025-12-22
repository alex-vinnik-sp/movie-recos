#!/usr/bin/env python3
"""
Batch processing CLI for movie recommendations with LangSmith tracing.

This script processes multiple movie recommendation queries using the MovieAgent
with LangSmith tracing enabled. Queries can be provided via command line arguments,
a file, or standard input.

Usage:
    python trace_cli.py "action movies like John Wick"
    python trace_cli.py "romantic comedies" "sci-fi movies" "horror films"
    python trace_cli.py --queries-file queries.txt
    echo "action movies" | python trace_cli.py --stdin
"""

import argparse
import asyncio
import logging
import sys
import os
from typing import List

from dotenv import load_dotenv

from src.agent import create_movie_agent

# Load environment variables
load_dotenv(override=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def configure_langsmith():
    """Configure LangSmith tracing."""
    if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        if os.getenv("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
        if os.getenv("LANGCHAIN_PROJECT"):
            os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
        logger.info("LangSmith tracing enabled")
        return True
    else:
        logger.warning("LangSmith tracing not enabled (LANGCHAIN_TRACING_V2 not set to 'true')")
        return False


def validate_environment():
    """Validate required environment variables."""
    required_vars = ["TMDB_API_KEY", "TAVILY_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please create a .env file with the required variables"
        )
    
    logger.info("All required environment variables are present")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Batch process movie recommendation queries with LangSmith tracing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trace_cli.py "action movies like John Wick"
  python trace_cli.py "romantic comedies" "sci-fi movies" "horror films"
  python trace_cli.py --queries-file queries.txt
  echo "action movies" | python trace_cli.py --stdin
        """
    )
    
    # Mutually exclusive group for input methods
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "--queries-file",
        type=str,
        help="Path to file containing queries (one per line)"
    )
    input_group.add_argument(
        "--stdin",
        action="store_true",
        help="Read queries from standard input (one per line)"
    )
    
    # Positional arguments for queries
    parser.add_argument(
        "queries",
        nargs="*",
        help="Movie recommendation queries (ignored if --queries-file or --stdin is used)"
    )
    
    return parser.parse_args()


def load_queries(args) -> List[str]:
    """Load queries from various input sources."""
    queries = []
    
    if args.queries_file:
        logger.info(f"Loading queries from file: {args.queries_file}")
        try:
            with open(args.queries_file, 'r', encoding='utf-8') as f:
                queries = [line.strip() for line in f if line.strip()]
            logger.info(f"Loaded {len(queries)} queries from file")
        except FileNotFoundError:
            logger.error(f"File not found: {args.queries_file}")
            raise
        except Exception as e:
            logger.error(f"Error reading file {args.queries_file}: {e}")
            raise
    elif args.stdin:
        logger.info("Reading queries from standard input")
        try:
            queries = [line.strip() for line in sys.stdin if line.strip()]
            logger.info(f"Loaded {len(queries)} queries from stdin")
        except Exception as e:
            logger.error(f"Error reading from stdin: {e}")
            raise
    else:
        queries = args.queries
        if queries:
            logger.info(f"Using {len(queries)} queries from command line arguments")
    
    if not queries:
        logger.error("No queries provided")
        raise ValueError("No queries provided. Use command line arguments, --queries-file, or --stdin")
    
    return queries


async def process_query(agent, query: str, query_num: int, total: int, index: int) -> dict:
    """Process a single query and return result."""
    logger.info(f"Processing query {query_num}/{total}: '{query[:50]}{'...' if len(query) > 50 else ''}'")
    
    try:
        result = await agent.aget_recommendations(query)
        
        if result["success"]:
            logger.info(f"Query {query_num}/{total} completed successfully")
            return {
                "index": index,
                "query": query,
                "success": True,
                "response": result["response"]
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Query {query_num}/{total} failed: {error_msg}")
            return {
                "index": index,
                "query": query,
                "success": False,
                "error": error_msg
            }
    except Exception as e:
        logger.error(f"Query {query_num}/{total} raised exception: {e}", exc_info=True)
        return {
            "index": index,
            "query": query,
            "success": False,
            "error": str(e)
        }


async def process_batch(agent, queries: List[str]) -> List[dict]:
    """Process all queries in parallel."""
    total = len(queries)
    logger.info(f"Starting parallel batch processing of {total} queries")
    
    # Create tasks for all queries to run in parallel
    tasks = [
        process_query(agent, query, i, total, i - 1)
        for i, query in enumerate(queries, start=1)
    ]
    
    # Run all queries in parallel
    results = await asyncio.gather(*tasks)
    
    # Sort results by index to maintain original order
    results.sort(key=lambda x: x["index"])
    
    return results


def print_results(results: List[dict]):
    """Print formatted results to stdout."""
    total = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total - successful
    
    print(f"\n{'='*60}")
    print(f"BATCH PROCESSING RESULTS")
    print(f"{'='*60}\n")
    
    for i, result in enumerate(results, start=1):
        print(f"Query {i}/{total}: {result['query']}")
        print(f"{'-'*60}")
        
        if result["success"]:
            print("RESPONSE:")
            print(result["response"])
        else:
            print(f"ERROR: {result['error']}")
        
        print()
    
    print(f"{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total queries: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Success rate: {(successful/total*100):.1f}%")
    print(f"{'='*60}\n")


async def main():
    """Main async function."""
    try:
        # Configure LangSmith
        langsmith_enabled = configure_langsmith()
        if not langsmith_enabled:
            logger.warning("LangSmith tracing is not enabled. Traces will not be recorded.")
        
        # Validate environment
        validate_environment()
        
        # Parse arguments
        args = parse_arguments()
        
        # Load queries
        queries = load_queries(args)
        
        # Initialize agent
        logger.info("Initializing MovieAgent")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        agent = create_movie_agent(
            tmdb_api_key=os.getenv("TMDB_API_KEY"),
            tavily_api_key=os.getenv("TAVILY_API_KEY"),
            aws_region=aws_region
        )
        logger.info("MovieAgent initialized successfully")
        
        # Process queries
        results = await process_batch(agent, queries)
        
        # Print results
        print_results(results)
        
        # Log completion
        successful = sum(1 for r in results if r["success"])
        logger.info(f"Batch processing complete: {successful}/{len(results)} successful")
        
        if langsmith_enabled:
            logger.info("Traces have been recorded in LangSmith")
            if os.getenv("LANGCHAIN_PROJECT"):
                logger.info(f"Project: {os.getenv('LANGCHAIN_PROJECT')}")
        
        # Exit with error code if any queries failed
        if successful < len(results):
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

