"""FastAPI server for movie recommendations with HTMX and A2A endpoints."""
import os
import re
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from src.agent import create_movie_agent

# Load environment variables
load_dotenv()

# Configure LangSmith tracing (if enabled)
if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    if os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY")
    if os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT")
    print("LangSmith tracing enabled")

# Validate required environment variables
required_vars = ["ANTHROPIC_API_KEY", "TMDB_API_KEY", "TAVILY_API_KEY"]
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        "Please create a .env file based on .env.example"
    )

# Initialize the agent
agent = create_movie_agent(
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    tmdb_api_key=os.getenv("TMDB_API_KEY"),
    tavily_api_key=os.getenv("TAVILY_API_KEY")
)

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


class A2ARequest(BaseModel):
    """Request model for A2A endpoint."""
    prompt: str


class A2AResponse(BaseModel):
    """Response model for A2A endpoint."""
    success: bool
    response: str = None
    error: str = None


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
    if not prompt:
        return HTMLResponse(
            content='<div class="error">Please enter a movie preference</div>',
            status_code=400
        )

    result = await agent.aget_recommendations(prompt)

    if not result["success"]:
        return HTMLResponse(
            content=f'<div class="error">Error: {result.get("error", "Unknown error")}</div>',
            status_code=500
        )

    formatted_response = format_response_for_html(result["response"])
    return HTMLResponse(content=formatted_response)


@app.post("/api/a2a/invoke", response_model=A2AResponse)
async def a2a_invoke(request: A2ARequest):
    """A2A endpoint for agent-to-agent communication."""
    if not request.prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    result = await agent.aget_recommendations(request.prompt)

    if not result["success"]:
        return A2AResponse(
            success=False,
            error=result.get("error", "Unknown error")
        )

    return A2AResponse(
        success=True,
        response=result["response"]
    )


@app.get("/api/a2a/health")
async def a2a_health():
    """Health check endpoint for A2A."""
    return {"status": "healthy", "service": "movie-recommendations-a2a"}


@app.get("/health")
async def health():
    """General health check endpoint."""
    return {"status": "healthy", "service": "movie-recommendations"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    print(f"Starting server on http://localhost:{port}")
    print(f"A2A API available at http://localhost:{port}/api/a2a")
    print(f"HTMX frontend available at http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
