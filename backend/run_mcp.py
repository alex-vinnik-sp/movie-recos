#!/usr/bin/env python3
"""Entry point for MCP server."""
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp_server import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())
