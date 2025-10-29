"""Web search tool using Tavily API."""
import json
from typing import Type
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


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

    def _run(self, query: str) -> str:
        """Execute the search."""
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

            return json.dumps({
                "success": True,
                "query": query,
                "results": results
            }, indent=2)

        except Exception as e:
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
