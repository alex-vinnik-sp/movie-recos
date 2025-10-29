#!/usr/bin/env python3
"""Entry point for FastAPI server."""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    from dotenv import load_dotenv

    load_dotenv()
    port = int(os.getenv("PORT", 3000))

    print(f"Starting server on http://localhost:{port}")
    print(f"HTMX frontend available at http://localhost:{port}")

    uvicorn.run("src.server:app", host="0.0.0.0", port=port, reload=True)
