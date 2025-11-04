"""MCP server for movie recommendations."""
import os
import sys
import asyncio
from typing import Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv
from src.agent import create_movie_agent

# Load environment variables
load_dotenv()

# Enable TruLens debug logging if requested
if os.getenv("DEBUG_TRULENS", "").lower() == "true":
    import logging
    logging.getLogger("trulens").setLevel(logging.DEBUG)
    logging.getLogger("trulens.core").setLevel(logging.DEBUG)
    logging.getLogger("trulens.connectors").setLevel(logging.DEBUG)
    logging.getLogger("trulens.providers").setLevel(logging.DEBUG)
    print("TruLens debug logging enabled", file=sys.stderr)

# Configure Snowflake AI Observability (if enabled)
if os.getenv("ENABLE_SNOWFLAKE_OBSERVABILITY", "").lower() == "true":
    # Set TruLens environment variable for OTEL tracing
    os.environ["TRULENS_OTEL_TRACING"] = "1"
    print("Snowflake AI Observability enabled", file=sys.stderr)
    
    # Initialize TruLens Snowflake connector
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
        
        # Validate Snowflake configuration
        required_keys = ["account", "user", "database", "schema", "warehouse"]
        missing_sf_vars = [k for k in required_keys if not snowflake_config.get(k)]
        if missing_sf_vars:
            print(f"Warning: Missing Snowflake configuration: {', '.join(missing_sf_vars)}", file=sys.stderr)
            print("Snowflake AI Observability will be disabled", file=sys.stderr)
        else:
            # Create Snowpark session with SSO
            print("Creating Snowpark session with SSO authentication...", file=sys.stderr)
            snowpark_session = Session.builder.configs(snowflake_config).create()
            print("Snowpark session created successfully", file=sys.stderr)
            
            # Initialize TruLens connector with the Snowpark session
            connector = SnowflakeConnector(snowpark_session=snowpark_session)
            print("Snowflake connector initialized for OTEL trace export", file=sys.stderr)
    except ImportError:
        print("Error: TruLens packages not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: Invalid Snowflake configuration: {str(e)}", file=sys.stderr)
        print("Please check your Snowflake credentials and configuration", file=sys.stderr)
        print("Exiting due to invalid Snowflake configuration", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Failed to initialize Snowflake AI Observability: {str(e)}", file=sys.stderr)
        sys.exit(1)

# Validate required environment variables
# Note: AWS credentials are handled by boto3's default credential chain
# (environment variables, ~/.aws/credentials, IAM roles, etc.)
required_vars = ["TMDB_API_KEY", "TAVILY_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please create a .env file based on .env.example"
    )

# AWS region and profile are optional (will use defaults if not set)
print(f"AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}", file=sys.stderr)
if os.getenv('AWS_PROFILE'):
    print(f"AWS Profile: {os.getenv('AWS_PROFILE')}", file=sys.stderr)

# Initialize the agent
agent = create_movie_agent(
    tmdb_api_key=os.getenv("TMDB_API_KEY"),
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    aws_region=os.getenv("AWS_REGION", "us-east-1"),
    aws_profile=os.getenv("AWS_PROFILE")
)

# Create MCP server
server = Server("movie-recommendations-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_movie_recommendations",
            description=(
                "Get personalized movie recommendations based on user preferences. "
                "You can ask for movies by genre, mood, theme, actor, director, or any other criteria. "
                "The tool uses TMDB API and web search to provide comprehensive recommendations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": (
                            "User's movie preference or request (e.g., 'action movies like John Wick', "
                            "'romantic comedies from the 90s', 'movies with strong female leads')"
                        )
                    }
                },
                "required": ["prompt"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""
    if name != "get_movie_recommendations":
        raise ValueError(f"Unknown tool: {name}")

    prompt = arguments.get("prompt")
    if not prompt or not isinstance(prompt, str):
        raise ValueError("Invalid prompt: must be a non-empty string")

    try:
        result = await agent.aget_recommendations(prompt)

        if not result["success"]:
            raise Exception(result.get("error", "Failed to get recommendations"))

        return [
            TextContent(
                type="text",
                text=result["response"]
            )
        ]
    except Exception as e:
        raise Exception(f"Error getting recommendations: {str(e)}")


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import sys
    print("Movie Recommendations MCP server running on stdio", file=sys.stderr)
    asyncio.run(main())
