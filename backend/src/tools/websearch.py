"""Web search tool using Tavily API."""
import json
import logging
import os
from typing import Type
import numpy as np
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from trulens.core.otel.instrument import instrument
from trulens.otel.semconv.trace import SpanAttributes
from trulens.core import Feedback
from trulens.core.feedback.selector import Selector
from trulens.apps.langgraph.inline_evaluations import inline_evaluation
from trulens.providers.bedrock import Bedrock

logger = logging.getLogger(__name__)

# Initialize Bedrock provider for inline evaluations
_bedrock_provider = Bedrock(
    model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
    region_name=os.getenv("AWS_REGION", "us-east-1"),
)

# Define context relevance feedback function for inline evaluation
f_context_relevance = (
    Feedback(
        _bedrock_provider.context_relevance_with_cot_reasons,
        name="Inline Context Relevance (Web Search)"
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
            collect_list=False
        )
    })
    .aggregate(np.mean)
)


class WebSearchInput(BaseModel):
    """Input for web search."""
    query: str = Field(description="The search query")


class WebSearchTool(BaseTool):
    """Tool for searching the web using Tavily API."""

    name: str = "web_search"
    description: str = (
        "Search the web for information about movies, reviews, recommendations, "
        "or general movie-related queries. Use this to get current information, "
        "reviews, or context about movies."
    )
    args_schema: Type[BaseModel] = WebSearchInput
    api_key: str


    @inline_evaluation(f_context_relevance)
    @instrument(
        span_type=SpanAttributes.SpanType.RETRIEVAL,
        attributes={
            SpanAttributes.RETRIEVAL.QUERY_TEXT: "query",
            SpanAttributes.RETRIEVAL.RETRIEVED_CONTEXTS: "return",
            }
    )
    def _run(self, query: str) -> str:
        """Execute the search."""
        logger.info(f"Web search: query='{query}'")
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5
                }
            )
            response.raise_for_status()
            data = response.json()

            results = [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "content": result["content"],
                    "score": result.get("score", 0)
                }
                for result in data.get("results", [])
            ]

            logger.info(f"Web search returned {len(results)} results")

            return json.dumps({
                "success": True,
                "query": query,
                "results": results
            }, indent=2)

        except Exception as e:
            logger.error(f"Web search failed for query '{query}': {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    async def _arun(self, query: str) -> str:
        """Async version."""
        return self._run(query)


def create_web_search_tool(api_key: str) -> WebSearchTool:
    """Create web search tool with the given API key."""
    return WebSearchTool(api_key=api_key)
