"""Movie recommendation agent using LangGraph and Claude."""

import os
from typing import Annotated, Any, Dict, Sequence, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.tools.tmdb import create_tmdb_tools
from src.tools.websearch import create_web_search_tool

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
        anthropic_api_key: str,
        tmdb_api_key: str,
        tavily_api_key: str,
        model_name: str = "claude-sonnet-4-20250514",
        temperature: float = 0.7,
    ):
        """Initialize the agent."""
        # Create tools
        self.tools = [
            *create_tmdb_tools(tmdb_api_key),
            create_web_search_tool(tavily_api_key),
        ]

        # Initialize LLM with tools
        self.llm = ChatAnthropic(
            model=model_name,
            anthropic_api_key=anthropic_api_key,
            temperature=temperature,
        ).bind_tools(self.tools)

        # Build the graph
        self.graph = self._build_graph()

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

    def _call_model(self, state: AgentState) -> Dict[str, Any]:
        """Call the model with the current state."""
        messages = state["messages"]

        # Add system message if this is the first call
        if not any(isinstance(m, AIMessage) for m in messages):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

        response = self.llm.invoke(messages)
        return {"messages": [response]}

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
        """Get movie recommendations based on user prompt."""
        try:
            # Create initial state
            initial_state = {"messages": [HumanMessage(content=user_prompt)]}

            # Run the graph
            result = self.graph.invoke(initial_state)

            # Extract the final response
            final_message = result["messages"][-1]

            return {"success": True, "response": final_message.content}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def aget_recommendations(self, user_prompt: str) -> Dict[str, Any]:
        """Get movie recommendations (async version)."""
        try:
            # Create initial state
            initial_state = {"messages": [HumanMessage(content=user_prompt)]}

            # Run the graph asynchronously
            result = await self.graph.ainvoke(initial_state)

            # Extract the final response
            final_message = result["messages"][-1]

            return {"success": True, "response": final_message.content}
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_movie_agent(
    anthropic_api_key: str, tmdb_api_key: str, tavily_api_key: str
) -> MovieAgent:
    """Create and return a movie recommendation agent."""
    return MovieAgent(
        anthropic_api_key=anthropic_api_key,
        tmdb_api_key=tmdb_api_key,
        tavily_api_key=tavily_api_key,
    )
