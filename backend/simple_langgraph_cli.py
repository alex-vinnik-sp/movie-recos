#!/usr/bin/env python3
"""
Simple LangGraph CLI with TruGraph and Snowflake tracing.

Follows the TruGraph documentation pattern for a minimal chat agent.

Required Environment Variables (in .env file):
    SNOWFLAKE_ACCOUNT: Your Snowflake account identifier
    SNOWFLAKE_USER: Snowflake username
    SNOWFLAKE_DATABASE: Database name for storing traces
    SNOWFLAKE_SCHEMA: Schema name for trace tables
    SNOWFLAKE_WAREHOUSE: Snowflake warehouse to use
    AWS_REGION: AWS region for Bedrock (default: us-east-1)
    AWS_PROFILE: Optional AWS profile name

Usage:
    uv run simple_langgraph_cli.py                # Use Cortex (default)
    uv run simple_langgraph_cli.py --llm bedrock  # Use Bedrock
"""

import os
# Disable LangChain/LangGraph native tracing to avoid conflicts
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGGRAPH_TRACING_ENABLED"] = "false"

import argparse
import logging
import time
from datetime import datetime

from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.graph import END, MessagesState, StateGraph
from snowflake.cortex import CompleteOptions, complete
from snowflake.snowpark import Session

from trulens.apps.langgraph import TruGraph
from trulens.connectors.snowflake import SnowflakeConnector
from trulens.core.run import RunStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ChatSnowflakeCortex(BaseChatModel):
    """Custom LangChain chat model wrapper for Snowflake Cortex.
    
    Uses the same underlying API as trulens.providers.cortex.Cortex,
    but implements LangChain's chat model interface for LangGraph compatibility.
    """
    
    session: object  # Snowpark Session
    model: str = "llama3.1-70b"
    temperature: float = 0.7
    
    def _generate(self, messages: list[BaseMessage], **kwargs) -> ChatResult:
        """Generate completion using Snowflake Cortex."""
        # Convert LangChain messages to Cortex format
        cortex_messages = []
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            cortex_messages.append({"role": role, "content": msg.content})
        
        # Create options with temperature
        options = CompleteOptions(temperature=self.temperature)
        
        try:
            # Call Cortex COMPLETE function (same as TruLens uses internally)
            result = complete(
                model=self.model,
                prompt=cortex_messages,
                options=options,
                session=self.session,
                stream=False
            )
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=result))])
        except Exception as e:
            logger.error(f"Cortex API error: {e}")
            logger.error(f"Model: {self.model}, Messages: {cortex_messages}")
            raise
    
    @property
    def _llm_type(self) -> str:
        return "snowflake-cortex"


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Simple LangGraph CLI with TruGraph tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--llm",
        choices=["bedrock", "cortex"],
        default="cortex",
        help="LLM provider: cortex (Snowflake, default) or bedrock (AWS)"
    )
    return parser.parse_args()


def main():
    """Main entry point for the CLI."""
    logger.info("=" * 60)
    logger.info("Simple LangGraph CLI with TruGraph")
    logger.info("=" * 60)

    # Load environment variables
    load_dotenv(override=True)

    # Check required environment variables
    required_vars = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_DATABASE",
        "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"
    ]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        return

    # Create Snowflake session
    logger.info("Creating Snowflake session...")
    snowflake_config = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "database": os.getenv("SNOWFLAKE_DATABASE"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        "role": os.getenv("SNOWFLAKE_ROLE", "SYSADMIN"),
        "authenticator": "externalbrowser"
    }
    
    snowpark_session = Session.builder.configs(snowflake_config).create()
    logger.info("✓ Snowflake session created")

    # Initialize TruLens connector
    use_account_event_table = os.getenv("TRULENS_USE_ACCOUNT_EVENT_TABLE", "true").lower() == "true"
    connector = SnowflakeConnector(
        snowpark_session=snowpark_session,
        use_account_event_table=use_account_event_table
    )
    logger.info("✓ TruLens connector initialized")

    # Create simple chat agent (following TruGraph documentation)
    logger.info("Building LangGraph chat agent...")
    
    # Parse CLI arguments
    args = parse_args()
    logger.info(f"Using LLM provider: {args.llm}")
    
    # Initialize LLM based on provider choice
    if args.llm == "cortex":
        # Use Snowflake Cortex (reuse Snowpark session from connector)
        snowpark_session = connector.snowpark_session
        llm = ChatSnowflakeCortex(
            session=snowpark_session,
            model="llama3.1-70b",
            temperature=0.7
        )
        logger.info("✓ Snowflake Cortex LLM initialized (llama3.1-70b)")
    elif args.llm == "bedrock":
        # Use AWS Bedrock
        llm = ChatBedrock(
            model="anthropic.claude-3-5-sonnet-20240620-v1:0",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            temperature=0.7
        )
        logger.info("✓ AWS Bedrock LLM initialized (Claude 3.5 Sonnet)")
    
    # Build graph (following documentation pattern)
    workflow = StateGraph(MessagesState)
    workflow.add_node("chat", lambda state: {"messages": [llm.invoke(state["messages"])]})
    workflow.add_edge("chat", END)
    workflow.set_entry_point("chat")
    
    graph = workflow.compile()
    logger.info("✓ LangGraph chat agent built")

    # Wrap with TruGraph (following documentation pattern)
    logger.info("Wrapping with TruGraph recorder...")
    tru_recorder = TruGraph(
        graph,
        app_name="SimpleChatAgent",
        app_version="v1",
        connector=connector
    )
    logger.info("✓ TruGraph recorder ready")

    # Simple chat loop
    print("\n" + "=" * 60)
    print("Simple Chat Agent (type 'quit' to exit)")
    print("=" * 60 + "\n")

    while True:
        user_query = input("You(q to quite): ").strip()
        
        if user_query.lower() in ['quit', 'exit', 'q']:
            logger.info("Exiting...")
            break
        
        if not user_query:
            continue

        # Record with live_run context manager
        run_name = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            with tru_recorder.live_run(run_name=run_name) as live_run:
                with live_run.input(user_query):
                    result = graph.invoke({"messages": [HumanMessage(content=user_query)]})
            
            # Extract and display response
            if result and "messages" in result and result["messages"]:
                response = result["messages"][-1].content
                print(f"\nAgent: {response}\n")
                logger.info(f"✓ Trace recorded to Snowflake (run: {run_name})")
            else:
                print("\nAgent: (no response)\n")
            
            # Wait for invocation to complete and compute metrics
            logger.info("Waiting for trace ingestion to complete...")
            run = tru_recorder.get_run(run_name=run_name)
            
            timeout = 180  # 3 minutes
            elapsed = 0
            while (status := run.get_status()) != RunStatus.INVOCATION_COMPLETED:
                if elapsed >= timeout:
                    logger.warning(f"Timeout waiting for invocation completion after {timeout}s. Status: {status}")
                    logger.warning("Skipping metric computation. Check Snowflake for trace status.")
                    break
                logger.info(f"Run status: {status} (elapsed: {elapsed}s)")
                time.sleep(30)
                elapsed += 30
            else:
                # Only compute metrics if invocation completed successfully
                logger.info("Computing metrics...")
                metric_status = run.compute_metrics(metrics=["answer_relevance", "helpfulness", "conciseness"])
                logger.info(f"✓ Metrics computation status: {metric_status}")
                
        except Exception as e:
            logger.error(f"Error during chat: {e}")
            print(f"\nError: {e}\n")

    logger.info("=" * 60)
    logger.info("Session complete. Check Snowflake for traces.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

