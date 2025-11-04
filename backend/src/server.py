"""FastAPI server for movie recommendations with HTMX."""
import os
import re
import sys
import logging
import traceback
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.agent import create_movie_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Enable TruLens debug logging if requested
if os.getenv("DEBUG_TRULENS", "").lower() == "true":
    logging.getLogger("trulens").setLevel(logging.DEBUG)
    logging.getLogger("trulens.core").setLevel(logging.DEBUG)
    logging.getLogger("trulens.connectors").setLevel(logging.DEBUG)
    logging.getLogger("trulens.providers").setLevel(logging.DEBUG)
    logger.info("TruLens debug logging enabled")

# Configure Snowflake AI Observability for tracing (if enabled)
if os.getenv("ENABLE_SNOWFLAKE_OBSERVABILITY", "").lower() == "true":
    # Set TruLens environment variable for OTEL tracing
    os.environ["TRULENS_OTEL_TRACING"] = "1"
    logger.info("Snowflake AI Observability (tracing) enabled")
    
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
            logger.warning(f"Missing Snowflake configuration: {', '.join(missing_sf_vars)}")
            logger.warning("Snowflake AI Observability will be disabled")
        else:
            # Create Snowpark session with SSO
            logger.info("Creating Snowpark session with SSO authentication...")
            snowpark_session = Session.builder.configs(snowflake_config).create()
            logger.info("Snowpark session created successfully")
            
            # Initialize TruLens connector with the Snowpark session
            connector = SnowflakeConnector(snowpark_session=snowpark_session)
            logger.info("Snowflake connector initialized for OTEL trace export")
    except ImportError:
        logger.error("TruLens packages not installed. Run: uv sync")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid Snowflake configuration: {str(e)}")
        logger.error("Please check your Snowflake credentials and configuration")
        logger.error("Exiting due to invalid Snowflake configuration")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to initialize Snowflake AI Observability: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)

# Validate required environment variables
# Note: AWS credentials are handled by boto3's default credential chain
# (environment variables, ~/.aws/credentials, IAM roles, etc.)
required_vars = ["TMDB_API_KEY", "TAVILY_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please create a .env file based on .env.example"
    )

# AWS region and profile are optional (will use defaults if not set)
logger.info(f"AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
if os.getenv('AWS_PROFILE'):
    logger.info(f"AWS Profile: {os.getenv('AWS_PROFILE')}")

logger.info("All required environment variables are present")

# Initialize the agent
try:
    logger.info("Initializing movie recommendation agent with AWS Bedrock")
    agent = create_movie_agent(
        tmdb_api_key=os.getenv("TMDB_API_KEY"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        aws_region=os.getenv("AWS_REGION", "us-east-1"),
        aws_profile=os.getenv("AWS_PROFILE")
    )
    logger.info("Agent initialized successfully")
            
except Exception as e:
    logger.error(f"Failed to initialize agent: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Create FastAPI app
app = FastAPI(title="Movie Recommendations API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


def format_response_for_html(response: str) -> str:
    """Convert markdown-style formatting to HTML."""
    # Convert **bold** to <strong>
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', response)
    # Convert *italic* to <em>
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    # Convert double newlines to paragraph breaks
    html = re.sub(r'\n\n', '</p><p>', html)
    # Convert single newlines to line breaks
    html = re.sub(r'\n', '<br>', html)

    return f'<div class="recommendations"><p>{html}</p></div>'


@app.get("/")
async def read_root():
    """Serve the main page."""
    with open("../frontend/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/api/recommend", response_class=HTMLResponse)
async def recommend(prompt: str = Form(...)):
    """HTMX endpoint for movie recommendations."""
    logger.info(f"Received recommendation request: '{prompt}'")
    
    if not prompt:
        logger.warning("Empty prompt received")
        return HTMLResponse(
            content='<div class="error">Please enter a movie preference</div>',
            status_code=400
        )

    try:
        logger.info("Calling agent.aget_recommendations()")
        result = await agent.aget_recommendations(prompt)
        logger.info(f"Agent returned result with success={result.get('success', False)}")

        if not result["success"]:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Agent returned error: {error_msg}")
            return HTMLResponse(
                content=f'<div class="error">Error: {error_msg}</div>',
                status_code=500
            )

        logger.info("Formatting successful response")
        formatted_response = format_response_for_html(result["response"])
        return HTMLResponse(content=formatted_response)
    
    except Exception as e:
        logger.error(f"Unexpected error in recommend endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return HTMLResponse(
            content=f'<div class="error">Unexpected error: {str(e)}</div>',
            status_code=500
        )


@app.get("/health")
async def health():
    """General health check endpoint."""
    return {"status": "healthy", "service": "movie-recommendations"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    print(f"Starting server on http://localhost:{port}")
    print(f"HTMX frontend available at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
