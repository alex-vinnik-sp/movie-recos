"""FastAPI server for movie recommendations with HTMX."""
import os
import re
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

# Configure LangSmith tracing (if enabled)
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
    if os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
    logger.info("LangSmith tracing enabled")

# Validate required environment variables
required_vars = ["OPENAI_API_KEY", "TMDB_API_KEY", "TAVILY_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please create a .env file based on .env.example"
    )

logger.info("All required environment variables are present")

# Initialize the agent
try:
    logger.info("Initializing movie recommendation agent with OpenAI")
    agent = create_movie_agent(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tmdb_api_key=os.getenv("TMDB_API_KEY"),
        tavily_api_key=os.getenv("TAVILY_API_KEY")
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
