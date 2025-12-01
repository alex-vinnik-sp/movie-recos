#!/usr/bin/env python3
"""
Simple Research Assistant CLI with LangGraph and OpenLIT Observability

OpenLIT outputs traces to console - no external collector needed!

Usage:
    uv run openlit_research_cli.py "What are the latest trends in AI?"
"""

import logging
import sys
from typing import TypedDict, Annotated
from operator import add
import re

import openlit  # OpenLIT SDK
from langchain_aws import ChatBedrock
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Enable debug logging for OpenLit and OpenTelemetry to see traces in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Set DEBUG level for opentelemetry.*, openlit.*, and httpx.* loggers
pattern = re.compile(r"^(opentelemetry|openlit|httpx)")
for logger_name in list(logging.root.manager.loggerDict.keys()):
    if pattern.match(logger_name):
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

# Initialize OpenLIT - will use the console exporter we just configured
# Note: Disabling langchain instrumentor due to compatibility issues
# with langchain 1.0+ modular architecture (hub, chains, agents split into separate packages)
openlit.init(
    application_name="research-assistant-cli",
    #disabled_instrumentors=["langchain"]
    otlp_endpoint="http://127.0.0.1:4318"
)

print("\n✨ OpenLIT initialized - traces will be displayed in console below\n")

# Define agent state
class ResearchState(TypedDict):
    """State for research assistant"""
    query: str
    research_notes: Annotated[list[str], add]
    final_answer: str
    iterations: int

# Initialize LLM (AWS Bedrock)
llm = ChatBedrock(
    model_id="anthropic.claude-3-haiku-20240307-v1:0",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

def research_node(state: ResearchState) -> ResearchState:
    """Generate research insights"""
    query = state["query"]
    iteration = state.get("iterations", 0)
    
    print(f"🔍 Research iteration {iteration + 1}...")
    
    prompt = f"""You are a research assistant. For the query: "{query}"
    
Provide 2-3 key insights or facts. Be concise and factual.
Research iteration: {iteration + 1}
"""
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "research_notes": [response.content],
        "iterations": iteration + 1
    }

def summarize_node(state: ResearchState) -> ResearchState:
    """Summarize research into final answer"""
    query = state["query"]
    notes = state["research_notes"]
    
    print("📝 Summarizing findings...")
    
    prompt = f"""Based on this research about "{query}":

{chr(10).join(f"- {note}" for note in notes)}

Provide a clear, concise summary answer (2-3 sentences)."""
    
    response = llm.invoke(prompt)
    
    return {
        **state,
        "final_answer": response.content
    }

def should_continue(state: ResearchState) -> str:
    """Decide if more research needed"""
    # Simple: do 1 research iteration then summarize
    if state["iterations"] < 1:
        return "research"
    return "summarize"

# Build LangGraph
def create_research_graph():
    """Create the research assistant graph"""
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("summarize", summarize_node)
    
    # Add edges
    workflow.set_entry_point("research")
    workflow.add_conditional_edges(
        "research",
        should_continue,
        {
            "research": "research",
            "summarize": "summarize"
        }
    )
    workflow.add_edge("summarize", END)
    
    return workflow.compile()

def main():
    """Main CLI function"""
    if len(sys.argv) < 2:
        print("Usage: uv run openlit_research_cli.py '<your question>'")
        print("Example: uv run openlit_research_cli.py 'What is quantum computing?'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    
    print(f"\n{'='*60}")
    print(f"🔍 Researching: {query}")
    print(f"{'='*60}\n")
    
    # Create and run graph
    graph = create_research_graph()
    
    initial_state = {
        "query": query,
        "research_notes": [],
        "final_answer": "",
        "iterations": 0
    }
    
    # Run with OpenLIT automatically tracking all LLM calls
    result = graph.invoke(initial_state)
    
    print(f"\n{'='*60}")
    print(f"📝 Final Answer:")
    print(f"{'='*60}")
    print(result["final_answer"])
    print(f"{'='*60}\n")
    print("✅ Complete! Check console output above for OpenLIT traces\n")

if __name__ == "__main__":
    main()

