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
import traceback
import numpy as np
from dotenv import load_dotenv

# Custom filter to suppress tracebacks from specific loggers
class SuppressTraceback(logging.Filter):
    def filter(self, record):
        # Suppress exc_info (traceback) for TruLens loggers
        if record.name.startswith('trulens'):
            record.exc_info = None
            record.exc_text = None
        return True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add traceback suppression filter to root logger
logging.root.addFilter(SuppressTraceback())


def main():
    """Main entry point for the CLI app."""
    print("=" * 60)
    print("TruLens Snowflake Tracing CLI")
    print("=" * 60)
    print()

    # Load environment variables from .env file
    logger.info("Loading environment variables from .env file...")
    load_dotenv(override=True)

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

    # Configure TruLens logging (reduce connector noise)
    # Set connectors and core.app to CRITICAL to suppress error tracebacks
    logging.getLogger("trulens").setLevel(logging.WARNING)  # Reduce general trulens noise
    logging.getLogger("trulens.core").setLevel(logging.WARNING)
    logging.getLogger("trulens.core.app").setLevel(logging.CRITICAL)  # Suppress app tracebacks
    logging.getLogger("trulens.connectors").setLevel(logging.CRITICAL)  # Suppress connector logs
    logging.getLogger("trulens.connectors.snowflake").setLevel(logging.CRITICAL)  # Suppress tracebacks
    logging.getLogger("trulens.connectors.snowflake.dao").setLevel(logging.CRITICAL)  # Suppress DAO errors
    logging.getLogger("trulens.otel").setLevel(logging.WARNING)
    logging.getLogger("trulens.providers").setLevel(logging.WARNING)
    logger.info("✓ TruLens logging configured (tracebacks suppressed)")

    # Enable TruLens debug logging if requested
    if os.getenv("DEBUG_TRULENS", "").lower() == "true":
        logging.getLogger("trulens").setLevel(logging.DEBUG)
        logging.getLogger("trulens.core").setLevel(logging.DEBUG)
        logging.getLogger("trulens.connectors").setLevel(logging.DEBUG)
        logging.getLogger("trulens.providers").setLevel(logging.DEBUG)
        logger.info("✓ TruLens debug logging enabled (DEBUG_TRULENS=true)")

    # Check TruLens OTEL tracing configuration (default: enabled)
    # User can set TRULENS_OTEL_TRACING=false in .env to disable
    otel_tracing_enabled = os.getenv("TRULENS_OTEL_TRACING", "true").lower() == "true"
    
    if otel_tracing_enabled:
        logger.info("✓ TruLens OTEL tracing enabled (TRULENS_OTEL_TRACING=true)")
        logger.info("  @instrument decorators will capture traces")
    else:
        logger.warning("⚠️  TruLens OTEL tracing disabled (TRULENS_OTEL_TRACING=false)")
        logger.warning("   @instrument decorators will not capture traces")

    # Initialize TruLens with Snowflake connector
    logger.info("Initializing TruLens with Snowflake connector...")
    logger.info("Note: A browser window will open for Snowflake authentication")
    try:
        from trulens.connectors.snowflake import SnowflakeConnector
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
        
        # Configure use_account_event_table based on environment variable
        # Both modes use OTEL tracing (@instrument decorators), but differ in storage:
        # False (default): OTEL traces → TruLens traditional tables (supports feedback evaluation)
        # True: OTEL traces → Snowflake native event tables (OpenTelemetry format, no feedback support)
        use_account_event_table = os.getenv("TRULENS_USE_ACCOUNT_EVENT_TABLE", "false").lower() == "true"
        
        connector = SnowflakeConnector(
            snowpark_session=snowpark_session,
            use_account_event_table=use_account_event_table
        )
        
        if use_account_event_table:
            logger.info("✓ TruLens connector created (using Snowflake native OTEL event tables)")
            logger.info("  OTEL traces will be stored in native OpenTelemetry format")
            logger.warning("  Note: Feedback evaluation is NOT supported with account event tables")
        else:
            logger.info("✓ TruLens connector created (using traditional TruLens tables)")
            logger.info("  OTEL traces + feedback results will be stored in TruLens schema")
        
        # Log connector details
        print(f"  Connector Type: {type(connector).__name__}")
        print(f"  Connector Module: {type(connector).__module__}")
        
        # Check if connector has expected attributes
        logger.info("Verifying connector attributes...")
        if hasattr(connector, 'session'):
            print(f"  ✓ Connector has session attribute")
        if hasattr(connector, 'snowpark_session'):
            print(f"  ✓ Connector has snowpark_session attribute")
        
        # Verify OTEL tracing is enabled
        otel_enabled = os.environ.get("TRULENS_OTEL_TRACING")
        print(f"  OTEL Tracing Enabled: {otel_enabled}")
        
        # Display table mode for OTEL traces
        table_mode = "Snowflake native OTEL event tables (traces only)" if use_account_event_table else "Traditional TruLens tables (OTEL traces + feedbacks)"
        print(f"  Table Mode: {table_mode}")
        
        print()
        logger.info("✓ SnowflakeConnector ready (will be passed to TruGraph)")
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

    # Create LLM-based and ground truth feedback functions (using Bedrock Claude as judge)
    # NOTE: These use an LLM to evaluate response quality - each evaluation costs an API call
    ground_truth_feedbacks = []
    llm_feedbacks = []
    enable_llm_evals = os.getenv("ENABLE_EVALUATIONS", "false").lower() == "true"
    
    if enable_llm_evals:
        logger.info("Evaluations enabled - creating feedback functions (ground truth + LLM-based)...")
        
        # Load MS MARCO BEIR dataset for ground truth evaluation demonstration
        # NOTE: This is for educational/demonstration purposes only.
        # The MovieAgent uses API calls (TMDB, Tavily) rather than traditional document retrieval,
        # so IR metrics like NDCG@k are not directly applicable to the agent's architecture.
        # This section demonstrates TruLens ground truth evaluation capabilities.
        logger.info("Loading MS MARCO BEIR dataset for ground truth demonstration...")
        msmarco_sample = None
        try:
            from trulens.benchmark.benchmark_frameworks.dataset.beir_loader import (
                TruBEIRDataLoader,
            )

            # Load a small subset of MS MARCO for demonstration
            beir_loader = TruBEIRDataLoader(
                data_folder="./beir_data", dataset_name="msmarco"
            )
            
            logger.info("Downloading MS MARCO dataset (this may take a moment on first run)...")
            msmarco_df = beir_loader.load_dataset_to_df(download=True)
            
            # Use only first 10 samples for quick demonstration
            msmarco_sample = msmarco_df.head(10)
            
            logger.info(f"✓ Loaded {len(msmarco_sample)} MS MARCO samples for demonstration")
            print(f"  Sample queries from MS MARCO:")
            for idx, row in msmarco_sample.head(3).iterrows():
                print(f"    - {row.get('query', 'N/A')}")
            print()

        except Exception as e:
            logger.warning(f"Failed to load MS MARCO dataset: {e}")
            logger.warning("Continuing without ground truth evaluation")
        
        # Create ground truth feedback functions if MS MARCO loaded successfully
        if msmarco_sample is not None:
            try:
                from trulens.core import Feedback
                from trulens.feedback import GroundTruthAgreement
                from trulens.providers.bedrock import Bedrock as BedrockGT

                logger.info("Creating ground truth feedback functions for demonstration...")
                logger.info("Using Bedrock (Claude) as LLM judge for ground truth evaluation")

                # Initialize Bedrock provider for ground truth evaluation
                bedrock_gt_provider = BedrockGT(
                    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                    region_name=os.getenv("AWS_REGION", "us-east-1"),
                )
                
                # Create GroundTruthAgreement with MS MARCO dataset
                # MS MARCO DataFrame has columns: query, expected_response, expected_chunks
                # This measures semantic similarity between agent response and ground truth
                ground_truth_agreement = GroundTruthAgreement(
                    msmarco_sample, 
                    provider=bedrock_gt_provider
                )
                
                # Standard pattern: use .on_input_output() for input/output comparison
                # This automatically maps to the root span's input/output
                f_groundtruth_answer = Feedback(
                    ground_truth_agreement.agreement_measure,
                    name="Ground Truth Answer Similarity (Demo)",
                ).on_input_output()

                ground_truth_feedbacks = [f_groundtruth_answer]
                
                logger.info(f"✓ Created {len(ground_truth_feedbacks)} ground truth feedback function(s): {[f.name for f in ground_truth_feedbacks]}")

            except Exception as e:
                logger.warning(f"Failed to create ground truth feedbacks: {e}")
                logger.warning("Continuing without ground truth feedback functions")
        
        # Create LLM-based feedback functions
        try:
            from trulens.providers.bedrock import Bedrock
            from trulens.otel.semconv.trace import SpanAttributes
            
            # Initialize Bedrock provider as the judge LLM
            bedrock_judge = Bedrock(
                model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
            )
            
            logger.info("✓ Bedrock judge LLM initialized")
            
            # Answer Relevance: Does the recommendation address the user's query?
            f_relevance = Feedback(
                bedrock_judge.relevance,
                name="Movie Recommendation Relevance",
            ).on_input_output()
            
            # Helpfulness: Is the recommendation helpful and actionable?
            f_helpfulness = Feedback(
                bedrock_judge.helpfulness,
                name="Recommendation Helpfulness",
            ).on_output()
            
            # Conciseness: Is the response clear and not overly verbose?
            f_conciseness = Feedback(
                bedrock_judge.conciseness,
                name="Response Conciseness",
            ).on_output()
            
            # Groundedness: Is the recommendation grounded in retrieved contexts?
            # This uses OTEL selectors to get contexts from RETRIEVAL spans
            from trulens.core.feedback.selector import Selector
            
            f_groundedness = (
                Feedback(
                    bedrock_judge.groundedness_measure_with_cot_reasons_consider_answerability,
                    name="Movie Recommendation Groundedness",
                )
                .on({
                    "source": Selector(
                        span_type=SpanAttributes.SpanType.RETRIEVAL,
                        span_attribute=SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS,
                        collect_list=True
                    )
                })
                .on({
                    "statement": Selector(
                        span_type=SpanAttributes.SpanType.RECORD_ROOT,
                        span_attribute=SpanAttributes.RECORD_ROOT.OUTPUT,
                    )
                })
                .on({
                    "question": Selector(
                        span_type=SpanAttributes.SpanType.RECORD_ROOT,
                        span_attribute=SpanAttributes.RECORD_ROOT.INPUT,
                    )
                })
            )
            
            # Retrieval Context Relevance: Evaluates quality of RETRIEVAL spans
            # This targets all RETRIEVAL spans (from websearch, tmdb tools) and evaluates
            # whether the retrieved contexts are relevant to the query
            f_retrieval_relevance = (
                Feedback(
                    bedrock_judge.context_relevance_with_cot_reasons,
                    name="Retrieval Context Relevance",
                )
                .on({
                    "question": Selector(
                        span_type=SpanAttributes.SpanType.RETRIEVAL,
                        span_attribute=SpanAttributes.RETRIEVAL.QUERY_TEXT,
                    )
                })
                .on({
                    "context": Selector(
                        span_type=SpanAttributes.SpanType.RETRIEVAL,
                        span_attribute=SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS,
                    )
                })
                .aggregate(np.mean)
            )
            
            llm_feedbacks = [f_relevance, f_helpfulness, f_conciseness, f_groundedness, f_retrieval_relevance]
            
            logger.info(f"✓ Created {len(llm_feedbacks)} LLM-based feedback function(s): {[f.name for f in llm_feedbacks]}")
            logger.info("Judge LLM: Claude 3.5 Sonnet (Bedrock)")
            logger.warning("⚠️  Each evaluation makes an LLM API call (cost applies)")
            
        except Exception as e:
            logger.warning(f"Failed to create LLM-based feedbacks: {e}")
            logger.warning("Continuing without LLM feedback functions")
            llm_feedbacks = []
    else:
        logger.info("Evaluations disabled (set ENABLE_EVALUATIONS=true in .env to enable)")
        logger.info("  Note: This disables both ground truth and LLM-based feedback evaluations")

    # Combine all feedbacks (ground truth + LLM-based)
    all_feedbacks = ground_truth_feedbacks + llm_feedbacks
    
    # Check if feedbacks are compatible with current table mode
    if all_feedbacks and use_account_event_table:
        logger.warning("⚠️  Feedback functions configured but OTEL + account event tables mode is enabled")
        logger.warning("   TruLens limitation: Feedback evaluation NOT supported with OTEL + native event tables")
        logger.warning("   Set TRULENS_USE_ACCOUNT_EVENT_TABLE=false to enable OTEL traces + feedbacks")
        logger.warning("   Disabling feedbacks to avoid initialization errors")
        all_feedbacks = []
    elif all_feedbacks:
        logger.info(f"Total feedbacks configured: {len(all_feedbacks)}")
        logger.info(f"  Feedbacks will be evaluated during live_run()")

    # Wrap agent with TruGraph (LangGraph-specific recorder)
    logger.info("Wrapping agent with TruGraph for trace recording...")
    try:
        from trulens.apps.langgraph import TruGraph
        from datetime import datetime

        tru_app = TruGraph(
            agent,
            app_name="movie_agent",
            app_version="v1",
            connector=connector,
            feedbacks=all_feedbacks
        )
        logger.info("✓ TruGraph wrapper created successfully (app_name=movie_agent, version=v1)")
        logger.info(f"Connector: {type(connector).__name__}")
        if all_feedbacks:
            logger.info(f"Total Feedbacks: {len(all_feedbacks)}")
            for fb in all_feedbacks:
                logger.info(f"  - {fb.name}")

    except Exception as e:
        logger.error(f"Failed to create TruGraph wrapper: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Run multiple movie recommendations to generate traces
    logger.info("Running movie recommendations to generate traces...")
    print()

    # Create timestamped run name
    run_name = f"movie_rec_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
    logger.info(f"Using run name: {run_name}")
    print()

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

        # Define async function to run within live_run context
        async def run_recommendations():
            with tru_app.live_run(run_name=run_name) as live_run:
                logger.info(f"✓ Live run context started (run_id: {live_run.run_id if hasattr(live_run, 'run_id') else 'N/A'})")
                
                print(f"\n{'=' * 60}")
                print(f"RUNNING {len(queries)} QUERIES IN PARALLEL")
                print("=" * 60)
                print()
                
                # Run all queries in parallel using asyncio.gather
                logger.info("Executing all queries concurrently...")
                tasks = [process_query(query, i+1) for i, query in enumerate(queries)]
                results = await asyncio.gather(*tasks)
                
                logger.info("✓ All queries completed")
                print()
                
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
                        print()
                    else:
                        logger.error(f"Query {index} failed: {result.get('error')}")
                        all_success = False
                
                return all_success

        # Run async recommendations within TruGraph live_run context
        success = asyncio.run(run_recommendations())

        if not success:
            logger.error("One or more recommendations failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during recommendations: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Confirmation
    print()
    print("=" * 60)
    logger.info("🎉 Traces have been recorded to Snowflake!")
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

