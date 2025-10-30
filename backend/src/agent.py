"""Movie recommendation agent using LangGraph and AWS Bedrock."""

import os
import logging
import traceback
from typing import Annotated, Any, Dict, Sequence, TypedDict

from langchain_aws import ChatBedrock
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.tools.tmdb import create_tmdb_tools
from src.tools.websearch import create_web_search_tool

# TruLens instrumentation imports for Snowflake AI Observability
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes

# Configure logging
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a helpful movie recommendation assistant. You have access to the TMDB (The Movie Database) API to search for movies and get detailed information, as well as web search capabilities to find reviews and additional context.

When providing movie recommendations:
1. Use the search_movies tool to find relevant movies based on the user's preferences
2. Use web_search to gather additional context, reviews, or trending information if needed
3. Use get_movie_details to get comprehensive information about specific movies
4. Provide thoughtful recommendations with reasons why each movie matches the user's request
5. Include relevant details like ratings, release dates, and brief overviews
6. Format your final response in a clear, readable way

Always be conversational and helpful in your responses."""


class AgentState(TypedDict):
    """State for the agent graph."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


class MovieAgent:
    """Movie recommendation agent using LangGraph."""

    def __init__(
        self,
        tmdb_api_key: str,
        tavily_api_key: str,
        aws_region: str = "us-east-1",
        aws_profile: str | None = None,
        model_name: str = "anthropic.claude-3-5-sonnet-20240620-v1:0",
        temperature: float = 0.7,
    ):
        """Initialize the agent."""
        logger.info(f"Initializing MovieAgent with model={model_name}, temperature={temperature}, region={aws_region}, profile={aws_profile}")
        
        # Create tools
        try:
            logger.info("Creating TMDB and web search tools")
            self.tools = [
                *create_tmdb_tools(tmdb_api_key),
                create_web_search_tool(tavily_api_key),
            ]
            logger.info(f"Created {len(self.tools)} tools successfully")
        except Exception as e:
            logger.error(f"Failed to create tools: {str(e)}")
            raise

        # Initialize LLM with tools
        try:
            logger.info("Initializing AWS Bedrock LLM (using default credential chain)")
            self.llm = ChatBedrock(
                model_id=model_name,
                region_name=aws_region,
                credentials_profile_name=aws_profile,  # boto3 will use default credential chain
                model_kwargs={"temperature": temperature},
            ).bind_tools(self.tools)
            logger.info("LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Bedrock LLM: {str(e)}")
            logger.error(traceback.format_exc())
            raise

        # Build the graph
        try:
            logger.info("Building LangGraph workflow")
            self.graph = self._build_graph()
            logger.info("LangGraph workflow built successfully")
        except Exception as e:
            logger.error(f"Failed to build graph: {str(e)}")
            raise

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph state graph."""
        # Create the graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(self.tools))

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent", self._should_continue, {"continue": "tools", "end": END}
        )

        # Add edge from tools back to agent
        workflow.add_edge("tools", "agent")

        # Compile the graph
        return workflow.compile()

    @instrument(span_type=SpanAttributes.SpanType.GENERATION)
    def _call_model(self, state: AgentState) -> Dict[str, Any]:
        """Call the model with the current state."""
        messages = state["messages"]
        logger.debug(f"Calling model with {len(messages)} messages")

        # Add system message if this is the first call
        if not any(isinstance(m, AIMessage) for m in messages):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
            logger.debug("Added system prompt to messages")

        try:
            response = self.llm.invoke(messages)
            logger.debug(f"Model responded with message type: {type(response).__name__}")
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Error calling model: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue or end."""
        messages = state["messages"]
        last_message = messages[-1]

        # If there are tool calls, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"

        # Otherwise, end
        return "end"

    def get_recommendations(self, user_prompt: str) -> Dict[str, Any]:
        """Get movie recommendations based on user prompt (sync version - not the main entry point)."""
        try:
            logger.info(f"Starting recommendation for prompt: '{user_prompt[:50]}...'")
            
            # Create initial state
            initial_state = {"messages": [HumanMessage(content=user_prompt)]}

            # Run the graph
            result = self.graph.invoke(initial_state)
            logger.info(f"Graph completed with {len(result['messages'])} messages")

            # Extract the final response
            final_message = result["messages"][-1]
            logger.info(f"Final message type: {type(final_message).__name__}")

            return {"success": True, "response": final_message.content}
        except Exception as e:
            logger.error(f"Error in get_recommendations: {str(e)}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}

    @instrument(
        span_type=SpanAttributes.SpanType.RECORD_ROOT,
        attributes={
            SpanAttributes.RECORD_ROOT.INPUT: "user_prompt",
            SpanAttributes.RECORD_ROOT.OUTPUT: "return",
        }
    )
    async def aget_recommendations(self, user_prompt: str) -> Dict[str, Any]:
        """Get movie recommendations (async version)."""
        try:
            logger.info(f"Starting async recommendation for prompt: '{user_prompt[:50]}...'")
            
            # Create initial state
            initial_state = {"messages": [HumanMessage(content=user_prompt)]}

            # Run the graph asynchronously
            logger.info("Invoking graph asynchronously")
            result = await self.graph.ainvoke(initial_state)
            logger.info(f"Graph completed with {len(result['messages'])} messages")

            # Extract the final response
            final_message = result["messages"][-1]
            logger.info(f"Final message type: {type(final_message).__name__}")

            return {"success": True, "response": final_message.content}
        except Exception as e:
            logger.error(f"Error in aget_recommendations: {str(e)}")
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}


def create_movie_agent(
    tmdb_api_key: str,
    tavily_api_key: str,
    aws_region: str = "us-east-1",
    aws_profile: str | None = None,
) -> MovieAgent:
    """Create and return a movie recommendation agent."""
    return MovieAgent(
        tmdb_api_key=tmdb_api_key,
        tavily_api_key=tavily_api_key,
        aws_region=aws_region,
        aws_profile=aws_profile,
    )
