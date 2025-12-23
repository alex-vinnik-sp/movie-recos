"""Evaluation wrapper for movie recommendation agent."""

import os
import logging
from typing import Dict, Any
from langsmith import traceable
from dotenv import load_dotenv

from src.agent import create_movie_agent

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@traceable
def evaluation_wrapper(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper function for evaluating the movie recommendation agent.
    
    This function wraps the agent's recommendation logic for LangSmith evaluation.
    It normalizes the input/output format to match LangSmith's expected structure.
    
    Supports multiple input formats:
    - Messages format: {'messages': [{'type': 'human', 'content': '...'}]}
    - Direct format: {'query': '...'} or {'text': '...'} or {'user_prompt': '...'}
    
    Args:
        inputs: Dictionary containing the user query in various formats
        
    Returns:
        Dictionary with 'output' key containing the agent's response
    """
    try:
        # Extract query from inputs (support multiple key formats)
        # LangSmith may pass inputs as messages format: {'messages': [{'type': 'human', 'content': '...'}]}
        query = ""
        
        # First, try to extract from messages format (LangSmith evaluation format)
        if "messages" in inputs and isinstance(inputs["messages"], list):
            for msg in inputs["messages"]:
                if isinstance(msg, dict):
                    msg_type = msg.get("type", "").lower()
                    if msg_type in ["human", "user"]:
                        query = msg.get("content", "")
                        break
                elif hasattr(msg, "content") and hasattr(msg, "type"):
                    # Handle LangChain message objects
                    if msg.type in ["human", "user"]:
                        query = msg.content
                        break
        
        # Fall back to direct key access
        if not query:
            query = inputs.get("query") or inputs.get("text") or inputs.get("user_prompt", "")
        
        if not query:
            logger.warning("Empty query received in evaluation wrapper")
            return {
                "output": "Error: No query provided",
                "error": "Empty query"
            }
        
        logger.info(f"Evaluation wrapper processing query: '{query[:50]}...'")
        
        # Get required API keys from environment
        tmdb_api_key = os.getenv("TMDB_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        if not tmdb_api_key or not tavily_api_key:
            error_msg = "Missing required API keys (TMDB_API_KEY or TAVILY_API_KEY)"
            logger.error(error_msg)
            return {
                "output": f"Error: {error_msg}",
                "error": error_msg
            }
        
        # Create agent instance
        agent = create_movie_agent(
            tmdb_api_key=tmdb_api_key,
            tavily_api_key=tavily_api_key,
            aws_region=aws_region
        )
        
        # Get recommendations (using sync version for evaluation)
        result = agent.get_recommendations(query)
        
        if result.get("success"):
            logger.info("Evaluation wrapper: Successfully got recommendations")
            return {
                "output": result["response"]
            }
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Evaluation wrapper: Agent returned error: {error_msg}")
            return {
                "output": f"Error: {error_msg}",
                "error": error_msg
            }
            
    except Exception as e:
        error_msg = f"Exception in evaluation wrapper: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "output": f"Error: {error_msg}",
            "error": str(e)
        }

