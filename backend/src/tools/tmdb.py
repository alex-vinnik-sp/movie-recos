"""TMDB API tools for movie search and details."""
import json
import os
import logging
from typing import Optional, Type
import requests
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"


class SearchMoviesInput(BaseModel):
    """Input for searching movies."""
    query: str = Field(description="Search query for movies (e.g., movie title, genre, or 'popular' for trending movies)")
    year: Optional[str] = Field(default=None, description="Optional year to filter results")
    page: int = Field(default=1, description="Page number for pagination (default: 1)")


class MovieDetailsInput(BaseModel):
    """Input for getting movie details."""
    movie_id: int = Field(description="The TMDB movie ID")


class SearchMoviesTool(BaseTool):
    """Tool for searching movies using TMDB API."""

    name: str = "search_movies"
    description: str = (
        "Search for movies using TMDB API. You can search by title, genre, year, "
        "or get popular/trending movies. Returns movie details including title, "
        "overview, rating, release date, and poster path."
    )
    args_schema: Type[BaseModel] = SearchMoviesInput
    api_key: str

    def _run(self, query: str, year: Optional[str] = None, page: int = 1) -> str:
        """Execute the search."""
        logger.info(f"Searching movies: query='{query}', year={year}, page={page}")
        try:
            params = {
                "api_key": self.api_key,
                "page": page
            }

            # Check if user wants popular/trending movies
            if "popular" in query.lower() or "trending" in query.lower():
                endpoint = f"{TMDB_BASE_URL}/movie/popular"
            else:
                endpoint = f"{TMDB_BASE_URL}/search/movie"
                params["query"] = query
                if year:
                    params["year"] = year

            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            movies = [
                {
                    "id": movie["id"],
                    "title": movie["title"],
                    "overview": movie["overview"],
                    "rating": movie["vote_average"],
                    "release_date": movie.get("release_date", ""),
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
                    "popularity": movie["popularity"]
                }
                for movie in data["results"][:10]
            ]

            logger.info(f"TMDB search returned {data['total_results']} total results, showing {len(movies)}")

            return json.dumps({
                "success": True,
                "total_results": data["total_results"],
                "movies": movies
            }, indent=2)

        except Exception as e:
            logger.error(f"TMDB search failed for query '{query}': {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    async def _arun(self, query: str, year: Optional[str] = None, page: int = 1) -> str:
        """Async version."""
        return self._run(query, year, page)


class MovieDetailsTool(BaseTool):
    """Tool for getting detailed movie information."""

    name: str = "get_movie_details"
    description: str = (
        "Get detailed information about a specific movie by its TMDB ID, "
        "including cast, crew, genres, and more."
    )
    args_schema: Type[BaseModel] = MovieDetailsInput
    api_key: str

    def _run(self, movie_id: int) -> str:
        """Execute the details fetch."""
        logger.info(f"Fetching movie details: movie_id={movie_id}")
        try:
            params = {
                "api_key": self.api_key,
                "append_to_response": "credits,keywords"
            }

            response = requests.get(f"{TMDB_BASE_URL}/movie/{movie_id}", params=params)
            response.raise_for_status()
            movie = response.json()

            logger.info(f"Retrieved details for movie: '{movie.get('title', 'Unknown')}'")

            result = {
                "success": True,
                "movie": {
                    "id": movie["id"],
                    "title": movie["title"],
                    "overview": movie["overview"],
                    "rating": movie["vote_average"],
                    "release_date": movie.get("release_date", ""),
                    "runtime": movie.get("runtime"),
                    "genres": [g["name"] for g in movie.get("genres", [])],
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get("poster_path") else None,
                    "backdrop_path": f"https://image.tmdb.org/t/p/original{movie['backdrop_path']}" if movie.get("backdrop_path") else None,
                    "cast": [c["name"] for c in movie.get("credits", {}).get("cast", [])[:10]],
                    "director": next((c["name"] for c in movie.get("credits", {}).get("crew", []) if c["job"] == "Director"), None),
                    "keywords": [k["name"] for k in movie.get("keywords", {}).get("keywords", [])]
                }
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to fetch movie details for ID {movie_id}: {str(e)}")
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    async def _arun(self, movie_id: int) -> str:
        """Async version."""
        return self._run(movie_id)


def create_tmdb_tools(api_key: str) -> list[BaseTool]:
    """Create TMDB tools with the given API key."""
    return [
        SearchMoviesTool(api_key=api_key),
        MovieDetailsTool(api_key=api_key)
    ]
